from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.runtime.skill_policy_engine import SkillRuntimePolicyEngine
from core.contracts import ExecutionContext, RuntimeServices
from core.state.models import NodeState, NodeStatus, NodeType, PolicyAction, RunRecord, RunState, RunStatus, SideEffectKind, ThreadRecord, ThreadState, ThreadStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import FunctionToolAdapter, PolicyAwareToolInvoker, RoutingToolInvoker, ToolApprovalMode, ToolDescriptor, ToolTransportKind
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec


def _context(runtime_resource_context: dict[str, object], *, message: str) -> ExecutionContext:
    from core.agents.bindings import ResolvedAgentBinding

    thread_record = ThreadRecord(thread_id="thread_1", thread_type="task", status=ThreadStatus.ACTIVE)
    run_record = RunRecord(
        run_id="run_1",
        thread_id="thread_1",
        workflow_id="wf.skills.policy",
        workflow_version="1.0.0",
        status=RunStatus.RUNNING,
        entry_node_id="tool_node",
    )
    thread_state = ThreadState(
        thread_id="thread_1",
        goal="exercise skill policy",
        active_run_id="run_1",
        thread_status=ThreadStatus.ACTIVE,
    )
    run_state = RunState(
        run_id="run_1",
        thread_id="thread_1",
        workflow_id="wf.skills.policy",
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
        workflow_id="wf.skills.policy",
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
        policy_engine=SkillRuntimePolicyEngine(),
    )
    binding = ResolvedAgentBinding(
        node_id="agent",
        agent_ref="agent.test",
        resolved_agent_id="agent.test",
        resolved_version="1.0.0",
        executor_ref="agent.domain",
        implementation_ref="agent.impl",
        tool_refs=["tool.read", "tool.write"],
        metadata={"runtime_resource_context": runtime_resource_context},
    )
    return ExecutionContext(
        thread_record=thread_record,
        run_record=run_record,
        thread_state=thread_state,
        run_state=run_state,
        node_state=node_state,
        workflow=workflow,
        node_spec=node_spec,
        agent_binding=binding,
        selected_input={"message": message},
        services=services,
    )


class SkillPolicyEngineTests(unittest.TestCase):
    def test_human_confirmed_active_skill_requires_approval_for_write_tool(self) -> None:
        registry = RoutingToolInvoker(
            registry=_tool_registry(
                ToolDescriptor(
                    tool_ref="tool.write",
                    name="Write",
                    description="Write a file",
                    transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                    approval_mode=ToolApprovalMode.NONE,
                    side_effect_kind=SideEffectKind.LOCAL_WRITE,
                )
            ),
            adapters=[_tool_adapter("tool.write")],
        )
        invoker = PolicyAwareToolInvoker(registry)
        context = _context(
            {
                "skill_packages": [
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "trigger_kinds": ["dependency", "audit"],
                        "execution_mode": "human_confirmed",
                    }
                ]
            },
            message="please run a dependency audit",
        )

        result = invoker.invoke("tool.write", {"path": "a.txt"}, context)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "POLICY_APPROVAL_REQUIRED")
        self.assertEqual(result.policy_decisions[0].action, PolicyAction.REQUIRE_APPROVAL)
        self.assertEqual(
            result.policy_decisions[0].reason_code,
            "skill_human_confirmation_required",
        )

    def test_human_confirmed_active_skill_still_allows_read_only_tool(self) -> None:
        registry = RoutingToolInvoker(
            registry=_tool_registry(
                ToolDescriptor(
                    tool_ref="tool.read",
                    name="Read",
                    description="Read a file",
                    transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                )
            ),
            adapters=[_tool_adapter("tool.read")],
        )
        invoker = PolicyAwareToolInvoker(registry)
        context = _context(
            {
                "skill_packages": [
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "trigger_kinds": ["dependency", "audit"],
                        "execution_mode": "human_confirmed",
                    }
                ]
            },
            message="please run a dependency audit",
        )

        result = invoker.invoke("tool.read", {"path": "a.txt"}, context)

        self.assertTrue(result.success)
        self.assertEqual(result.policy_decisions[0].action, PolicyAction.ALLOW)

    def test_auto_skill_does_not_require_approval_for_write_tool(self) -> None:
        registry = RoutingToolInvoker(
            registry=_tool_registry(
                ToolDescriptor(
                    tool_ref="tool.write",
                    name="Write",
                    description="Write a file",
                    transport_kind=ToolTransportKind.LOCAL_FUNCTION,
                    approval_mode=ToolApprovalMode.NONE,
                    side_effect_kind=SideEffectKind.LOCAL_WRITE,
                )
            ),
            adapters=[_tool_adapter("tool.write")],
        )
        invoker = PolicyAwareToolInvoker(registry)
        context = _context(
            {
                "skill_packages": [
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "trigger_kinds": ["dependency", "audit"],
                        "execution_mode": "auto",
                    }
                ]
            },
            message="please run a dependency audit",
        )

        result = invoker.invoke("tool.write", {"path": "a.txt"}, context)

        self.assertTrue(result.success)
        self.assertEqual(result.policy_decisions[0].action, PolicyAction.ALLOW)


def _tool_registry(descriptor: ToolDescriptor):
    from core.tools import InMemoryToolRegistry

    registry = InMemoryToolRegistry()
    registry.register(descriptor)
    return registry


def _tool_adapter(tool_ref: str) -> FunctionToolAdapter:
    adapter = FunctionToolAdapter()
    adapter.register_handler(tool_ref, lambda payload, context: {"ok": True, "payload": payload})
    return adapter


if __name__ == "__main__":
    unittest.main()
