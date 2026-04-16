from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.agents import AgentDescriptor, AgentImplementation, ResolvedAgentBinding
from core.contracts import ExecutionContext, RuntimeServices
from core.state.models import NodeState, NodeStatus, NodeType, RunRecord, RunState, ThreadRecord, ThreadState, RunStatus
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec, WorkflowDefinition

from domain_packs.education.orchestration.session_models import (
    AgentArtifactPreview,
    AgentSessionMessage,
    AgentSessionRequest,
    AgentSessionResult,
    AgentWritebackStatus,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _artifact_summary(payload: dict[str, Any]) -> str:
    for key in ("reply", "summary", "explanation", "error_analysis"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Agent session artifact generated."


def _tool_events_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tool_context = payload.get("tool_context")
    if not isinstance(tool_context, dict):
        return []
    events: list[dict[str, Any]] = []
    for key, value in tool_context.items():
        events.append(
            {
                "tool_key": str(key),
                "output_preview": deepcopy(value),
            }
        )
    return events


def _resource_events_from_binding(binding: ResolvedAgentBinding | None) -> list[dict[str, Any]]:
    if binding is None:
        return []
    runtime_context = binding.metadata.get("runtime_resource_context")
    if not isinstance(runtime_context, dict):
        return []
    events: list[dict[str, Any]] = []
    mcp_servers = runtime_context.get("mcp_servers")
    if isinstance(mcp_servers, list) and mcp_servers:
        events.append(
            {
                "resource_kind": "mcp_servers",
                "items": deepcopy(mcp_servers),
            }
        )
    skills = runtime_context.get("skills")
    if isinstance(skills, list) and skills:
        events.append(
            {
                "resource_kind": "skills",
                "items": deepcopy(skills),
            }
        )
    workspace = runtime_context.get("workspace")
    if isinstance(workspace, dict) and workspace:
        events.append(
            {
                "resource_kind": "workspace",
                "items": deepcopy(workspace),
            }
        )
    effectiveness = runtime_context.get("distribution_effectiveness")
    if isinstance(effectiveness, dict) and effectiveness:
        events.append(
            {
                "resource_kind": "distribution_effectiveness",
                "items": deepcopy(effectiveness),
            }
        )
    return events


def _case_context_events_from_input(selected_input: dict[str, Any]) -> list[dict[str, Any]]:
    case_context = selected_input.get("case_context")
    if not isinstance(case_context, dict):
        return []
    return [
        {
            "resource_kind": "case_context",
            "items": {
                "case_id": case_context.get("case_id"),
                "title": case_context.get("title"),
                "learner_state": case_context.get("learner_state"),
                "active_plan": case_context.get("active_plan"),
                "recent_artifacts": case_context.get("recent_artifacts"),
                "recent_session_summaries": case_context.get("recent_session_summaries"),
            },
        }
    ]


class AgentSessionService:
    """
    Education-domain single-agent session orchestrator.

    This service intentionally does not go through RuntimeService.start_run().
    It provides a lighter interaction model for one-agent playground sessions
    while still reusing the same agent implementations, llm tools, and memory
    services as the rest of the platform.
    """

    def __init__(
        self,
        *,
        agent_descriptors: list[AgentDescriptor],
        agent_implementations: list[AgentImplementation],
        services: RuntimeServices,
    ) -> None:
        self._descriptors = {descriptor.agent_id: deepcopy(descriptor) for descriptor in agent_descriptors}
        self._implementations = list(agent_implementations)
        self._services = services

    def list_agents(self) -> list[AgentDescriptor]:
        return [deepcopy(item) for item in self._descriptors.values()]

    def get_agent(self, agent_id: str) -> AgentDescriptor:
        descriptor = self._descriptors.get(agent_id)
        if descriptor is None:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        return deepcopy(descriptor)

    def send_message(self, request: AgentSessionRequest) -> AgentSessionResult:
        descriptor = self.get_agent(request.agent_id)
        implementation = self._select_implementation(descriptor)
        binding = self._build_binding(descriptor)
        selected_input = self._build_selected_input(request)
        effective_session_id = str(selected_input.get("session_id", "")).strip() or _new_id("agent_session")
        selected_input["session_id"] = effective_session_id
        context = self._build_execution_context(binding=binding, selected_input=selected_input)
        result = implementation.invoke(context)

        if result.status != NodeStatus.SUCCEEDED or result.output is None:
            error_message = result.error_message or "Agent session failed."
            return AgentSessionResult(
                session_id=effective_session_id,
                status=str(result.status),
                agent_id=descriptor.agent_id,
                agent_name=descriptor.name,
                messages=[
                    AgentSessionMessage(role="user", content=request.message),
                    AgentSessionMessage(role="system", content=error_message),
                ],
                artifact_preview=None,
                tool_events=[],
                resource_events=(
                    _resource_events_from_binding(binding)
                    + _case_context_events_from_input(selected_input)
                ),
                memory_events=[],
                writeback_status=self._build_writeback_status(request),
            )

        artifact_type = str(descriptor.output_contract.get("type", f"education.{descriptor.agent_id}.result"))
        artifact_payload = deepcopy(result.output or {})
        artifact_preview = AgentArtifactPreview(
            artifact_type=artifact_type,
            summary=_artifact_summary(artifact_payload),
            payload=artifact_payload,
        )
        return AgentSessionResult(
            session_id=effective_session_id,
            status="responded" if result.status == NodeStatus.SUCCEEDED else str(result.status),
            agent_id=descriptor.agent_id,
            agent_name=descriptor.name,
            messages=[
                AgentSessionMessage(role="user", content=request.message),
                AgentSessionMessage(
                    role="agent",
                    content=str(artifact_payload.get("reply", artifact_preview.summary)),
                ),
            ],
            artifact_preview=artifact_preview,
            tool_events=_tool_events_from_payload(artifact_payload),
            resource_events=(
                _resource_events_from_binding(binding)
                + _case_context_events_from_input(selected_input)
            ),
            memory_events=[],
            writeback_status=self._build_writeback_status(request),
        )

    def _select_implementation(self, descriptor: AgentDescriptor) -> AgentImplementation:
        matches = [
            implementation
            for implementation in self._implementations
            if getattr(implementation, "implementation_ref", None) == descriptor.implementation_ref
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(
                f"no implementation available for agent_id '{descriptor.agent_id}'"
            )
        raise ValueError(
            f"multiple implementations available for agent_id '{descriptor.agent_id}'"
        )

    def _build_binding(self, descriptor: AgentDescriptor) -> ResolvedAgentBinding:
        return ResolvedAgentBinding(
            node_id="agent_session",
            agent_ref=descriptor.agent_id,
            resolved_agent_id=descriptor.agent_id,
            resolved_version=descriptor.version,
            executor_ref=descriptor.executor_ref,
            implementation_ref=descriptor.implementation_ref,
            tool_refs=list(descriptor.tool_refs),
            memory_scopes=list(descriptor.memory_scopes),
            policy_profiles=list(descriptor.policy_profiles),
            capabilities=list(descriptor.capabilities),
            metadata=deepcopy(descriptor.metadata),
        )

    def _build_selected_input(self, request: AgentSessionRequest) -> dict[str, Any]:
        payload = deepcopy(request.ephemeral_context)
        payload["message"] = request.message
        if request.session_id:
            payload["session_id"] = request.session_id
        if request.case_id:
            payload["case_id"] = request.case_id
        return payload

    def _build_execution_context(
        self,
        *,
        binding: ResolvedAgentBinding,
        selected_input: dict[str, Any],
    ) -> ExecutionContext:
        workflow = WorkflowDefinition(
            workflow_id="education.agent_session",
            name="Education Agent Session",
            version="0.1.0",
            entry_node_id="agent_session",
            node_specs=[
                NodeSpec(
                    node_id="agent_session",
                    node_type=NodeType.AGENT,
                    executor_ref=binding.executor_ref,
                    agent_ref=binding.agent_ref,
                    input_selector=InputSelector(
                        sources=[
                            InputSource(
                                source_type=InputSourceType.LITERAL,
                                source_ref="session_input",
                            )
                        ]
                    ),
                    metadata={"mode": "agent_playground"},
                )
            ],
            edge_specs=[],
        )
        compiled_workflow = CompiledWorkflow(
            workflow_id=workflow.workflow_id,
            version=workflow.version,
            entry_node_id=workflow.entry_node_id,
            node_map={node.node_id: node for node in workflow.node_specs},
            outgoing_edges={"agent_session": []},
            incoming_edges={"agent_session": []},
        )
        session_id = str(selected_input.get("session_id", "")).strip() or _new_id("agent_session")
        thread_id = f"thread_{session_id}"
        run_id = _new_id("run")
        node_spec = compiled_workflow.node_map["agent_session"]
        now = datetime.now(UTC)
        runtime_resource_context = (
            deepcopy(binding.metadata.get("runtime_resource_context", {}))
            if binding.metadata
            else {}
        )
        if runtime_resource_context:
            selected_input["runtime_resource_context"] = deepcopy(runtime_resource_context)
        return ExecutionContext(
            thread_record=ThreadRecord(
                thread_id=thread_id,
                thread_type="education_agent_session",
                title="Agent Playground Session",
            ),
            run_record=RunRecord(
                run_id=run_id,
                thread_id=thread_id,
                workflow_id=compiled_workflow.workflow_id,
                workflow_version=compiled_workflow.version,
                status=RunStatus.RUNNING,
                entry_node_id=node_spec.node_id,
            ),
            thread_state=ThreadState(
                thread_id=thread_id,
                goal="education agent playground session",
                global_context=deepcopy(selected_input),
            ),
            run_state=RunState(
                run_id=run_id,
                thread_id=thread_id,
                workflow_id=compiled_workflow.workflow_id,
                workflow_version=compiled_workflow.version,
                status=RunStatus.RUNNING,
            ),
            node_state=NodeState(
                run_id=run_id,
                node_id=node_spec.node_id,
                node_type=node_spec.node_type,
                status=NodeStatus.RUNNING,
                attempt=1,
                started_at=now,
                executor_ref=node_spec.executor_ref,
            ),
            workflow=compiled_workflow,
            node_spec=node_spec,
            agent_binding=binding,
            selected_input=selected_input,
            services=self._services,
            trace_context={"scope": "agent_playground"},
        )

    def _build_writeback_status(self, request: AgentSessionRequest) -> AgentWritebackStatus:
        if not request.persist_artifact:
            return AgentWritebackStatus(
                persisted=False,
                case_id=request.case_id,
                message="writeback not requested",
            )
        if not request.case_id:
            return AgentWritebackStatus(
                persisted=False,
                case_id=None,
                message="case_id is required for writeback",
            )
        return AgentWritebackStatus(
            persisted=False,
            case_id=request.case_id,
            message="case repository is not implemented yet",
        )
