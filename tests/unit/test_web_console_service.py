from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.llm import LLMResult
from interfaces.web_console import EducationConsoleService


class _FakeAssistantLLMInvoker:
    def __init__(self) -> None:
        self.last_request = None

    def invoke(self, request, context=None):
        self.last_request = request
        return LLMResult(
            success=True,
            provider_ref="deepseek",
            model_name="deepseek-chat",
            output_text="当前项目已经可以先从 diagnostic_plan 工作流开始做教育领域测试。",
        )


class _FakeDisabledLLMInvoker:
    def invoke(self, request, context=None):
        return LLMResult(
            success=False,
            provider_ref="test",
            model_name="fake-model",
            error_code="TEST_DISABLED",
            error_message="llm disabled in unit test",
        )


class WebConsoleServiceTestCase(unittest.TestCase):
    def test_overview_reflects_current_project_state(self) -> None:
        service = EducationConsoleService()

        overview = service.get_overview()

        self.assertTrue(overview["llm_status"]["integrated"])
        self.assertIn("configured", overview["llm_status"])
        self.assertIn("configured_provider_count", overview["llm_status"])
        self.assertIn("configured_profile_count", overview["llm_status"])
        self.assertGreaterEqual(overview["llm_status"]["configured_provider_count"], 0)
        self.assertGreaterEqual(overview["llm_status"]["configured_profile_count"], 0)
        self.assertEqual(overview["counts"]["agents"], 5)
        self.assertEqual(overview["counts"]["workflows"], 3)
        self.assertEqual(overview["counts"]["tools"], 4)
        self.assertEqual(overview["counts"]["eval_suites"], 3)

    def test_workflow_run_returns_completed_diagnostic_flow(self) -> None:
        service = EducationConsoleService()

        result = service.run_workflow(
            "education.diagnostic_plan",
            global_context={
                "learner_id": "web-learner-001",
                "goal": "fractions mastery",
                "current_level": "beginner",
                "weak_topics": ["fractions"],
                "preferences": ["worked examples"],
            },
        )

        self.assertEqual(result["run"]["status"], "completed")
        self.assertIn("lookup_curriculum_context", result["run"]["completed_nodes"])
        self.assertGreaterEqual(len(result["timeline"]), 1)

    def test_eval_suite_returns_summary(self) -> None:
        service = EducationConsoleService()

        result = service.run_eval_suite("education.eval_suite.smoke")

        self.assertEqual(result["suite"]["suite_id"], "education.eval_suite.smoke")
        self.assertEqual(result["summary"]["total_cases"], 4)
        self.assertEqual(len(result["cases"]), 4)

    def test_project_assistant_returns_project_aware_reply(self) -> None:
        fake_invoker = _FakeAssistantLLMInvoker()
        service = EducationConsoleService(llm_invoker_override=fake_invoker)

        result = service.chat_with_project_agent("现在适合怎么开始做教育测试？")

        self.assertEqual(result["mode"], "llm")
        self.assertEqual(result["provider_ref"], "deepseek")
        self.assertIn("diagnostic_plan", result["message"])
        self.assertEqual(result["project_snapshot"]["counts"]["agents"], 5)
        self.assertEqual(fake_invoker.last_request.profile_ref, "deepseek.default")

    def test_agent_playground_bootstrap_and_message_are_available(self) -> None:
        service = EducationConsoleService(llm_invoker_override=_FakeDisabledLLMInvoker())

        bootstrap = service.get_agent_playground_bootstrap()
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

        self.assertEqual(bootstrap["default_agent_id"], "learner_profiler")
        self.assertEqual(result["session"]["status"], "responded")
        self.assertEqual(result["agent"]["agent_id"], "learner_profiler")
