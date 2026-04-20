from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents.bindings import ResolvedAgentBinding
from core.contracts import ExecutionContext, MemoryResult, RuntimeServices, ToolInvocationResult
from core.llm import LLMResult
from core.state.models import NodeState, NodeStatus, NodeType, RunRecord, RunStatus, RunState, ThreadRecord, ThreadState
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools.models import ToolDescriptor, ToolTransportKind
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec, OutputBinding
from domain_packs.operations import OPERATION_TOOL_REFS
from domain_packs.test_pro import TestProDomainPack
from domain_packs.test_pro.agents.implementations import TestProChatImplementation


def _literal_selector(value: str) -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class _FakeLLMInvoker:
    def __init__(self, results: list[LLMResult]) -> None:
        self._results = list(results)
        self.requests = []

    def invoke(self, request, context=None):
        self.requests.append(request)
        if not self._results:
            raise AssertionError("unexpected extra llm invoke")
        return self._results.pop(0)


class _FakeToolInvoker:
    def __init__(self) -> None:
        self.calls = []

    def invoke(self, tool_ref: str, tool_input: dict[str, object], context: ExecutionContext):
        self.calls.append((tool_ref, tool_input))
        return ToolInvocationResult(
            success=True,
            output={
                "path": tool_input.get("path", ""),
                "tool_ref": tool_ref,
                "observed": True,
            },
        )

    def get_descriptor(self, tool_ref: str):
        return ToolDescriptor(
            tool_ref=tool_ref,
            name=tool_ref,
            description="fake tool",
            transport_kind=ToolTransportKind.LOCAL_FUNCTION,
        )

    def list_tools(self, query=None):
        return []


class _FakeMemoryProvider:
    def __init__(self) -> None:
        self.retrieve_calls = []
        self.write_calls = []

    def retrieve(self, query: str, scope: str, *, top_k: int = 5, context=None):
        self.retrieve_calls.append((query, scope, top_k))
        if scope.endswith("thread-1"):
            return [
                MemoryResult(
                    memory_id="memory-session-1",
                    scope=scope,
                    score=0.9,
                    payload={
                        "summary": "previous login investigation",
                        "content": "read src/auth/login.py",
                        "task_memory": {
                            "objective": "fix login bug",
                            "target_files": ["src/auth/login.py"],
                            "confirmed_facts": ["Target file was previously inspected."],
                            "pending_next_step": "Decide whether the login branch needs a focused edit.",
                            "last_validation_status": "required",
                        },
                    },
                    source_ref="run-prev",
                )
            ]
        return []

    def write(self, memory_item: dict[str, object], *, context=None):
        self.write_calls.append(memory_item)
        return f"memory-write-{len(self.write_calls)}"

    def summarize(self, scope: str, *, context=None):
        return {"scope": scope, "total_items": 0}


def _build_context(
    *,
    message: str,
    llm_invoker=None,
    tool_invoker=None,
    memory_provider=None,
) -> ExecutionContext:
    descriptor = TestProDomainPack.get_agent_descriptors()[0]
    binding = ResolvedAgentBinding(
        node_id="agent",
        agent_ref=descriptor.agent_id,
        resolved_agent_id=descriptor.agent_id,
        resolved_version=descriptor.version,
        executor_ref=descriptor.executor_ref,
        implementation_ref=descriptor.implementation_ref,
        tool_refs=list(descriptor.tool_refs),
        memory_scopes=list(descriptor.memory_scopes),
        policy_profiles=list(descriptor.policy_profiles),
        capabilities=list(descriptor.capabilities),
        metadata=dict(descriptor.metadata),
    )
    node_spec = NodeSpec(
        node_id="agent",
        node_type=NodeType.AGENT,
        executor_ref="agent.domain",
        agent_ref=descriptor.agent_id,
        input_selector=_literal_selector(message or "__empty__"),
        output_binding=OutputBinding(artifact_type="test_pro.chat_output"),
    )
    workflow = CompiledWorkflow(
        workflow_id="wf.test_pro.invoke",
        version="1.0.0",
        entry_node_id="agent",
        node_map={"agent": node_spec},
        outgoing_edges={"agent": []},
        incoming_edges={"agent": []},
    )
    return ExecutionContext(
        thread_record=ThreadRecord(thread_id="thread-1", thread_type="task"),
        run_record=RunRecord(
            run_id="run-1",
            thread_id="thread-1",
            workflow_id="wf.test_pro.invoke",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
            entry_node_id="agent",
        ),
        thread_state=ThreadState(thread_id="thread-1", goal="test invoke"),
        run_state=RunState(
            run_id="run-1",
            thread_id="thread-1",
            workflow_id="wf.test_pro.invoke",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
        ),
        node_state=NodeState(
            run_id="run-1",
            node_id="agent",
            node_type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            started_at=ThreadRecord(thread_id="tmp", thread_type="tmp").created_at,
            executor_ref="agent.domain",
        ),
        workflow=workflow,
        node_spec=node_spec,
        agent_binding=binding,
        selected_input={"message": message},
        services=RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            llm_invoker=llm_invoker,
            tool_invoker=tool_invoker,
            memory_provider=memory_provider,
        ),
    )


