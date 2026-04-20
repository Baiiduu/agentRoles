from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.runtime.skill_prompt_service import (
    build_runtime_skill_packages,
    build_skill_prompt_appendix,
    resolve_active_skill_packages,
)


class SkillPromptServiceTests(unittest.TestCase):
    def test_build_runtime_skill_packages_reads_prompt_and_binding_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_file = Path(temp_dir) / "SKILL.md"
            prompt_file.write_text(
                """
---
name: Dependency Audit
description: Review dependency risk with a repeatable checklist.
---

# Dependency Audit

Inspect dependency manifests before giving a recommendation.
                """.strip(),
                encoding="utf-8",
            )

            packages = build_runtime_skill_packages(
                registered_skills=[
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "description": "Review dependency risk with a repeatable checklist.",
                        "trigger_kinds": ["dependency", "audit"],
                        "prompt_file": str(prompt_file),
                    }
                ],
                skill_bindings=[
                    {
                        "skill_name": "dependency-audit",
                        "enabled": True,
                        "execution_mode": "human_confirmed",
                        "scope": "session",
                        "trigger_kinds": ["manifest"],
                        "usage_notes": "Use this for package review tasks.",
                    }
                ],
            )

            self.assertEqual(len(packages), 1)
            self.assertEqual(
                packages[0]["trigger_kinds"],
                ["dependency", "audit", "manifest"],
            )
            self.assertEqual(packages[0]["execution_mode"], "human_confirmed")
            self.assertTrue(packages[0]["prompt_available"])
            self.assertIn(
                "Inspect dependency manifests before giving a recommendation.",
                packages[0]["prompt_body"],
            )

    def test_skill_prompt_appendix_expands_only_active_skill_body(self) -> None:
        runtime_resource_context = {
            "skill_packages": [
                {
                    "skill_name": "dependency-audit",
                    "name": "Dependency Audit",
                    "description": "Review dependency risk.",
                    "trigger_kinds": ["dependency", "audit"],
                    "execution_mode": "human_confirmed",
                    "scope": "session",
                    "usage_notes": "Use for package review.",
                    "prompt_summary": "Inspect manifests before deciding.",
                    "prompt_body": "Inspect manifests before deciding.\nAsk before publishing conclusions.",
                },
                {
                    "skill_name": "sbom-helper",
                    "name": "SBOM Helper",
                    "description": "Work with SBOM data.",
                    "trigger_kinds": ["sbom"],
                    "execution_mode": "advisory",
                    "scope": "session",
                    "usage_notes": "",
                    "prompt_summary": "Summarize SBOM coverage.",
                    "prompt_body": "Summarize SBOM coverage in a concise table.",
                },
            ]
        }

        resolved = resolve_active_skill_packages(
            runtime_resource_context,
            {"message": "请帮我做一次 dependency audit"},
        )
        self.assertEqual(
            [item["skill_name"] for item in resolved["active"]],
            ["dependency-audit"],
        )
        appendix = build_skill_prompt_appendix(
            runtime_resource_context,
            {"message": "请帮我做一次 dependency audit"},
        )
        self.assertIn("Active skills for this request:", appendix)
        self.assertIn("Inspect manifests before deciding.", appendix)
        self.assertIn("Assigned skills available as summaries:", appendix)
        self.assertIn("Summarize SBOM coverage.", appendix)
        self.assertNotIn("Summarize SBOM coverage in a concise table.", appendix)


if __name__ == "__main__":
    unittest.main()
