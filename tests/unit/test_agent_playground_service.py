from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.llm import LLMResult
from application.playground.agent_playground_service import AgentPlaygroundFacade


class _FakeAgentLLMInvoker:
    def invoke(self, request, context=None):
        return LLMResult(
            success=False,
            provider_ref="test",
            model_name="fake-model",
            error_code="TEST_DISABLED",
            error_message="llm disabled in unit test",
        )


class AgentPlaygroundFacadeTestCase(unittest.TestCase):
    def test_bootstrap_exposes_agents_and_sample_cases(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())

        result = facade.get_bootstrap()

        self.assertEqual(len(result["agents"]), 10)
        self.assertGreaterEqual(len(result["available_cases"]), 2)
        self.assertEqual(result["default_agent_id"], "learner_profiler")
        self.assertTrue(result["agent_tree"])
        self.assertEqual(result["agent_tree"][0]["name"], "domain_packs")
        agent_ids = {item["agent_id"] for item in result["agents"]}
        self.assertIn("dependency_auditor", agent_ids)
        self.assertIn("vulnerability_remediator", agent_ids)
        self.assertIn("compliance_specialist", agent_ids)
        self.assertIn("evolver_agent", agent_ids)

    def test_send_message_surfaces_llm_failure_state(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())

        result = facade.send_message(
            {
                "agent_id": "curriculum_planner",
                "message": "请设计一个两周学习计划",
                "ephemeral_context": {
                    "goal": "提高数学应用题能力",
                    "target_objective": "提高数学应用题能力",
                    "current_level": "初二",
                    "weaknesses": ["一元二次方程"],
                },
                "persist_artifact": False,
            }
        )

        self.assertEqual(result["session"]["status"], "failed")
        self.assertEqual(result["agent"]["agent_id"], "curriculum_planner")
        self.assertIsNone(result["artifact_preview"])
        self.assertEqual(result["messages"][-1]["content"], "llm disabled in unit test")

    def test_send_message_with_case_writeback_returns_case_status(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())

        result = facade.send_message(
            {
                "agent_id": "learner_profiler",
                "case_id": "case-algebra-foundation",
                "message": "请给出这个学生的学习画像",
                "ephemeral_context": {
                    "learner_id": "stu-001",
                    "goal": "提高数学应用题能力",
                    "current_level": "初二",
                },
                "persist_artifact": True,
            }
        )

        self.assertEqual(result["writeback_status"]["case_id"], "case-algebra-foundation")
        self.assertFalse(result["writeback_status"]["persisted"])
        self.assertIn("case repository", result["writeback_status"]["message"])

    def test_history_persists_user_and_agent_roles_only(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())
        created = facade.create_chat_session("test_pro_chat")
        session_id = created["session"]["session_id"]
        facade._persist_chat_exchange(
            SimpleNamespace(
                session_id=session_id,
                agent_id="test_pro_chat",
                messages=[
                    SimpleNamespace(role="user", content="hello"),
                    SimpleNamespace(role="agent", content="world"),
                    SimpleNamespace(role="system", content="ignored"),
                ],
            )
        )

        history = facade.get_chat_history("test_pro_chat", session_id=session_id, limit=10)

        matching = [item for item in history["messages"] if item["session_id"] == session_id]
        self.assertEqual(len(matching), 2)
        self.assertEqual([item["role"] for item in matching], ["user", "agent"])

    def test_consecutive_messages_reuse_latest_session_by_default(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())

        first = facade.send_message(
            {
                "agent_id": "test_pro_chat",
                "message": "first message",
                "ephemeral_context": {},
                "persist_artifact": False,
            }
        )
        second = facade.send_message(
            {
                "agent_id": "test_pro_chat",
                "message": "second message",
                "ephemeral_context": {},
                "persist_artifact": False,
            }
        )

        self.assertEqual(first["session"]["session_id"], second["session"]["session_id"])

    def test_can_create_and_delete_chat_session(self) -> None:
        facade = AgentPlaygroundFacade(llm_invoker_override=_FakeAgentLLMInvoker())

        created = facade.create_chat_session("test_pro_chat")
        listed = facade.list_chat_sessions("test_pro_chat")
        deleted = facade.delete_chat_session("test_pro_chat", created["session"]["session_id"])

        self.assertIn(created["session"]["session_id"], [item["session_id"] for item in listed["sessions"]])
        self.assertEqual(deleted["deleted_session_id"], created["session"]["session_id"])


if __name__ == "__main__":
    unittest.main()
