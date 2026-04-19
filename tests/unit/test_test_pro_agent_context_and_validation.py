from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_packs.operations import OPERATION_TOOL_REFS
from domain_packs.test_pro.agents.implementations import (
    _NormalizedTestProInput,
    _enrich_final_reply,
    _preferred_tool_decision,
)


class TestProAgentContextAndValidationTestCase(unittest.TestCase):
    def test_edit_request_prefers_changed_file_hint_context(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="请帮我修复登录逻辑，必要时直接修改",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["read_file"],
                OPERATION_TOOL_REFS["list_files"],
            ],
            raw_selected_input={
                "changed_files_hint": ["src/auth/login.py"],
            },
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={},
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["read_file"])
        self.assertEqual(tool_input["path"], "src/auth/login.py")

    def test_final_reply_adds_validation_guidance_after_edit_without_validation(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="帮我修复登录逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            raw_selected_input={
                "changed_files_hint": ["src/auth/login.py"],
                "verification_mode": "suggest",
            },
        )

        enriched = _enrich_final_reply(
            "我已经完成了登录逻辑的修改。",
            normalized_input=normalized_input,
            execution_trace=[
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["apply_patch"],
                    "tool_input": {"path": "src/auth/login.py"},
                }
            ],
        )

        self.assertIn("验证建议", enriched)
        self.assertIn("src/auth/login.py", enriched)
        self.assertIn("剩余风险", enriched)

    def test_final_reply_does_not_duplicate_validation_block_when_already_present(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="帮我修复登录逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            raw_selected_input={},
        )

        enriched = _enrich_final_reply(
            "修改已完成。\n\n验证建议：\n- 运行最小测试。",
            normalized_input=normalized_input,
            execution_trace=[
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["apply_patch"],
                    "tool_input": {"path": "src/auth/login.py"},
                }
            ],
        )

        self.assertEqual(enriched.count("验证建议"), 1)


if __name__ == "__main__":
    unittest.main()
