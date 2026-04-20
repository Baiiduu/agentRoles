from __future__ import annotations

import unittest

from tests.unit._web_console_test_support import make_console_service


class WebConsoleRuntimeTestCase(unittest.TestCase):
    def test_workflow_run_returns_completed_diagnostic_flow(self) -> None:
        service = make_console_service()

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
        service = make_console_service()

        result = service.run_eval_suite("education.eval_suite.smoke")

        self.assertEqual(result["suite"]["suite_id"], "education.eval_suite.smoke")
        self.assertEqual(result["summary"]["total_cases"], 4)
        self.assertEqual(len(result["cases"]), 4)


if __name__ == "__main__":
    unittest.main()
