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


class BoundAgentExecutor:
    def can_execute(self, node_type, executor_ref):
        return node_type == NodeType.AGENT and executor_ref.startswith("agent.")

    def execute(self, context):
        binding = context.agent_binding
        if binding is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code="MISSING_AGENT_BINDING",
                error_message="agent binding is required",
            )
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output={
                "agent_id": binding.resolved_agent_id,
                "version": binding.resolved_version,
                "executor_ref": binding.executor_ref,
                "capabilities": list(binding.capabilities),
            },
        )


class AgentBindingResolverTestCase(unittest.TestCase):
    def test_resolver_builds_binding_from_registry(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.1.0",
                role="planner",
                description="Builds lesson plans",
                executor_ref="agent.teacher_planner",
                tool_refs=["tool.search"],
                memory_scopes=["domain:education"],
                policy_profiles=["edu_default"],
                capabilities=["lesson_planning"],
            )
        )
        resolver = RegistryBackedAgentBindingResolver(registry)
        node = NodeSpec(
            node_id="plan",
            node_type=NodeType.AGENT,
            executor_ref="agent.placeholder",
            agent_ref="teacher_planner",
            input_selector=_literal_selector("plan"),
        )

        binding = resolver.resolve_node_binding(node)

        self.assertIsNotNone(binding)
        self.assertEqual(binding.resolved_agent_id, "teacher_planner")
        self.assertEqual(binding.resolved_version, "1.1.0")
        self.assertEqual(binding.executor_ref, "agent.teacher_planner")
        self.assertEqual(binding.capabilities, ["lesson_planning"])

    def test_runtime_can_freeze_agent_binding_into_run_state_and_context(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="2.0.0",
                role="planner",
                description="Builds lesson plans",
                executor_ref="agent.teacher_planner",
                capabilities=["lesson_planning", "curriculum_alignment"],
                tool_refs=["tool.search"],
                memory_scopes=["domain:education"],
            )
        )
        resolver = RegistryBackedAgentBindingResolver(registry)

        workflows = InMemoryWorkflowProvider()
        workflows.register(
            WorkflowDefinition(
                workflow_id="wf.agent.binding",
                name="Agent Binding Workflow",
                version="1.0.0",
                entry_node_id="plan",
                node_specs=[
                    NodeSpec(
                        node_id="plan",
                        node_type=NodeType.AGENT,
                        executor_ref="agent.placeholder",
                        agent_ref="teacher_planner",
                        input_selector=_literal_selector("plan"),
                        output_binding=OutputBinding(artifact_type="plan"),
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
            node_executor=BoundAgentExecutor(),
            agent_binding_resolver=resolver,
        )

        thread = runtime.create_thread("task", "agent binding integration")
        run = runtime.start_run(thread.thread_id, "wf.agent.binding")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        binding_payload = state.run_state.extensions["agent_bindings"]["agent_bindings_by_node"][
            "plan"
        ]
        self.assertEqual(binding_payload["resolved_agent_id"], "teacher_planner")
        self.assertEqual(binding_payload["resolved_version"], "2.0.0")
        artifact = state.artifacts[state.node_states["plan"].output_artifact_id]
        self.assertEqual(artifact.payload_inline["agent_id"], "teacher_planner")
        self.assertEqual(artifact.payload_inline["executor_ref"], "agent.teacher_planner")

    def test_runtime_rejects_agent_ref_without_binding_resolver(self) -> None:
        workflows = InMemoryWorkflowProvider()
        workflows.register(
            WorkflowDefinition(
                workflow_id="wf.agent.noresolver",
                name="Agent No Resolver",
                version="1.0.0",
                entry_node_id="plan",
                node_specs=[
                    NodeSpec(
                        node_id="plan",
                        node_type=NodeType.AGENT,
                        executor_ref="agent.placeholder",
                        agent_ref="teacher_planner",
                        input_selector=_literal_selector("plan"),
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
            node_executor=BoundAgentExecutor(),
        )
        thread = runtime.create_thread("task", "missing binding resolver")

        with self.assertRaises(ValueError):
            runtime.start_run(thread.thread_id, "wf.agent.noresolver")

    def test_non_agent_node_cannot_declare_agent_ref(self) -> None:
        with self.assertRaises(ValueError):
            NodeSpec(
                node_id="bad",
                node_type=NodeType.NOOP,
                executor_ref="builtin.noop",
                agent_ref="teacher_planner",
                input_selector=_literal_selector("bad"),
            )
