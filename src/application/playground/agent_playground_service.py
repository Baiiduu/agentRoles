from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock, Thread
from typing import Any
from uuid import uuid4

from core.contracts import RuntimeServices
from core.tools import ToolTransportKind
from core.llm import (
    DeepSeekChatAdapter,
    EnvironmentProviderConfigLoader,
    OpenAIResponsesAdapter,
    RoutingLLMInvoker,
)
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import InMemoryToolRegistry, ObservedToolInvoker, RoutingToolInvoker
from domain_packs import (
    get_registered_agent_implementations,
    get_registered_tool_descriptors,
)
from domain_packs.education.orchestration import AgentSessionRequest, AgentSessionService
from domain_packs.education.tools import build_education_function_tool_adapter
from domain_packs.operations import build_operations_function_tool_adapter

from application.casework.case_workspace_service import CaseWorkspaceFacade
from application.resource_manager.agent_resource_manager_service import AgentResourceManagerFacade
from application.runtime.agent_runtime_context_service import AgentRuntimeContextFacade
from infrastructure.mcp.mcp_runtime_service import MCPRuntimeFactory, build_mcp_server_catalog
from infrastructure.persistence import (
    SQLiteAgentChatHistoryRepository,
    SQLiteAgentChatSessionRepository,
    get_persistence_settings,
)


