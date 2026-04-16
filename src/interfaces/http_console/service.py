from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

from core.agents import InMemoryAgentRegistry, RegistryBackedAgentBindingResolver
from core.contracts import RuntimeServices
from core.evaluation import EvaluationCaseResult, EvaluationRunner, SuiteMetricsAggregator
from core.evaluation.models import EvaluationSuite, EvaluationSuiteResult
from core.executors import BasicNodeExecutor, DomainAgentExecutor, ToolNodeExecutor
from core.llm import (
    DeepSeekChatAdapter,
    EnvironmentProviderConfigLoader,
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
    LLMResponseFormatKind,
    OpenAIResponsesAdapter,
    RoutingLLMInvoker,
)
from core.observability import RuntimeQueryService
from core.runtime import RuntimeService
from core.state.models import NodeType
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import InMemoryToolRegistry, ObservedToolInvoker, RoutingToolInvoker
from core.workflow import InMemoryWorkflowProvider
from domain_packs import (
    get_registered_agent_descriptors,
    get_registered_agent_implementations,
    get_registered_domain_packs,
    get_registered_eval_cases,
    get_registered_eval_suites,
    get_registered_tool_descriptors,
    get_registered_workflow_definitions,
)
from domain_packs.education.evals import (
    EducationEvaluationDriver,
    build_default_education_eval_scorers,
)
from domain_packs.education.tools import build_education_function_tool_adapter
from application.agent_admin.agent_capability_service import AgentCapabilityFacade
from application.agent_admin.agent_config_service import AgentConfigFacade
from application.casework.case_workspace_service import CaseWorkspaceFacade
from application.playground.agent_playground_service import AgentPlaygroundFacade
from application.resource_manager.agent_resource_manager_service import AgentResourceManagerFacade


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(item) for item in value]
    return value


def _pretty_json(value: Any) -> str:
    return json.dumps(_json_ready(value), ensure_ascii=False, indent=2)


