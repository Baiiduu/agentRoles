from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import NodeExecutionResult, RuntimeServices
from core.executors import BasicNodeExecutor, ToolNodeExecutor
from core.policies import StaticPolicyEngine
from core.runtime import RuntimeService
from core.state.models import NodeStatus, NodeType, PolicyAction, RunStatus, SideEffectKind, ThreadStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import (
    FunctionToolAdapter,
    InMemoryToolRegistry,
    ObservedToolInvoker,
    PolicyAwareToolInvoker,
    RoutingToolInvoker,
    ToolDescriptor,
    ToolTransportKind,
)
from core.workflow import InMemoryWorkflowProvider
from core.workflow.workflow_models import (
    ApprovalPolicy,
    ApproverType,
    EdgeCondition,
    EdgeConditionType,
    EdgeSpec,
    InputSelector,
    InputSource,
    InputSourceType,
    JoinPolicy,
    JoinPolicyKind,
    MergeMode,
    MergeStrategySpec,
    NodeSpec,
    OutputBinding,
    TerminalCondition,
    TerminalConditionType,
    WorkflowDefinition,
)


class SuccessExecutor:
    def can_execute(self, node_type, executor_ref):
        return True

    def execute(self, context):
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output={"node": context.node_state.node_id},
        )


class RuntimeE2ETestCase(unittest.TestCase):
    def _runtime(
        self,
        definition: WorkflowDefinition,
        *,
        node_executor=None,
    ) -> tuple[RuntimeService, RuntimeServices]:
        provider = InMemoryWorkflowProvider()
        provider.register(definition)
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=node_executor or BasicNodeExecutor(),
        )
        return runtime, services

    def _literal_selector(self, value: str = "seed") -> InputSelector:
        return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])

    def test_sequential_workflow_completes(self) -> None:
        runtime, _ = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.sequential",
                name="Sequential",
                version="1.0.0",
                entry_node_id="start",
                node_specs=[
                    NodeSpec(
                        node_id="start",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("start"),
                    ),
                    NodeSpec(
                        node_id="finish",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("finish"),
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="start", to_node_id="finish")
                ],
            )
        )
        thread = runtime.create_thread("task", "sequential goal")
        run = runtime.start_run(thread.thread_id, "wf.sequential")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(state.run_state.status, RunStatus.COMPLETED)
        self.assertEqual(set(state.run_state.completed_nodes), {"start", "finish"})
        self.assertEqual(state.thread_state.thread_status, ThreadStatus.ACTIVE)

    def test_condition_branch_selects_matching_path(self) -> None:
        runtime, _ = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.condition",
                name="Condition",
                version="1.0.0",
                entry_node_id="seed",
                node_specs=[
                    NodeSpec(
                        node_id="seed",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("seed"),
                        output_binding=OutputBinding(artifact_type="seed"),
                        config={"output": {"score": 88}},
                    ),
                    NodeSpec(
                        node_id="decide",
                        node_type=NodeType.CONDITION,
                        executor_ref="builtin.condition",
                        input_selector=InputSelector(
                            sources=[InputSource(InputSourceType.ARTIFACT, "seed")]
                        ),
                        output_binding=OutputBinding(artifact_type="decision"),
                        config={
                            "operand_path": "score",
                            "operator": "gte",
                            "value": 60,
                            "branches": {"true": "pass", "false": "fail"},
                        },
                    ),
                    NodeSpec(
                        node_id="pass",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("pass"),
                    ),
                    NodeSpec(
                        node_id="fail",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("fail"),
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e_seed", from_node_id="seed", to_node_id="decide"),
                    EdgeSpec(
                        edge_id="e_true",
                        from_node_id="decide",
                        to_node_id="pass",
                        condition=EdgeCondition(
                            condition_type=EdgeConditionType.RESULT_FIELD_EQUALS,
                            operand_path="matched",
                            expected_value=True,
                        ),
                    ),
                    EdgeSpec(
                        edge_id="e_false",
                        from_node_id="decide",
                        to_node_id="fail",
                        condition=EdgeCondition(
                            condition_type=EdgeConditionType.RESULT_FIELD_EQUALS,
                            operand_path="matched",
                            expected_value=False,
                        ),
                    ),
                ],
                terminal_conditions=[
                    TerminalCondition(
                        condition_type=TerminalConditionType.EXPLICIT_NODE_COMPLETED,
                        node_id="pass",
                    ),
                    TerminalCondition(
                        condition_type=TerminalConditionType.EXPLICIT_NODE_COMPLETED,
                        node_id="fail",
                    ),
                ],
            )
        )
        thread = runtime.create_thread("task", "condition goal")
        run = runtime.start_run(thread.thread_id, "wf.condition")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertIn("pass", state.run_state.completed_nodes)
        self.assertNotIn("fail", state.run_state.completed_nodes)
        self.assertEqual(state.node_states["pass"].status, NodeStatus.SUCCEEDED)
        self.assertEqual(state.node_states["fail"].status, NodeStatus.PENDING)

    def test_parallel_fanout_merge_workflow_completes(self) -> None:
        runtime, _ = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.merge",
                name="Merge",
                version="1.0.0",
                entry_node_id="seed",
                node_specs=[
                    NodeSpec(
                        node_id="seed",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("seed"),
                    ),
                    NodeSpec(
                        node_id="left",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("left"),
                        output_binding=OutputBinding(artifact_type="branch"),
                        config={"output": {"branch": "left", "score": 1}},
                    ),
                    NodeSpec(
                        node_id="right",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("right"),
                        output_binding=OutputBinding(artifact_type="branch"),
                        config={"output": {"branch": "right", "score": 2}},
                    ),
                    NodeSpec(
                        node_id="merge",
                        node_type=NodeType.MERGE,
                        executor_ref="builtin.merge",
                        input_selector=self._literal_selector("merge"),
                        join_policy=JoinPolicy(kind=JoinPolicyKind.ALL_SUCCESS),
                        merge_strategy=MergeStrategySpec(mode=MergeMode.COLLECT_LIST),
                        output_binding=OutputBinding(artifact_type="merged"),
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="seed", to_node_id="left"),
                    EdgeSpec(edge_id="e2", from_node_id="seed", to_node_id="right"),
                    EdgeSpec(edge_id="e3", from_node_id="left", to_node_id="merge"),
                    EdgeSpec(edge_id="e4", from_node_id="right", to_node_id="merge"),
                ],
            )
        )
        thread = runtime.create_thread("task", "merge goal")
        run = runtime.start_run(thread.thread_id, "wf.merge")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(state.node_states["merge"].status, NodeStatus.SUCCEEDED)
        self.assertIsNotNone(state.node_states["merge"].output_artifact_id)
        merged_artifact = state.artifacts[state.node_states["merge"].output_artifact_id]
        self.assertEqual(merged_artifact.payload_inline["count"], 2)
        self.assertEqual(len(merged_artifact.payload_inline["items"]), 2)

    def test_human_gate_interrupt_and_resume(self) -> None:
        runtime, _ = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.gate",
                name="Gate",
                version="1.0.0",
                entry_node_id="approve",
                node_specs=[
                    NodeSpec(
                        node_id="approve",
                        node_type=NodeType.HUMAN_GATE,
                        executor_ref="builtin.human_gate",
                        input_selector=InputSelector(
                            sources=[
                                InputSource(
                                    InputSourceType.INTERRUPT_RESOLUTION,
                                    "approve",
                                    required=False,
                                )
                            ]
                        ),
                        approval_policy=ApprovalPolicy(
                            required=True,
                            approver_type=ApproverType.HUMAN,
                            approval_reason_code="needs_approval",
                        ),
                    )
                ],
                edge_specs=[],
            )
        )
        thread = runtime.create_thread("task", "approval goal")
        run = runtime.start_run(thread.thread_id, "wf.gate")
        interrupted_state = runtime.get_state(run.run_id)

        self.assertEqual(interrupted_state.run_record.status, RunStatus.INTERRUPTED)
        self.assertEqual(interrupted_state.thread_state.thread_status, ThreadStatus.PAUSED)
        self.assertEqual(len(interrupted_state.run_state.pending_interrupt_ids), 1)

        resumed = runtime.resume_run(run.run_id, {"approved": True, "comment": "ok"})
        final_state = runtime.get_state(resumed.run_id)

        self.assertEqual(final_state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(final_state.node_states["approve"].status, NodeStatus.SUCCEEDED)
        self.assertEqual(final_state.run_state.pending_interrupt_ids, [])
        self.assertEqual(final_state.thread_state.thread_status, ThreadStatus.ACTIVE)

    def test_no_progress_marks_run_failed(self) -> None:
        runtime, _ = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.no_progress",
                name="No Progress",
                version="1.0.0",
                entry_node_id="start",
                node_specs=[
                    NodeSpec(
                        node_id="start",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("start"),
                    ),
                    NodeSpec(
                        node_id="orphan",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("orphan"),
                    ),
                ],
                edge_specs=[],
            )
        )
        thread = runtime.create_thread("task", "deadlock goal")
        run = runtime.start_run(thread.thread_id, "wf.no_progress")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.FAILED)
        self.assertEqual(state.run_record.failure_code, "NO_PROGRESS")
        self.assertIsNone(state.thread_record.current_run_id)

    def test_checkpoint_restore_contains_runtime_snapshot_ids(self) -> None:
        runtime, services = self._runtime(
            WorkflowDefinition(
                workflow_id="wf.checkpoint",
                name="Checkpoint",
                version="1.0.0",
                entry_node_id="start",
                node_specs=[
                    NodeSpec(
                        node_id="start",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=self._literal_selector("start"),
                        output_binding=OutputBinding(artifact_type="result"),
                        config={"output": {"value": 1}},
                    )
                ],
                edge_specs=[],
            )
        )
        thread = runtime.create_thread("task", "checkpoint goal")
        run = runtime.start_run(thread.thread_id, "wf.checkpoint")
        state = runtime.get_state(run.run_id)
        checkpoint_store = services.checkpoint_store
        latest = checkpoint_store.latest(run.run_id)
        self.assertIsNotNone(latest)
        payload = checkpoint_store.restore(latest.checkpoint_id)

        self.assertEqual(payload.run_record.run_id, run.run_id)
        self.assertEqual(payload.thread_record.thread_id, thread.thread_id)
        self.assertEqual(len(payload.node_states), 1)
        self.assertEqual(payload.artifact_ids, list(state.artifacts))
        self.assertEqual(payload.interrupt_ids, [])

    def test_tool_node_uses_tool_invoker(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.tool",
                name="Tool Workflow",
                version="1.0.0",
                entry_node_id="search",
                node_specs=[
                    NodeSpec(
                        node_id="search",
                        node_type=NodeType.TOOL,
                        executor_ref="tool.search",
                        input_selector=InputSelector(
                            sources=[InputSource(InputSourceType.LITERAL, "langgraph")],
                        ),
                        output_binding=OutputBinding(artifact_type="tool/result"),
                    )
                ],
                edge_specs=[],
            )
        )

        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="search",
                name="Search",
                description="Search docs",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                side_effect_kind=SideEffectKind.READ_ONLY,
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler(
            "search",
            lambda payload, context: {
                "query": payload["value"],
                "raw_input": payload,
                "node": context.node_state.node_id,
            },
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            tool_invoker=ObservedToolInvoker(
                RoutingToolInvoker(registry=registry, adapters=[adapter])
            ),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[ToolNodeExecutor()]),
        )

        thread = runtime.create_thread("task", "tool goal")
        run = runtime.start_run(thread.thread_id, "wf.tool")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(state.node_states["search"].status, NodeStatus.SUCCEEDED)
        artifact = state.artifacts[state.node_states["search"].output_artifact_id]
        self.assertEqual(artifact.payload_inline["query"], "langgraph")
        self.assertEqual(artifact.payload_inline["raw_input"]["value"], "langgraph")
        self.assertEqual(artifact.payload_inline["node"], "search")
        self.assertEqual(len(state.side_effects), 1)
        side_effect = next(iter(state.side_effects.values()))
        self.assertEqual(side_effect.target_type, "tool")
        self.assertEqual(side_effect.target_ref, "search")
        self.assertEqual(side_effect.action, "invoke")
        self.assertTrue(side_effect.succeeded)
        events = list(runtime.stream_events(run.run_id))
        event_types = [item.event_type for item in events]
        self.assertIn("tool.invocation.started", event_types)
        self.assertIn("tool.invocation.succeeded", event_types)
        tool_started = next(item for item in events if item.event_type == "tool.invocation.started")
        tool_finished = next(item for item in events if item.event_type == "tool.invocation.succeeded")
        self.assertEqual(tool_started.trace_id, run.run_id)
        self.assertEqual(tool_finished.trace_id, run.run_id)
        self.assertEqual(tool_started.span_id, tool_finished.span_id)
        self.assertEqual(tool_started.parent_span_id, f"node:search:1")

    def test_tool_policy_require_approval_interrupts_run(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.tool.approval",
                name="Tool Approval Workflow",
                version="1.0.0",
                entry_node_id="delete",
                node_specs=[
                    NodeSpec(
                        node_id="delete",
                        node_type=NodeType.TOOL,
                        executor_ref="tool.delete",
                        input_selector=InputSelector(
                            sources=[InputSource(InputSourceType.LITERAL, "/tmp/demo")],
                        ),
                        output_binding=OutputBinding(artifact_type="tool/result"),
                    )
                ],
                edge_specs=[],
            )
        )

        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="delete",
                name="Delete",
                description="Delete path",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                side_effect_kind=SideEffectKind.LOCAL_WRITE,
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("delete", lambda payload, context: {"deleted": payload["value"]})
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            policy_engine=StaticPolicyEngine(approval_tool_refs={"delete"}),
            tool_invoker=ObservedToolInvoker(
                PolicyAwareToolInvoker(
                    RoutingToolInvoker(registry=registry, adapters=[adapter])
                )
            ),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[ToolNodeExecutor()]),
        )

        thread = runtime.create_thread("task", "tool approval goal")
        run = runtime.start_run(thread.thread_id, "wf.tool.approval")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.INTERRUPTED)
        self.assertEqual(state.node_states["delete"].status, NodeStatus.WAITING)
        self.assertEqual(len(state.run_state.pending_interrupt_ids), 1)
        self.assertEqual(len(state.policy_decisions), 1)
        decision = next(iter(state.policy_decisions.values()))
        self.assertEqual(decision.action, PolicyAction.REQUIRE_APPROVAL)


if __name__ == "__main__":
    unittest.main()