class TestProAgentInvokeTestCase(unittest.TestCase):
    def test_invoke_fails_when_message_is_empty(self) -> None:
        implementation = TestProChatImplementation()
        context = _build_context(message="")

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.FAILED)
        self.assertEqual(result.error_code, "TEST_PRO_MESSAGE_REQUIRED")

    def test_invoke_returns_fallback_when_llm_is_missing(self) -> None:
        implementation = TestProChatImplementation()
        context = _build_context(message="请帮我看看仓库结构", llm_invoker=None)

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertEqual(result.output["mode"], "fallback")
        self.assertIn("no llm provider", result.output["reply"].lower())

    def test_invoke_can_complete_with_direct_llm_response(self) -> None:
        implementation = TestProChatImplementation()
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我已经理解了任务，不需要进一步调用工具。",
                        "reasoning_summary": "任务可以直接回答",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "explain",
                        "next_step": "直接总结当前判断。",
                    },
                )
            ]
        )
        context = _build_context(message="解释一下这个 agent 的能力", llm_invoker=llm)

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertEqual(result.output["mode"], "agent_loop")
        self.assertEqual(result.output["loop_stop_reason"], "decision_respond")
        self.assertIn("execution_trace", result.output)
        self.assertEqual(result.output["decision"]["decision_type"], "respond")
        self.assertEqual(result.output["current_phase"], "report")
        self.assertIn("working_summary", result.output)
        self.assertIn("task_state", result.output)
        self.assertIn("validation_plan", result.output)
        self.assertIn("edit_readiness", result.output["task_state"])

    def test_invoke_records_tool_context_after_tool_call(self) -> None:
        implementation = TestProChatImplementation()
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "tool_call",
                        "reply": "我先读取目标文件。",
                        "reasoning_summary": "先收集上下文",
                        "should_use_tools": True,
                        "suggested_tool_ref": OPERATION_TOOL_REFS["read_file"],
                        "suggested_tool_input": {"path": "src/app.py"},
                        "task_kind": "read",
                        "next_step": "读取文件后再总结。",
                    },
                ),
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我已经读取了目标文件并完成初步判断。",
                        "reasoning_summary": "已有足够上下文",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "summarize",
                        "next_step": "输出结论。",
                    },
                ),
            ]
        )
        tool_invoker = _FakeToolInvoker()
        context = _build_context(
            message="先看看 src/app.py",
            llm_invoker=llm,
            tool_invoker=tool_invoker,
        )

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertTrue(tool_invoker.calls)
        self.assertIn("tool_context", result.output)
        self.assertTrue(result.output["tool_context"])
        self.assertEqual(result.output["loop_stop_reason"], "decision_respond")
        self.assertEqual(result.output["decision"]["decision_type"], "respond")
        self.assertEqual(result.output["current_phase"], "report")
        self.assertTrue(result.output["working_summary"]["recent_tool_refs"])

    def test_invoke_loads_memory_context_and_persists_turn_summary(self) -> None:
        implementation = TestProChatImplementation()
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我已经结合当前请求和已有上下文完成了初步结论。",
                        "reasoning_summary": "已有足够信息直接回答",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "summarize",
                        "next_step": "输出本轮结论",
                    },
                )
            ]
        )
        memory_provider = _FakeMemoryProvider()
        context = _build_context(
            message="帮我继续处理登录逻辑",
            llm_invoker=llm,
            memory_provider=memory_provider,
        )

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertIn("memory_context", result.output)
        recommended_scope = result.output["recommended_memory_scope"]
        self.assertEqual(recommended_scope, "domain:test_pro")
        self.assertIn("session:test_pro:thread-1", result.output["memory_context"])
        self.assertTrue(memory_provider.retrieve_calls)
        self.assertEqual(len(memory_provider.write_calls), 2)
        self.assertEqual(result.output["memory_write_ids"], ["memory-write-1", "memory-write-2"])
        self.assertEqual(result.output["task_state"]["current_phase"], "report")
        self.assertGreaterEqual(result.output["working_summary"]["memory_hits"], 1)
        self.assertIn("status", result.output["validation_plan"])
        self.assertIn("task_memory", result.output)
        self.assertEqual(result.output["task_memory"]["objective"], "fix login bug")
        self.assertIn("src/auth/login.py", result.output["task_memory"]["target_files"])
        self.assertTrue(memory_provider.write_calls[0]["payload"]["task_memory"]["confirmed_facts"])

    def test_invoke_exposes_edit_readiness_for_edit_request(self) -> None:
        implementation = TestProChatImplementation()
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我先总结当前能确认的修改前状态。",
                        "reasoning_summary": "先给出当前判断",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "summarize",
                        "next_step": "继续收集编辑上下文",
                    },
                ),
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我已经拿到目标文件上下文，可以继续后续编辑判断。",
                        "reasoning_summary": "已完成最小编辑前置读取",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "summarize",
                        "next_step": "继续评估是否满足编辑条件",
                    },
                ),
            ]
        )
        context = _build_context(message="请修改 src/auth/login.py 的登录逻辑", llm_invoker=llm)
        context.selected_input["task_goal"] = "fix login bug"
        context.selected_input["changed_files_hint"] = ["src/auth/login.py"]

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        edit_readiness = result.output["task_state"]["edit_readiness"]
        self.assertTrue(edit_readiness["edit_requested"])
        self.assertFalse(edit_readiness["ready"])
        self.assertEqual(edit_readiness["target_path"], "src/auth/login.py")
        self.assertIn("read_target_context", edit_readiness["missing_requirements"])
        self.assertEqual(result.output["task_state"]["validation_status"], "not_needed")

    def test_invoke_ignores_internal_callback_in_selected_input_payload(self) -> None:
        implementation = TestProChatImplementation()
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "done",
                        "reasoning_summary": "direct response",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "summarize",
                        "next_step": "report",
                    },
                )
            ]
        )
        context = _build_context(message="check current state", llm_invoker=llm)
        context.selected_input["_progress_callback"] = lambda payload: None

        result = implementation.invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
