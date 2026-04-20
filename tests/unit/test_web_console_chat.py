from __future__ import annotations

import unittest

from tests.unit._web_console_test_support import (
    FakeAssistantLLMInvoker,
    make_console_service,
)


class WebConsoleChatTestCase(unittest.TestCase):
    def test_project_assistant_returns_project_aware_reply(self) -> None:
        fake_invoker = FakeAssistantLLMInvoker()
        service = make_console_service(llm_invoker_override=fake_invoker)

        result = service.chat_with_project_agent("现在适合怎么开始做教育测试？")

        self.assertEqual(result["mode"], "llm")
        self.assertEqual(result["provider_ref"], "deepseek")
        self.assertIn("diagnostic_plan", result["message"])
        self.assertGreaterEqual(result["project_snapshot"]["counts"]["agents"], 5)
        self.assertEqual(fake_invoker.last_request.profile_ref, "deepseek.default")


if __name__ == "__main__":
    unittest.main()