class AgentPlaygroundFacade:
    def __init__(self, *, llm_invoker_override: object | None = None) -> None:
        self._llm_invoker_override = llm_invoker_override
        self._runtime_context = AgentRuntimeContextFacade()
        self._case_workspace = CaseWorkspaceFacade()
        self._resource_manager = AgentResourceManagerFacade()
        self._mcp_runtime = MCPRuntimeFactory()
        settings = get_persistence_settings()
        self._chat_history = SQLiteAgentChatHistoryRepository(settings.sqlite_path)
        self._chat_sessions = SQLiteAgentChatSessionRepository(settings.sqlite_path)
        self._session_tasks: dict[str, dict[str, object]] = {}
        self._session_task_lock = Lock()

    def get_bootstrap(self) -> dict[str, object]:
        descriptors = self._runtime_context.runtime_descriptors()
        tool_registry = self._tool_registry_snapshot()
        serialized_agents = [
            self._serialize_agent_summary(descriptor, tool_registry)
            for descriptor in descriptors
        ]
        return {
            "agents": serialized_agents,
            "agent_tree": self._build_agent_tree(serialized_agents),
            "available_cases": self._case_workspace.list_cases()["cases"],
            "default_agent_id": descriptors[0].agent_id if descriptors else None,
            "supported_artifact_types": sorted(
                {
                    str(descriptor.output_contract.get("type", "education.agent_result"))
                    for descriptor in descriptors
                }
            ),
        }

    def get_agent(self, agent_id: str) -> dict[str, object]:
        tool_registry = self._tool_registry_snapshot()
        descriptor = {item.agent_id: item for item in self._runtime_context.runtime_descriptors()}.get(
            agent_id
        )
        if descriptor is None:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        payload = {
            "agent_id": descriptor.agent_id,
            "domain": descriptor.domain,
            "name": descriptor.name,
            "role": descriptor.role,
            "description": descriptor.description,
            "capabilities": list(descriptor.capabilities),
            "tool_refs": list(descriptor.tool_refs),
            "memory_scopes": list(descriptor.memory_scopes),
            "input_contract": descriptor.input_contract,
            "output_contract": descriptor.output_contract,
            "metadata": descriptor.metadata,
            "config": dict(descriptor.metadata.get("config_metadata", {})),
        }
        payload.update(self._tool_view(descriptor, tool_registry))
        sessions = self._serialize_chat_sessions(agent_id)
        active_session_id = sessions[0]["session_id"] if sessions else None
        payload["chat_sessions"] = sessions
        payload["active_session_id"] = active_session_id
        payload["chat_history"] = self._serialize_chat_history(
            agent_id,
            session_id=active_session_id,
        )
        return payload

    def send_message(self, payload: dict[str, object]) -> dict[str, object]:
        request, session = self._build_agent_session_request(payload)
        result = self._run_agent_session_request(payload=payload, request=request, session=session)
        return result

    def start_message_task(self, payload: dict[str, object]) -> dict[str, object]:
        request, session = self._build_agent_session_request(payload)
        now = self._utcnow()
        task_id = f"agent_task_{uuid4().hex}"
        snapshot = {
            "task_id": task_id,
            "agent_id": request.agent_id,
            "session_id": request.session_id,
            "case_id": request.case_id,
            "message": request.message,
            "status": "queued",
            "stage": "queued",
            "current_phase": "understand",
            "current_activity": "Queued and waiting to start.",
            "created_at": now,
            "updated_at": now,
            "events": [],
            "event_count": 0,
            "result": None,
            "error": None,
        }
        with self._session_task_lock:
            self._session_tasks[task_id] = snapshot
        self._append_session_task_event(
            task_id,
            kind="task",
            stage="queued",
            status="queued",
            summary="Task queued.",
            current_phase="understand",
        )
        worker = Thread(
            target=self._run_message_task,
            kwargs={
                "task_id": task_id,
                "payload": deepcopy(payload),
                "request": request,
                "session": session,
            },
            daemon=True,
        )
        worker.start()
        return self.get_message_task(task_id)

    def get_message_task(self, task_id: str) -> dict[str, object]:
        with self._session_task_lock:
            snapshot = deepcopy(self._session_tasks.get(task_id))
        if snapshot is None:
            raise KeyError(f"unknown task_id '{task_id}'")
        return snapshot

    def _build_agent_session_request(
        self,
        payload: dict[str, object],
    ) -> tuple[AgentSessionRequest, object]:
        case_id = str(payload["case_id"]) if payload.get("case_id") is not None else None
        agent_id = str(payload.get("agent_id", ""))
        requested_session_id = str(payload.get("session_id", "")).strip()
        session = (
            self._chat_sessions.get_session(session_id=requested_session_id)
            if requested_session_id
            else self._chat_sessions.get_or_create_latest_session(agent_id=agent_id)
        )
        if session is None:
            raise KeyError(f"unknown session_id '{requested_session_id}'")
        if session.agent_id != agent_id:
            raise ValueError("session does not belong to the selected agent")
        user_ephemeral_context = dict(payload.get("ephemeral_context") or {})
        derived_case_context: dict[str, object] = {}
        if case_id:
            try:
                derived_case_context = self._case_workspace.build_case_session_context(case_id)
            except KeyError:
                derived_case_context = {}
        request = AgentSessionRequest(
            agent_id=agent_id,
            case_id=case_id,
            session_id=session.session_id,
            message=str(payload.get("message", "")),
            ephemeral_context={
                "conversation_history": self._build_conversation_history(session.session_id),
                **derived_case_context,
                **user_ephemeral_context,
            },
            persist_artifact=bool(payload.get("persist_artifact", False)),
        )
        return request, session

    def _run_agent_session_request(
        self,
        *,
        payload: dict[str, object],
        request: AgentSessionRequest,
        session,
    ) -> dict[str, object]:
        service = AgentSessionService(
            agent_descriptors=self._runtime_context.runtime_descriptors(),
            agent_implementations=get_registered_agent_implementations(),
            services=self._build_runtime_services(),
        )
        result = service.send_message(request)
        self._persist_chat_exchange(result)
        self._chat_sessions.rename_session_if_placeholder(
            session_id=result.session_id,
            title=str(payload.get("message", "")),
        )
        return {
            "session": {
                "session_id": result.session_id,
                "agent_id": result.agent_id,
                "status": result.status,
            },
            "agent": {
                "agent_id": result.agent_id,
                "name": result.agent_name,
            },
            "messages": [asdict(message) for message in result.messages],
            "artifact_preview": asdict(result.artifact_preview)
            if result.artifact_preview is not None
            else None,
            "tool_events": result.tool_events,
            "resource_events": result.resource_events,
            "memory_events": result.memory_events,
            "writeback_status": asdict(result.writeback_status),
        }

    def _run_message_task(
        self,
        *,
        task_id: str,
        payload: dict[str, object],
        request: AgentSessionRequest,
        session,
    ) -> None:
        try:
            self._update_session_task(
                task_id,
                {
                    "status": "running",
                    "stage": "preparing",
                    "current_phase": "understand",
                    "current_activity": "Preparing conversation context and runtime services.",
                },
            )
            self._append_session_task_event(
                task_id,
                kind="task",
                stage="preparing",
                status="running",
                summary="Preparing conversation context.",
                current_phase="understand",
            )
            request.ephemeral_context["_progress_callback"] = self._build_progress_callback(task_id)
            response = self._run_agent_session_request(
                payload=payload,
                request=request,
                session=session,
            )
            artifact_payload = (
                response.get("artifact_preview", {}).get("payload", {})
                if isinstance(response.get("artifact_preview"), dict)
                else {}
            )
            current_phase = (
                str(artifact_payload.get("current_phase", "")).strip() or "report"
            )
            self._append_session_task_event(
                task_id,
                kind="task",
                stage="completed",
                status="completed",
                summary="Run completed.",
                current_phase=current_phase,
            )
            self._update_session_task(
                task_id,
                {
                    "status": "completed",
                    "stage": "completed",
                    "current_phase": current_phase,
                    "current_activity": "Completed and ready for review.",
                    "result": response,
                    "error": None,
                },
            )
        except Exception as exc:
            self._append_session_task_event(
                task_id,
                kind="task",
                stage="failed",
                status="failed",
                summary=str(exc),
                current_phase="report",
            )
            self._update_session_task(
                task_id,
                {
                    "status": "failed",
                    "stage": "failed",
                    "current_phase": "report",
                    "current_activity": "Run failed.",
                    "error": str(exc),
                },
            )

    def get_chat_history(
        self,
        agent_id: str,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, object]:
        descriptor = {item.agent_id: item for item in self._runtime_context.runtime_descriptors()}.get(
            agent_id
        )
        if descriptor is None:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        effective_session_id = session_id
        if effective_session_id is None:
            sessions = self._chat_sessions.list_sessions(agent_id=agent_id, limit=1)
            effective_session_id = sessions[0].session_id if sessions else None
        return {
            "agent_id": agent_id,
            "session_id": effective_session_id,
            "messages": self._serialize_chat_history(
                agent_id,
                session_id=effective_session_id,
                limit=limit,
            ),
        }

    def list_chat_sessions(self, agent_id: str, *, limit: int = 20) -> dict[str, object]:
        descriptor = {item.agent_id: item for item in self._runtime_context.runtime_descriptors()}.get(
            agent_id
        )
        if descriptor is None:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        sessions = self._serialize_chat_sessions(agent_id, limit=limit)
        return {
            "agent_id": agent_id,
            "sessions": sessions,
            "active_session_id": sessions[0]["session_id"] if sessions else None,
        }

    def create_chat_session(self, agent_id: str) -> dict[str, object]:
        descriptor = {item.agent_id: item for item in self._runtime_context.runtime_descriptors()}.get(
            agent_id
        )
        if descriptor is None:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        session = self._chat_sessions.create_session(agent_id=agent_id)
        return {
            "agent_id": agent_id,
            "session": self._serialize_chat_session(session),
        }

    def delete_chat_session(self, agent_id: str, session_id: str) -> dict[str, object]:
        deleted = self._chat_sessions.delete_session(session_id=session_id, agent_id=agent_id)
        if not deleted:
            raise KeyError(f"unknown session_id '{session_id}'")
        remaining = self._serialize_chat_sessions(agent_id)
        return {
            "agent_id": agent_id,
            "deleted_session_id": session_id,
            "active_session_id": remaining[0]["session_id"] if remaining else None,
            "sessions": remaining,
        }

    def _build_runtime_services(self) -> RuntimeServices:
        resource_snapshot = self._resource_manager.get_snapshot()
        tool_registry = self._tool_registry_snapshot(
            registered_servers=list(resource_snapshot.get("registry", {}).get("mcp_servers", []))
        )
        _, mcp_adapter = self._mcp_runtime.build(
            registered_servers=list(resource_snapshot.get("registry", {}).get("mcp_servers", []))
        )
        return RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            tool_invoker=ObservedToolInvoker(
                RoutingToolInvoker(
                    registry=tool_registry,
                    adapters=[
                        build_education_function_tool_adapter(),
                        build_operations_function_tool_adapter(),
                        mcp_adapter,
                    ],
                )
            ),
            llm_invoker=self._build_llm_invoker(),
        )

    def _build_llm_invoker(self):
        if self._llm_invoker_override is not None:
            return self._llm_invoker_override

        llm_registry, default_profile_ref = EnvironmentProviderConfigLoader().build_registry()
        if not llm_registry.list_providers():
            return None
        return RoutingLLMInvoker(
            registry=llm_registry,
            adapters=[OpenAIResponsesAdapter(), DeepSeekChatAdapter()],
            default_profile_ref=default_profile_ref,
        )

    def _tool_registry_snapshot(
        self,
        *,
        registered_servers: list[dict[str, object]] | None = None,
    ) -> InMemoryToolRegistry:
        tool_registry = InMemoryToolRegistry()
        for descriptor in get_registered_tool_descriptors():
            tool_registry.register(descriptor)
        mcp_descriptors, _ = self._mcp_runtime.build(
            registered_servers=registered_servers
            if registered_servers is not None
            else list(
                self._resource_manager.get_snapshot().get("registry", {}).get("mcp_servers", [])
            )
        )
        for descriptor in mcp_descriptors:
            if tool_registry.get(descriptor.tool_ref) is None:
                tool_registry.register(descriptor)
        return tool_registry

    def _serialize_agent_summary(self, descriptor, tool_registry: InMemoryToolRegistry) -> dict[str, object]:
        tree_path = self._build_agent_tree_path(descriptor)
        payload = {
            "agent_id": descriptor.agent_id,
            "domain": descriptor.domain,
            "name": descriptor.name,
            "role": descriptor.role,
            "description": descriptor.description,
            "capabilities": list(descriptor.capabilities),
            "tool_refs": list(descriptor.tool_refs),
            "memory_scopes": list(descriptor.memory_scopes),
            "config": dict(descriptor.metadata.get("config_metadata", {})),
            "tree_path": tree_path,
        }
        payload.update(self._tool_view(descriptor, tool_registry))
        return payload

    def _build_agent_tree_path(self, descriptor) -> list[str]:
        domain = str(descriptor.domain or "ungrouped").strip() or "ungrouped"
        return ["domain_packs", domain, "agents", descriptor.agent_id]

    def _build_agent_tree(self, agents: list[dict[str, object]]) -> list[dict[str, object]]:
        root: dict[str, Any] = {"children": {}}
        for agent in agents:
            segments = [str(item).strip() for item in (agent.get("tree_path") or []) if str(item).strip()]
            if not segments:
                continue
            cursor = root
            for index, segment in enumerate(segments):
                children = cursor.setdefault("children", {})
                node = children.get(segment)
                is_leaf = index == len(segments) - 1
                if node is None:
                    node = {
                        "node_id": "/".join(segments[: index + 1]),
                        "name": segment,
                        "kind": "agent" if is_leaf else "group",
                        "children": {},
                    }
                    children[segment] = node
                cursor = node
            cursor["agent_id"] = agent.get("agent_id")
            cursor["label"] = agent.get("name")
            cursor["domain"] = agent.get("domain")
            cursor["role"] = agent.get("role")
            cursor["description"] = agent.get("description")
        return self._serialize_tree_children(root.get("children", {}))

    def _serialize_tree_children(self, children: dict[str, dict[str, Any]]) -> list[dict[str, object]]:
        serialized: list[dict[str, object]] = []
        for key in sorted(children):
            node = children[key]
            kind = str(node.get("kind", "group"))
            payload: dict[str, object] = {
                "node_id": str(node.get("node_id", key)),
                "name": str(node.get("name", key)),
                "kind": kind,
            }
            if kind == "agent":
                payload.update(
                    {
                        "agent_id": node.get("agent_id"),
                        "label": node.get("label") or node.get("name", key),
                        "domain": node.get("domain"),
                        "role": node.get("role"),
                        "description": node.get("description"),
                    }
                )
            else:
                payload["children"] = self._serialize_tree_children(node.get("children", {}))
            serialized.append(payload)
        return serialized

    def _tool_view(self, descriptor, tool_registry: InMemoryToolRegistry) -> dict[str, object]:
        runtime_resources = dict(descriptor.metadata.get("runtime_resource_context") or {})
        assigned_servers = [
            deepcopy(item)
            for item in runtime_resources.get("mcp_servers", [])
            if isinstance(item, dict)
        ]
        mcp_server_catalog = runtime_resources.get("mcp_server_catalog")
        if not isinstance(mcp_server_catalog, list):
            mcp_server_catalog = build_mcp_server_catalog(assigned_servers)
        descriptor_index = {
            tool_ref: tool_registry.get(tool_ref)
            for tool_ref in descriptor.tool_refs
        }
        local_tools: list[dict[str, object]] = []
        mcp_tools: list[dict[str, object]] = []
        for tool_ref in descriptor.tool_refs:
            tool_descriptor = descriptor_index.get(tool_ref)
            if tool_descriptor is None:
                continue
            serialized = self._serialize_tool_descriptor(tool_descriptor)
            if tool_descriptor.transport_kind == ToolTransportKind.MCP:
                mcp_tools.append(serialized)
            else:
                local_tools.append(serialized)
        return {
            "mcp_servers": deepcopy(mcp_server_catalog),
            "tool_catalog": {
                "local_tools": local_tools,
                "mcp_tools": mcp_tools,
            },
            "tool_groups": {
                "local_tool_refs": [item["tool_ref"] for item in local_tools],
                "mcp_tool_refs": [item["tool_ref"] for item in mcp_tools],
            },
        }

    def _serialize_tool_descriptor(self, descriptor) -> dict[str, object]:
        return {
            "tool_ref": descriptor.tool_ref,
            "name": descriptor.name,
            "description": descriptor.description,
            "transport_kind": str(descriptor.transport_kind),
            "provider_ref": descriptor.provider_ref,
            "operation_ref": descriptor.operation_ref,
            "side_effect_kind": str(descriptor.side_effect_kind),
            "tags": list(descriptor.tags),
            "metadata": deepcopy(descriptor.metadata),
        }

    def _persist_chat_exchange(self, result) -> None:
        user_messages = [item for item in result.messages if getattr(item, "role", "") == "user"]
        for message in user_messages:
            if message.content.strip():
                self._chat_history.append_user_message(
                    session_id=result.session_id,
                    agent_id=result.agent_id,
                    content=message.content,
                )
        agent_messages = [item for item in result.messages if getattr(item, "role", "") == "agent"]
        for message in agent_messages:
            if message.content.strip():
                self._chat_history.append_agent_message(
                    session_id=result.session_id,
                    agent_id=result.agent_id,
                    content=message.content,
                )

    def _serialize_chat_history(
        self,
        agent_id: str,
        *,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        return [
            {
                "message_id": item.message_id,
                "session_id": item.session_id,
                "agent_id": item.agent_id,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at,
            }
            for item in self._chat_history.list_messages(
                agent_id=agent_id if session_id is None else None,
                session_id=session_id,
                limit=limit,
            )
        ]

    def _serialize_chat_sessions(self, agent_id: str, *, limit: int = 20) -> list[dict[str, object]]:
        return [
            self._serialize_chat_session(item)
            for item in self._chat_sessions.list_sessions(agent_id=agent_id, limit=limit)
        ]

    def _serialize_chat_session(self, session) -> dict[str, object]:
        return {
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    def _build_conversation_history(self, session_id: str, *, limit: int = 20) -> list[dict[str, str]]:
        return [
            {
                "role": item.role,
                "content": item.content,
            }
            for item in self._chat_history.list_messages(session_id=session_id, limit=limit)
        ]

    def _build_progress_callback(self, task_id: str):
        def _callback(event: dict[str, object]) -> None:
            self._record_progress_event(task_id, event)

        return _callback

    def _record_progress_event(self, task_id: str, event: dict[str, object]) -> None:
        stage = str(event.get("stage", "running")).strip() or "running"
        status = str(event.get("status", "running")).strip() or "running"
        current_phase = str(event.get("current_phase", "understand")).strip() or "understand"
        summary = str(event.get("summary", "")).strip() or "Agent is working."
        current_activity = str(event.get("current_activity", "")).strip() or summary
        self._append_session_task_event(
            task_id,
            kind=str(event.get("kind", "progress")).strip() or "progress",
            stage=stage,
            status=status,
            summary=summary,
            current_phase=current_phase,
            tool_ref=event.get("tool_ref"),
            detail=event.get("detail"),
        )
        self._update_session_task(
            task_id,
            {
                "status": status,
                "stage": stage,
                "current_phase": current_phase,
                "current_activity": current_activity,
            },
        )

    def _append_session_task_event(
        self,
        task_id: str,
        *,
        kind: str,
        stage: str,
        status: str,
        summary: str,
        current_phase: str,
        tool_ref: object | None = None,
        detail: object | None = None,
    ) -> None:
        with self._session_task_lock:
            snapshot = self._session_tasks.get(task_id)
            if snapshot is None:
                return
            events = snapshot.setdefault("events", [])
            sequence = len(events) + 1
            event = {
                "sequence": sequence,
                "timestamp": self._utcnow(),
                "kind": kind,
                "stage": stage,
                "status": status,
                "summary": summary,
                "current_phase": current_phase,
            }
            if isinstance(tool_ref, str) and tool_ref.strip():
                event["tool_ref"] = tool_ref.strip()
            if detail is not None:
                event["detail"] = deepcopy(detail)
            events.append(event)
            snapshot["event_count"] = len(events)
            snapshot["updated_at"] = self._utcnow()

    def _update_session_task(self, task_id: str, patch: dict[str, object]) -> None:
        with self._session_task_lock:
            snapshot = self._session_tasks.get(task_id)
            if snapshot is None:
                return
            snapshot.update(deepcopy(patch))
            snapshot["updated_at"] = self._utcnow()

    def _utcnow(self) -> str:
        return datetime.now(UTC).isoformat()
