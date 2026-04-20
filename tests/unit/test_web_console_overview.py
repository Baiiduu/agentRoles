from __future__ import annotations

import unittest

from tests.unit._web_console_test_support import make_console_service


class WebConsoleOverviewTestCase(unittest.TestCase):
    def test_overview_reflects_current_project_state(self) -> None:
        service = make_console_service()

        overview = service.get_overview()

        self.assertTrue(overview["llm_status"]["integrated"])
        self.assertIn("configured", overview["llm_status"])
        self.assertIn("configured_provider_count", overview["llm_status"])
        self.assertIn("configured_profile_count", overview["llm_status"])
        self.assertGreaterEqual(overview["llm_status"]["configured_provider_count"], 0)
        self.assertGreaterEqual(overview["llm_status"]["configured_profile_count"], 0)
        self.assertGreaterEqual(overview["counts"]["agents"], 5)
        self.assertGreaterEqual(overview["counts"]["workflows"], 3)
        self.assertGreaterEqual(overview["counts"]["tools"], 4)
        self.assertGreaterEqual(overview["counts"]["eval_suites"], 3)
        self.assertIn("domain_packs", overview)
        self.assertTrue(any(agent["agent_id"] == "learner_profiler" for agent in overview["agents"]))
        self.assertTrue(
            any(workflow["workflow_id"] == "education.diagnostic_plan" for workflow in overview["workflows"])
        )


if __name__ == "__main__":
    unittest.main()
