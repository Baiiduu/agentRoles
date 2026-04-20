from __future__ import annotations

import unittest

from tests.unit._web_console_test_support import (
    FakeDisabledLLMInvoker,
    make_console_service,
)


class WebConsoleAgentPlaygroundTestCase(unittest.TestCase):
    def test_agent_playground_bootstrap_is_available(self) -> None:
        service = make_console_service(llm_invoker_override=FakeDisabledLLMInvoker())

        bootstrap = service.get_agent_playground_bootstrap()

        self.assertEqual(bootstrap["default_agent_id"], "learner_profiler")
        self.assertTrue(bootstrap["agents"])

    def test_agent_playground_message_returns_session_contract(self) -> None:
        service = make_console_service(llm_invoker_override=FakeDisabledLLMInvoker())

        result = service.send_agent_playground_message(
            {
                "agent_id": "learner_profiler",
                "message": "请分析这个学生的学习情况",
                "ephemeral_context": {
                    "learner_id": "stu-001",
                    "goal": "提高数学应用题能力",
                    "current_level": "初二",
                },
                "persist_artifact": False,
            }
        )

        self.assertEqual(result["agent"]["agent_id"], "learner_profiler")
        self.assertEqual(result["session"]["agent_id"], "learner_profiler")
        self.assertIn(result["session"]["status"], {"responded", "failed"})
        self.assertGreaterEqual(len(result["messages"]), 1)
        self.assertIn("writeback_status", result)


if __name__ == "__main__":
    unittest.main()
