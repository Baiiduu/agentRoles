from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents import (
    AgentDescriptor,
    InMemoryAgentRegistry,
    RegistryBackedAgentBindingResolver,
)
from core.contracts import NodeExecutionResult, RuntimeServices
from core.executors import BasicNodeExecutor, DomainAgentExecutor
from core.runtime import RuntimeService
from core.state.models import NodeStatus, NodeType, RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.workflow import InMemoryWorkflowProvider
from core.workflow.workflow_models import (
    InputSelector,
    InputSource,
    InputSourceType,
    NodeSpec,
    OutputBinding,
    WorkflowDefinition,
)


def _literal_selector(value: str = "seed") -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class EducationPlannerImplementation:
    implementation_ref = "education.teacher_planner"

    def can_handle(self, binding) -> bool:
        return "lesson_planning" in binding.capabilities

    def invoke(self, context):
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output={
                "kind": "lesson_plan",
                "agent_id": context.agent_binding.resolved_agent_id,
                "version": context.agent_binding.resolved_version,
                "implementation_ref": context.agent_binding.implementation_ref,
            },
        )


class SupplyChainFallbackImplementation:
    implementation_ref = "supply.sbom_analyst"

    def can_handle(self, binding) -> bool:
        return "sbom_analysis" in binding.capabilities

    def invoke(self, context):
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output={"kind": "sbom_analysis"},
        )


class DomainAgentExecutorTestCase(unittest.TestCase):
    def test_domain_agent_executor_routes_by_implementation_ref(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.0.0",
                role="planner",
                description="Creates lesson plans",
                executor_ref="agent.domain",
                implementation_ref="education.teacher_planner",
                capabilities=["lesson_planning"],
            )
        )
        workflows = InMemoryWorkflowProvider()
        workflows.register(
            WorkflowDefinition(
                workflow_id="wf.domain.agent",
                name="Domain Agent",
                version="1.0.0",
                entry_node_id="plan",
                node_specs=[
                    NodeSpec(
                        node_id="plan",
                        node_type=NodeType.AGENT,
                        executor_ref="agent.placeholder",
                        agent_ref="teacher_planner",
                        input_selector=_literal_selector("plan"),
                        output_binding=OutputBinding(artifact_type="lesson_plan"),
                    )
                ],
                edge_specs=[],
            )
        )
        runtime = RuntimeService(
            services=RuntimeServices(
                state_store=InMemoryStateStore(),
                event_store=InMemoryEventStore(),
                checkpoint_store=InMemoryCheckpointStore(),
            ),
            workflow_provider=workflows,
            node_executor=BasicNodeExecutor(
                delegates=[
                    DomainAgentExecutor(
                        implementations=[
                            EducationPlannerImplementation(),
                            SupplyChainFallbackImplementation(),
                        ]
                    )
                ]
            ),
            agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
        )

        thread = runtime.create_thread("task", "education domain entry")
        run = runtime.start_run(thread.thread_id, "wf.domain.agent")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        artifact = state.artifacts[state.node_states["plan"].output_artifact_id]
        self.assertEqual(artifact.payload_inline["agent_id"], "teacher_planner")
        self.assertEqual(
            artifact.payload_inline["implementation_ref"], "education.teacher_planner"
        )

    def test_domain_agent_executor_fails_without_binding(self) -> None:
        executor = DomainAgentExecutor(implementations=[EducationPlannerImplementation()])

        class _Context:
            agent_binding = None

        result = executor.execute(_Context())

        self.assertEqual(result.status, NodeStatus.FAILED)
        self.assertEqual(result.error_code, "MISSING_AGENT_BINDING")

    def test_domain_agent_executor_raises_when_no_implementation_matches(self) -> None:
        executor = DomainAgentExecutor(implementations=[EducationPlannerImplementation()])

        class _Binding:
            agent_ref = "sbom_analyst"
            implementation_ref = "supply.sbom_analyst"
            capabilities = ["sbom_analysis"]

        with self.assertRaises(ValueError):
            executor._select_implementation(_Binding())
