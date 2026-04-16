from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import RuntimeServices
from core.executors import BasicNodeExecutor, ToolNodeExecutor
from core.observability import RuntimeQueryService
from core.policies import StaticPolicyEngine
from core.runtime import RuntimeService
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
    InputSelector,
    InputSource,
    InputSourceType,
    NodeSpec,
    WorkflowDefinition,
)
from core.state.models import NodeType


def _literal_selector(value: str = "seed") -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class ObservabilityQueryTestCase(unittest.TestCase):
    def test_query_service_returns_tool_views_and_timeline(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.obs.tool",
                name="Tool Observability",
                version="1.0.0",
                entry_node_id="search",
                node_specs=[
                    NodeSpec(
                        node_id="search",
                        node_type=NodeType.TOOL,
                        executor_ref="tool.search",
                        input_selector=_literal_selector("query"),
                        config={"tool_ref": "tool.search"},
                    )
                ],
                edge_specs=[],
            )
        )
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.search",
                name="Search",
                description="Search test tool",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                provider_ref="tests",
                operation_ref="search",
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.search", lambda tool_input, context: {"query": tool_input})
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

        thread = runtime.create_thread("task", "observability tool test")
        run = runtime.start_run(thread.thread_id, "wf.obs.tool")
        query = RuntimeQueryService(runtime)

        tool_events = query.list_tool_events(run.run_id)
        grouped = query.group_events_by_node(run.run_id)
        timeline = query.build_timeline(run.run_id)
        digest = query.build_digest(run.run_id)

        self.assertEqual([event.event_type for event in tool_events], [
            "tool.invocation.started",
            "tool.invocation.succeeded",
        ])
        self.assertIn("search", grouped)
        self.assertTrue(any(entry.source_kind == "side_effect" for entry in timeline))
        self.assertEqual(digest.tool_event_count, 2)
        self.assertEqual(digest.side_effect_count, 1)
        self.assertEqual(digest.completed_node_count, 1)

    def test_query_service_surfaces_policy_and_interrupt_views(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.obs.policy",
                name="Policy Observability",
                version="1.0.0",
                entry_node_id="lookup",
                node_specs=[
                    NodeSpec(
                        node_id="lookup",
                        node_type=NodeType.TOOL,
                        executor_ref="tool.lookup",
                        input_selector=_literal_selector("query"),
                        config={"tool_ref": "tool.lookup"},
                    )
                ],
                edge_specs=[],
            )
        )
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.lookup",
                name="Lookup",
                description="Lookup test tool",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                provider_ref="tests",
                operation_ref="lookup",
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.lookup", lambda request, context: {"ok": True})
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            policy_engine=StaticPolicyEngine(approval_tool_refs={"tool.lookup"}),
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

        thread = runtime.create_thread("task", "policy observability test")
        run = runtime.start_run(thread.thread_id, "wf.obs.policy")
        query = RuntimeQueryService(runtime)

        decisions = query.list_policy_decisions(run.run_id)
        interrupts = query.list_interrupts(run.run_id)
        timeline = query.build_timeline(run.run_id)
        digest = query.build_digest(run.run_id)

        self.assertEqual(len(decisions), 1)
        self.assertEqual(str(decisions[0].action), "require_approval")
        self.assertEqual(len(interrupts), 1)
        self.assertTrue(any(entry.source_kind == "policy_decision" for entry in timeline))
        self.assertTrue(any(entry.source_kind == "interrupt" for entry in timeline))
        self.assertEqual(digest.policy_decision_count, 1)
        self.assertEqual(digest.interrupt_count, 1)