class ProjectConsoleService:
    """
    Thin demo-facing application service.

    This layer assembles the existing platform and domain pack for local web
    exploration without pushing presentation concerns back into core or the
    education pack.
    """

    def __init__(self, *, llm_invoker_override: object | None = None) -> None:
        self._llm_invoker_override = llm_invoker_override
        self._agent_capability = AgentCapabilityFacade()
        self._agent_config = AgentConfigFacade()
        self._agent_playground = AgentPlaygroundFacade(
            llm_invoker_override=llm_invoker_override
        )
        self._agent_resource_manager = AgentResourceManagerFacade()
        self._case_workspace = CaseWorkspaceFacade()

    def list_agent_configs(self) -> dict[str, object]:
        return self._agent_config.list_configs()

    def get_agent_config(self, agent_id: str) -> dict[str, object]:
        return self._agent_config.get_config(agent_id)

    def save_agent_config(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        return self._agent_config.save_config(agent_id, payload)

    def list_agent_capabilities(self) -> dict[str, object]:
        return self._agent_capability.list_capabilities()

    def get_agent_capability(self, agent_id: str) -> dict[str, object]:
        return self._agent_capability.get_capability(agent_id)

    def save_agent_capability(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        return self._agent_capability.save_capability(agent_id, payload)

    def get_agent_resource_manager_snapshot(self) -> dict[str, object]:
        return self._agent_resource_manager.get_snapshot()

    def save_agent_workspace_root(self, payload: dict[str, object]) -> dict[str, object]:
        return self._agent_resource_manager.save_workspace_root(payload)

    def provision_agent_workspace_root(self) -> dict[str, object]:
        return self._agent_resource_manager.provision_workspace_root()

    def pick_agent_workspace_root(self) -> dict[str, object]:
        return self._agent_resource_manager.pick_workspace_root()

    def save_registered_mcp_server(
        self,
        server_ref: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._agent_resource_manager.save_mcp_server(server_ref, payload)

    def test_registered_mcp_server(
        self,
        server_ref: str,
    ) -> dict[str, object]:
        return self._agent_resource_manager.test_mcp_server_connection(server_ref)

    def authenticate_registered_mcp_server(
        self,
        server_ref: str,
    ) -> dict[str, object]:
        return self._agent_resource_manager.authenticate_mcp_server(server_ref)

    def discover_registered_mcp_server_tools(
        self,
        server_ref: str,
    ) -> dict[str, object]:
        return self._agent_resource_manager.discover_mcp_server_tools(server_ref)

    def save_registered_skill(
        self,
        skill_name: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._agent_resource_manager.save_skill(skill_name, payload)

    def save_agent_workspace(
        self,
        agent_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._agent_resource_manager.save_workspace(agent_id, payload)

    def save_agent_resource_distribution(
        self,
        agent_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._agent_resource_manager.save_agent_distribution(agent_id, payload)

    def get_agent_playground_bootstrap(self) -> dict[str, object]:
        return self._agent_playground.get_bootstrap()

    def get_agent_playground_agent(self, agent_id: str) -> dict[str, object]:
        return self._agent_playground.get_agent(agent_id)

    def get_agent_playground_chat_history(
        self,
        agent_id: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, object]:
        return self._agent_playground.get_chat_history(agent_id, session_id=session_id)

    def list_agent_playground_sessions(self, agent_id: str) -> dict[str, object]:
        return self._agent_playground.list_chat_sessions(agent_id)

    def create_agent_playground_session(self, agent_id: str) -> dict[str, object]:
        return self._agent_playground.create_chat_session(agent_id)

    def delete_agent_playground_session(self, agent_id: str, session_id: str) -> dict[str, object]:
        return self._agent_playground.delete_chat_session(agent_id, session_id)

    def send_agent_playground_message(self, payload: dict[str, object]) -> dict[str, object]:
        return self._agent_playground.send_message(payload)

    def list_case_workspace_cases(self) -> dict[str, object]:
        return self._case_workspace.list_cases()

    def get_case_workspace_case(self, case_id: str) -> dict[str, object]:
        return self._case_workspace.get_case(case_id)

    def create_case_handoff(
        self,
        case_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._case_workspace.create_handoff(case_id, payload)

    def append_case_session_feed_item(
        self,
        case_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return self._case_workspace.append_session_feed_item(case_id, payload)

    def get_case_coordination(self, case_id: str) -> dict[str, object]:
        return self._case_workspace.get_coordination(case_id)

    def get_overview(self) -> dict[str, object]:
        llm_bundle = EnvironmentProviderConfigLoader().load()
        domain_packs = get_registered_domain_packs()
        agents = get_registered_agent_descriptors()
        workflows = get_registered_workflow_definitions()
        tools = get_registered_tool_descriptors()
        eval_cases = get_registered_eval_cases()
        eval_suites = get_registered_eval_suites()

        samples: dict[str, list[dict[str, object]]] = {}
        for case in eval_cases:
            global_context = case.trigger_payload.get("global_context", {})
            if isinstance(global_context, dict):
                samples.setdefault(case.workflow_id, []).append(
                    {
                        "case_id": case.case_id,
                        "title": case.title or case.case_id,
                        "global_context": _json_ready(global_context),
                    }
                )

        return {
            "project": {
                "name": "Agent Roles Prototype Console",
                "mode": "prototype",
                "intended_use": "self-test and architecture exploration",
            },
            "llm_status": {
                "integrated": True,
                "configured": bool(llm_bundle.providers),
                "configured_provider_count": len(llm_bundle.providers),
                "configured_profile_count": len(llm_bundle.profiles),
                "mode": "adapter_layer_ready",
                "summary": (
                    "项目已经具备真实的 LLM 适配层。只要 provider 配置存在，"
                    "教育域 agent 就可以调用真实模型。"
                ),
                "api_owner": "你通过 .env 或环境变量提供 OpenAI / DeepSeek 的 API 配置。",
                "next_step": "配置 provider 后，就可以让教育域 agent 直接跑真实模型。",
                "providers": [
                    {
                        "provider_ref": provider.provider_ref,
                        "provider_kind": str(provider.provider_kind),
                        "default_model": provider.default_model,
                        "base_url": provider.base_url,
                    }
                    for provider in llm_bundle.providers
                ],
                "profiles": [
                    {
                        "profile_ref": profile.profile_ref,
                        "provider_ref": profile.provider_ref,
                        "model_name": profile.model_name,
                    }
                    for profile in llm_bundle.profiles
                ],
                "required_env_vars": [
                    "AGENTSROLES_OPENAI_API_KEY",
                    "AGENTSROLES_OPENAI_BASE_URL",
                    "AGENTSROLES_OPENAI_MODEL",
                    "AGENTSROLES_DEEPSEEK_API_KEY",
                    "AGENTSROLES_DEEPSEEK_BASE_URL",
                    "AGENTSROLES_DEEPSEEK_MODEL",
                    "AGENTSROLES_DEFAULT_LLM_PROFILE",
                ],
            },
            "domain_packs": [
                _json_ready(asdict(pack.get_metadata()))
                for pack in domain_packs
            ],
            "counts": {
                "domain_packs": len(domain_packs),
                "agents": len(agents),
                "workflows": len(workflows),
                "tools": len(tools),
                "eval_cases": len(eval_cases),
                "eval_suites": len(eval_suites),
            },
            "agents": [
                {
                    "agent_id": descriptor.agent_id,
                    "name": descriptor.name,
                    "role": descriptor.role,
                    "domain": descriptor.domain,
                    "version": descriptor.version,
                    "description": descriptor.description,
                    "capabilities": list(descriptor.capabilities),
                    "tool_refs": list(descriptor.tool_refs),
                    "memory_scopes": list(descriptor.memory_scopes),
                    "implementation_ref": descriptor.implementation_ref,
                }
                for descriptor in agents
            ],
            "tools": [
                {
                    "tool_ref": descriptor.tool_ref,
                    "name": descriptor.name,
                    "description": descriptor.description,
                    "transport_kind": str(descriptor.transport_kind),
                    "side_effect_kind": str(descriptor.side_effect_kind),
                    "tags": list(descriptor.tags),
                }
                for descriptor in tools
            ],
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "version": workflow.version,
                    "entry_node_id": workflow.entry_node_id,
                    "node_count": len(workflow.node_specs),
                    "agent_node_count": sum(
                        1 for node in workflow.node_specs if node.node_type == NodeType.AGENT
                    ),
                    "tool_node_count": sum(
                        1 for node in workflow.node_specs if node.node_type == NodeType.TOOL
                    ),
                    "nodes": [
                        {
                            "node_id": node.node_id,
                            "node_type": str(node.node_type),
                            "executor_ref": node.executor_ref,
                            "agent_ref": node.agent_ref,
                            "tool_ref": node.config.get("tool_ref"),
                        }
                        for node in workflow.node_specs
                    ],
                }
                for workflow in workflows
            ],
            "eval_suites": [
                {
                    "suite_id": suite.suite_id,
                    "name": suite.name,
                    "case_count": len(suite.cases),
                    "case_ids": [case.case_id for case in suite.cases],
                }
                for suite in eval_suites
            ],
            "samples": samples,
        }

    def chat_with_project_agent(self, message: str) -> dict[str, object]:
        user_message = message.strip()
        if not user_message:
            raise ValueError("message must be non-empty")

        project_snapshot = self._build_project_snapshot()
        llm_invoker = self._build_llm_invoker()
        if llm_invoker is None:
            return {
                "mode": "local_fallback",
                "message": self._build_local_assistant_reply(user_message, project_snapshot),
                "provider_ref": None,
                "model_name": None,
                "project_snapshot": project_snapshot,
            }

        result = llm_invoker.invoke(
            LLMRequest(
                request_id=f"web-console-assistant:{datetime.now().isoformat()}",
                profile_ref=self._preferred_assistant_profile_ref(),
                response_format=LLMResponseFormatKind.TEXT,
                messages=[
                    LLMMessage(
                        role=LLMMessageRole.USER,
                        content=(
                            "以下是当前项目结构摘要，请基于它回答用户问题。\n\n"
                            f"{_pretty_json(project_snapshot)}\n\n"
                            "用户问题：\n"
                            f"{user_message}"
                        ),
                    )
                ],
                system_prompt=(
                    "你是一个教育领域多智能体项目助手。"
                    "你能看到当前项目结构、教育域 agent、workflow、tool 和 eval。"
                    "请用简体中文回答，尽量结合当前项目的真实结构给出具体建议。"
                    "如果用户问 workflow 和 eval 是怎么运行的，请直接说明实际执行路径。"
                ),
                metadata={"channel": "education_web_console_chat"},
            )
        )

        if not result.success or not result.output_text:
            return {
                "mode": "local_fallback",
                "message": self._build_local_assistant_reply(user_message, project_snapshot),
                "provider_ref": result.provider_ref,
                "model_name": result.model_name,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "project_snapshot": project_snapshot,
            }

        return {
            "mode": "llm",
            "message": result.output_text,
            "provider_ref": result.provider_ref,
            "model_name": result.model_name,
            "finish_reason": result.finish_reason,
            "project_snapshot": project_snapshot,
        }

    def run_workflow(
        self,
        workflow_id: str,
        *,
        global_context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        runtime, services = self._build_runtime()
        thread = runtime.create_thread("demo", workflow_id, title=f"Demo {workflow_id}")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        if thread_state is None:
            raise ValueError("thread_state missing for newly created thread")
        thread_state.global_context = dict(global_context or {})
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, workflow_id)
        query_service = RuntimeQueryService(runtime)
        observation = query_service.fetch_run_observation(run.run_id)
        digest = query_service.build_digest(run.run_id)
        timeline = query_service.build_timeline(run.run_id)

        return {
            "run": {
                "run_id": observation.snapshot.run_record.run_id,
                "thread_id": observation.snapshot.thread_record.thread_id,
                "workflow_id": observation.snapshot.run_record.workflow_id,
                "workflow_version": observation.snapshot.run_record.workflow_version,
                "status": str(observation.snapshot.run_record.status),
                "completed_nodes": list(observation.snapshot.run_state.completed_nodes),
                "failed_nodes": list(observation.snapshot.run_state.failed_nodes),
                "waiting_nodes": list(observation.snapshot.run_state.waiting_nodes),
            },
            "digest": _json_ready(asdict(digest)),
            "nodes": [
                {
                    "node_id": node_state.node_id,
                    "node_type": str(node_state.node_type),
                    "status": str(node_state.status),
                    "attempt": node_state.attempt,
                    "executor_ref": node_state.executor_ref,
                    "output_artifact_id": node_state.output_artifact_id,
                    "error_code": node_state.error_code,
                    "error_message": node_state.error_message,
                }
                for node_state in observation.snapshot.node_states.values()
            ],
            "artifacts": [
                {
                    "artifact_id": artifact.artifact_id,
                    "producer_node_id": artifact.producer_node_id,
                    "artifact_type": artifact.artifact_type,
                    "summary": artifact.summary,
                    "payload": _json_ready(artifact.payload_inline or {}),
                }
                for artifact in observation.snapshot.artifacts.values()
            ],
            "timeline": [
                {
                    "source_kind": item.source_kind,
                    "occurred_at": item.occurred_at.isoformat(),
                    "label": item.label,
                    "node_id": item.node_id,
                    "event_type": item.event_type,
                    "payload": _json_ready(item.payload),
                    "metadata": _json_ready(item.metadata),
                }
                for item in timeline
            ],
            "interrupts": [
                {
                    "interrupt_id": interrupt.interrupt_id,
                    "interrupt_type": str(interrupt.interrupt_type),
                    "status": str(interrupt.status),
                    "node_id": interrupt.node_id,
                    "reason_code": interrupt.reason_code,
                    "reason_message": interrupt.reason_message,
                }
                for interrupt in observation.snapshot.interrupts.values()
            ],
            "policy_decisions": [
                {
                    "decision_id": decision.decision_id,
                    "action": str(decision.action),
                    "policy_name": decision.policy_name,
                    "reason_code": decision.reason_code,
                    "reason_message": decision.reason_message,
                    "node_id": decision.node_id,
                }
                for decision in observation.snapshot.policy_decisions.values()
            ],
        }

    def run_eval_suite(self, suite_id: str) -> dict[str, object]:
        suite = self._find_suite(suite_id)
        runtime, _ = self._build_runtime()
        runner = EvaluationRunner(runtime, driver=EducationEvaluationDriver())
        case_results = [
            runner.run_case(
                case,
                scorers=build_default_education_eval_scorers(case),
                driver=EducationEvaluationDriver(),
            )
            for case in suite.cases
        ]
        suite_result = EvaluationSuiteResult(
            suite=suite,
            case_results=case_results,
            metadata={"suite_id": suite.suite_id, "suite_name": suite.name},
        )
        summary = SuiteMetricsAggregator().summarize(suite_result)
        return {
            "suite": {
                "suite_id": suite.suite_id,
                "name": suite.name,
                "case_ids": [case.case_id for case in suite.cases],
            },
            "summary": _json_ready(asdict(summary)),
            "cases": [self._serialize_case_result(result) for result in case_results],
        }

    def _serialize_case_result(self, result: EvaluationCaseResult) -> dict[str, object]:
        execution = result.execution
        return {
            "case_id": result.case.case_id,
            "title": result.case.title,
            "workflow_id": result.case.workflow_id,
            "status": str(result.status),
            "error_message": result.error_message,
            "metrics": [
                {
                    "metric_name": metric.metric_name,
                    "passed": metric.passed,
                    "value": _json_ready(metric.value),
                    "details": _json_ready(metric.details),
                }
                for metric in result.metrics
            ],
            "run_status": str(execution.run_record.status) if execution else None,
            "completed_nodes": (
                list(execution.final_state.run_state.completed_nodes) if execution else []
            ),
            "event_count": len(execution.events) if execution else 0,
        }

    def _find_suite(self, suite_id: str) -> EvaluationSuite:
        suites = {suite.suite_id: suite for suite in get_registered_eval_suites()}
        if suite_id not in suites:
            raise KeyError(f"unknown suite_id '{suite_id}'")
        return suites[suite_id]

    def _build_project_snapshot(self) -> dict[str, object]:
        overview = self.get_overview()
        return {
            "project": overview["project"],
            "domain_packs": overview["domain_packs"],
            "counts": overview["counts"],
            "agents": [
                {
                    "agent_id": item["agent_id"],
                    "name": item["name"],
                    "role": item["role"],
                    "domain": item.get("domain"),
                    "capabilities": item["capabilities"],
                    "tool_refs": item["tool_refs"],
                }
                for item in overview["agents"]
            ],
            "workflows": [
                {
                    "workflow_id": item["workflow_id"],
                    "name": item["name"],
                    "nodes": [
                        {
                            "node_id": node["node_id"],
                            "node_type": node["node_type"],
                            "agent_ref": node["agent_ref"],
                            "tool_ref": node["tool_ref"],
                        }
                        for node in item["nodes"]
                    ],
                }
                for item in overview["workflows"]
            ],
            "eval_suites": overview["eval_suites"],
        }

    def _build_local_assistant_reply(
        self,
        user_message: str,
        project_snapshot: dict[str, object],
    ) -> str:
        workflow_ids = [item["workflow_id"] for item in project_snapshot["workflows"]]
        return (
            "当前我已经能看到你的项目结构。教育域目前有 "
            f"{project_snapshot['counts']['agents']} 个 agent、"
            f"{project_snapshot['counts']['workflows']} 条 workflow、"
            f"{project_snapshot['counts']['tools']} 个 tool、"
            f"{project_snapshot['counts']['eval_suites']} 个评估套件。\n\n"
            "工作流运行方式：前端把 global_context 发给后端，后端创建 thread 和 run，"
            "再按 workflow 中的节点顺序执行 tool 节点和 agent 节点，"
            "最后把状态、artifact 和 timeline 返回给页面。\n\n"
            "评估运行方式：系统读取预定义 eval suite，逐个执行 case，"
            "用 scorer 判断 run 状态、关键节点和结果是否满足预期，最后汇总成通过率。\n\n"
            f"当前可直接测试的 workflow 有：{', '.join(workflow_ids)}。\n"
            f"你刚才的问题是：{user_message}\n\n"
            "如果你准备开始把项目真正用于教育场景，建议先从 diagnostic_plan 主链开始，"
            "确认 learner_profiler -> curriculum_planner -> tutor_coach 这一条能稳定返回 llm 模式结果。"
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

    def _preferred_assistant_profile_ref(self) -> str | None:
        bundle = EnvironmentProviderConfigLoader().load()
        profile_refs = {profile.profile_ref for profile in bundle.profiles}
        if "deepseek.default" in profile_refs:
            return "deepseek.default"
        if "openai.default" in profile_refs:
            return "openai.default"
        return bundle.default_profile_ref

    def _build_runtime(self) -> tuple[RuntimeService, RuntimeServices]:
        registry = InMemoryAgentRegistry()
        for descriptor in self._agent_config.configured_descriptors():
            registry.register(descriptor)

        workflow_provider = InMemoryWorkflowProvider()
        for definition in get_registered_workflow_definitions():
            workflow_provider.register(definition)

        tool_registry = InMemoryToolRegistry()
        for descriptor in get_registered_tool_descriptors():
            tool_registry.register(descriptor)

        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            tool_invoker=ObservedToolInvoker(
                RoutingToolInvoker(
                    registry=tool_registry,
                    adapters=[build_education_function_tool_adapter()],
                )
            ),
            llm_invoker=self._build_llm_invoker(),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=workflow_provider,
            node_executor=BasicNodeExecutor(
                delegates=[
                    ToolNodeExecutor(),
                    DomainAgentExecutor(get_registered_agent_implementations()),
                ]
            ),
            agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
        )
        return runtime, services


# Backward-compatible alias while the surrounding module names are still migrating.
EducationConsoleService = ProjectConsoleService
