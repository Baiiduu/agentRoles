from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import ExecutionContext, RuntimeServices
from core.policies import StaticPolicyEngine
from core.state.models import (
    PolicyAction,
    NodeState,
    NodeStatus,
    NodeType,
    RunRecord,
    RunState,
    RunStatus,
    ThreadRecord,
    ThreadState,
    ThreadStatus,
)
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import (
    FunctionToolAdapter,
    InMemoryMCPGateway,
    InMemoryToolRegistry,
    MCPServerDescriptor,
    MCPToolAdapter,
    MCPTransportKind,
    ObservedToolInvoker,
    PolicyAwareToolInvoker,
    RoutingToolInvoker,
    ToolDescriptor,
    ToolQuery,
    ToolTransportKind,
)
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec


class ToolLayerTestCase(unittest.TestCase):
    def _context(self) -> ExecutionContext:
        thread_record = ThreadRecord(thread_id="thread_1", thread_type="task", status=ThreadStatus.ACTIVE)
        run_record = RunRecord(
            run_id="run_1",
            thread_id="thread_1",
            workflow_id="wf.tools",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
            entry_node_id="tool_node",
        )
        thread_state = ThreadState(
            thread_id="thread_1",
            goal="exercise tool layer",
            active_run_id="run_1",
            thread_status=ThreadStatus.ACTIVE,
        )
        run_state = RunState(
            run_id="run_1",
            thread_id="thread_1",
            workflow_id="wf.tools",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
            frontier=["tool_node"],
        )
        node_state = NodeState(
            run_id="run_1",
            node_id="tool_node",
            node_type=NodeType.TOOL,
            status=NodeStatus.RUNNING,
            attempt=1,
            executor_ref="tool.executor",
            started_at=datetime.now(UTC),
        )
        node_spec = NodeSpec(
            node_id="tool_node",
            node_type=NodeType.TOOL,
            executor_ref="tool.executor",
            input_selector=InputSelector(
                sources=[InputSource(InputSourceType.LITERAL, "seed")],
            ),
        )
        workflow = CompiledWorkflow(
            workflow_id="wf.tools",
            version="1.0.0",
            entry_node_id="tool_node",
            node_map={"tool_node": node_spec},
            outgoing_edges={"tool_node": []},
            incoming_edges={"tool_node": []},
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
        )
        return ExecutionContext(
            thread_record=thread_record,
            run_record=run_record,
            thread_state=thread_state,
            run_state=run_state,
            node_state=node_state,
            workflow=workflow,
            node_spec=node_spec,
            services=services,
        )

    def test_function_tool_invoker_routes_local_descriptor(self) -> None:
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.echo",
                name="Echo",
                description="Echo payloads",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                tags=["utility", "local"],
            )
        )

        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.echo", lambda payload, context: {"echo": payload, "node": context.node_state.node_id})
        invoker = RoutingToolInvoker(registry=registry, adapters=[adapter])

        result = invoker.invoke("tool.echo", {"message": "hello"}, self._context())

        self.assertTrue(result.success)
        self.assertEqual(result.output["echo"]["message"], "hello")
        self.assertEqual(result.output["node"], "tool_node")
        self.assertEqual(result.metadata["adapter_ref"], "adapter.function")
        self.assertEqual(invoker.get_descriptor("tool.echo").name, "Echo")
        listed = invoker.list_tools(ToolQuery(tags=["utility"]))
        self.assertEqual([item.tool_ref for item in listed], ["tool.echo"])

    def test_mcp_tool_adapter_routes_registered_server(self) -> None:
        gateway = InMemoryMCPGateway()
        gateway.register_server(
            MCPServerDescriptor(
                server_ref="mcp.lab",
                transport_kind=MCPTransportKind.STDIO,
                command=["python"],
                args=["server.py"],
            )
        )
        descriptor = ToolDescriptor(
            tool_ref="tool.search",
            name="Search",
            description="Search through MCP",
            transport_kind=ToolTransportKind.MCP,
            provider_ref="mcp.lab",
            operation_ref="search_docs",
            tags=["search", "mcp"],
        )
        gateway.register_tool(descriptor)
        gateway.register_handler(
            "mcp.lab",
            "search_docs",
            lambda payload, context: {
                "query": payload["query"],
                "run_id": context.run_record.run_id if context is not None else None,
            },
        )

        registry = InMemoryToolRegistry()
        registry.register(descriptor)
        invoker = RoutingToolInvoker(
            registry=registry,
            adapters=[MCPToolAdapter(gateway)],
        )

        result = invoker.invoke("tool.search", {"query": "langgraph"}, self._context())

        self.assertTrue(result.success)
        self.assertEqual(result.output["query"], "langgraph")
        self.assertEqual(result.output["run_id"], "run_1")
        self.assertEqual(result.metadata["adapter_ref"], "adapter.mcp")
        self.assertEqual(result.metadata["server_ref"], "mcp.lab")

    def test_missing_tool_returns_structured_error(self) -> None:
        invoker = RoutingToolInvoker(registry=InMemoryToolRegistry(), adapters=[FunctionToolAdapter()])

        result = invoker.invoke("tool.missing", {"value": 1}, self._context())

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "TOOL_NOT_FOUND")

    def test_policy_aware_tool_invoker_denies_tool(self) -> None:
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.delete",
                name="Delete",
                description="Dangerous delete",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.delete", lambda payload, context: {"deleted": True})

        context = self._context()
        context.services.policy_engine = StaticPolicyEngine(deny_tool_refs={"tool.delete"})
        invoker = PolicyAwareToolInvoker(
            RoutingToolInvoker(registry=registry, adapters=[adapter])
        )

        result = invoker.invoke("tool.delete", {"path": "/tmp/demo"}, context)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "POLICY_DENIED")
        self.assertEqual(len(result.policy_decisions), 1)
        self.assertEqual(result.policy_decisions[0].action, PolicyAction.DENY)

    def test_policy_aware_tool_invoker_redacts_input(self) -> None:
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.audit",
                name="Audit",
                description="Audit record",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.audit", lambda payload, context: {"payload": payload})

        context = self._context()
        context.services.policy_engine = StaticPolicyEngine(
            redact_tool_refs={"tool.audit": ["secret.token"]}
        )
        invoker = PolicyAwareToolInvoker(
            RoutingToolInvoker(registry=registry, adapters=[adapter])
        )

        result = invoker.invoke(
            "tool.audit",
            {"secret": {"token": "abc", "keep": "ok"}},
            context,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.policy_decisions[0].action, PolicyAction.REDACT)
        self.assertNotIn("token", result.output["payload"]["secret"])
        self.assertEqual(result.output["payload"]["secret"]["keep"], "ok")

    def test_observed_tool_invoker_emits_trace_side_effect(self) -> None:
        registry = InMemoryToolRegistry()
        registry.register(
            ToolDescriptor(
                tool_ref="tool.echo.trace",
                name="Echo Trace",
                description="Echo with trace",
                transport_kind=ToolTransportKind.LOCAL_FUNCTION,
            )
        )
        adapter = FunctionToolAdapter()
        adapter.register_handler("tool.echo.trace", lambda payload, context: {"echo": payload})
        invoker = ObservedToolInvoker(
            RoutingToolInvoker(registry=registry, adapters=[adapter])
        )
        context = self._context()

        result = invoker.invoke("tool.echo.trace", {"message": "hello"}, context)

        self.assertTrue(result.success)
        self.assertIn("observability", result.metadata)
        self.assertIn("duration_ms", result.metadata["observability"])
        self.assertEqual(len(result.side_effects), 1)
        trace = result.side_effects[0]
        self.assertEqual(trace.target_type, "tool")
        self.assertEqual(trace.target_ref, "tool.echo.trace")
        self.assertEqual(trace.action, "invoke")
        self.assertTrue(trace.succeeded)
        events = context.services.event_store.list_by_run("run_1")
        self.assertEqual([item.event_type for item in events], ["tool.invocation.started", "tool.invocation.succeeded"])
        self.assertEqual(events[0].trace_id, events[1].trace_id)
        self.assertEqual(events[0].span_id, events[1].span_id)


if __name__ == "__main__":
    unittest.main()
