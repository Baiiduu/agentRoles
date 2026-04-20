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
    _apply_policy_to_decision,
    _edit_readiness_status,
    _preferred_tool_decision,
    _validation_plan,
)


class TestProAgentImplementationPolicyTestCase(unittest.TestCase):
    def test_preferred_tool_decision_prefers_git_status_tool(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="请先看一下当前 git status",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["git_status"],
                OPERATION_TOOL_REFS["shell_run"],
            ],
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={},
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["git_status"])
        self.assertEqual(tool_input, {})

    def test_preferred_tool_decision_prefers_repo_listing_before_edit_without_path(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="请帮我修改登录逻辑，先看看仓库里相关文件",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["list_files"],
                OPERATION_TOOL_REFS["shell_run"],
            ],
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={},
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["list_files"])
        self.assertEqual(tool_input["path"], ".")
        self.assertTrue(tool_input["recursive"])

    def test_preferred_tool_decision_prefers_definition_lookup_for_symbol_question(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="where is definition login_user",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["lookup_definition"],
                OPERATION_TOOL_REFS["ripgrep_search"],
            ],
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={},
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["lookup_definition"])
        self.assertEqual(tool_input["symbol"], "login_user")

    def test_preferred_tool_decision_prefers_exact_replace_when_target_context_is_loaded(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message='replace "old_value" with "new_value" in src/auth/login.py',
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["replace_in_file"],
                OPERATION_TOOL_REFS["apply_patch"],
                OPERATION_TOOL_REFS["read_file"],
            ],
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={
                "step_1:read": {
                    "tool_output": {
                        "path": "src/auth/login.py",
                    }
                }
            },
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["replace_in_file"])
        self.assertEqual(tool_input["path"], "src/auth/login.py")
        self.assertEqual(tool_input["old_text"], "old_value")
        self.assertEqual(tool_input["new_text"], "new_value")
        self.assertEqual(tool_input["expected_occurrences"], 1)

    def test_preferred_tool_decision_prefers_anchored_insert_when_target_context_is_loaded(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message='insert "import os\\n" before "def login():" in src/auth/login.py',
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["insert_in_file"],
                OPERATION_TOOL_REFS["apply_patch"],
                OPERATION_TOOL_REFS["read_file"],
            ],
        )

        decision = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context={
                "step_1:read": {
                    "tool_output": {
                        "path": "src/auth/login.py",
                    }
                }
            },
        )

        self.assertIsNotNone(decision)
        tool_ref, tool_input, _ = decision
        self.assertEqual(tool_ref, OPERATION_TOOL_REFS["insert_in_file"])
        self.assertEqual(tool_input["path"], "src/auth/login.py")
        self.assertEqual(tool_input["anchor_text"], "def login():")
        self.assertEqual(tool_input["insert_text"], "import os\\n")
        self.assertEqual(tool_input["position"], "before")
        self.assertEqual(tool_input["expected_occurrences"], 1)

    def test_preferred_tool_decision_uses_task_memory_target_for_continue_request(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="continue the login task",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["read_file"],
                OPERATION_TOOL_REFS["list_files"],
            ],
            task_memory={
                "target_files": ["src/auth/login.py"],
                "pending_next_step": "Read src/auth/login.py and continue the focused edit.",
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

    def test_apply_policy_stops_repeated_broad_exploration_loop(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="帮我找一下登录逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[OPERATION_TOOL_REFS["ripgrep_search"]],
        )
        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "继续搜索",
                "reasoning_summary": "继续找",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["ripgrep_search"],
                "suggested_tool_input": {"pattern": "login", "limit": 20},
                "task_kind": "search",
                "next_step": "继续搜索",
            },
            normalized_input=normalized_input,
            execution_trace=[
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["ripgrep_search"],
                    "tool_input": {"pattern": "login", "limit": 20},
                },
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["ripgrep_search"],
                    "tool_input": {"pattern": "auth", "limit": 20},
                },
            ],
            tool_context={},
            current_step=3,
        )

        self.assertEqual(adjusted["decision_type"], "respond")
        self.assertFalse(adjusted["should_use_tools"])
        self.assertEqual(adjusted["suggested_tool_ref"], "")
        self.assertIn("broad exploration tool", adjusted["adjustment_reason"])

    def test_apply_policy_redirects_broad_exploration_to_remembered_target(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="continue working on the remembered login fix",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["list_files"],
                OPERATION_TOOL_REFS["read_file"],
            ],
            task_memory={
                "target_files": ["src/auth/login.py"],
            },
        )

        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "explore the repository again",
                "reasoning_summary": "need more context",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["list_files"],
                "suggested_tool_input": {"path": ".", "recursive": True, "limit": 200},
                "task_kind": "explore",
                "next_step": "inspect repository structure",
            },
            normalized_input=normalized_input,
            execution_trace=[],
            tool_context={},
            current_step=2,
        )

        self.assertEqual(adjusted["suggested_tool_ref"], OPERATION_TOOL_REFS["read_file"])
        self.assertEqual(adjusted["suggested_tool_input"], {"path": "src/auth/login.py"})
        self.assertIn("remembered target file", adjusted["adjustment_reason"])

    def test_apply_policy_does_not_block_focused_read_progress(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="继续查看不同文件片段来理解逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[OPERATION_TOOL_REFS["read_file_segment"]],
        )
        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "继续读取",
                "reasoning_summary": "还需要上下文",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["read_file_segment"],
                "suggested_tool_input": {"path": "src/app.py", "start_line": 10, "end_line": 30},
                "task_kind": "read",
                "next_step": "继续读取片段",
            },
            normalized_input=normalized_input,
            execution_trace=[
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["read_file_segment"],
                    "tool_input": {"path": "src/a.py", "start_line": 1, "end_line": 20},
                },
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["read_file_segment"],
                    "tool_input": {"path": "src/b.py", "start_line": 1, "end_line": 20},
                },
            ],
            tool_context={},
            current_step=3,
        )

        self.assertEqual(adjusted["decision_type"], "tool_call")
        self.assertEqual(adjusted["suggested_tool_ref"], OPERATION_TOOL_REFS["read_file_segment"])

    def test_apply_policy_blocks_direct_edit_until_target_file_is_read(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="请直接修改 src/auth/login.py 里的登录逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["apply_patch"],
                OPERATION_TOOL_REFS["read_file"],
            ],
            raw_selected_input={
                "task_goal": "fix login logic",
                "changed_files_hint": ["src/auth/login.py"],
            },
        )

        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "直接修改目标文件",
                "reasoning_summary": "已经知道大概目标",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["apply_patch"],
                "suggested_tool_input": {"path": "src/auth/login.py", "patch": "*** patch"},
                "task_kind": "edit",
                "next_step": "应用补丁",
            },
            normalized_input=normalized_input,
            execution_trace=[],
            tool_context={},
            current_step=1,
        )

        self.assertEqual(adjusted["decision_type"], "tool_call")
        self.assertEqual(adjusted["suggested_tool_ref"], OPERATION_TOOL_REFS["read_file"])
        self.assertEqual(adjusted["suggested_tool_input"], {"path": "src/auth/login.py"})
        self.assertIn("Edit readiness blocked", adjusted["adjustment_reason"])

    def test_apply_policy_requires_preview_before_structured_replace(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message='replace "old_value" with "new_value" in src/auth/login.py',
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["preview_structured_edit"],
                OPERATION_TOOL_REFS["replace_in_file"],
            ],
        )

        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "apply exact replace",
                "reasoning_summary": "use structured edit",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["replace_in_file"],
                "suggested_tool_input": {
                    "path": "src/auth/login.py",
                    "old_text": "old_value",
                    "new_text": "new_value",
                    "expected_occurrences": 1,
                },
                "task_kind": "edit",
                "next_step": "replace the target text",
            },
            normalized_input=normalized_input,
            execution_trace=[],
            tool_context={
                "step_1:read": {
                    "tool_output": {"path": "src/auth/login.py"},
                }
            },
            current_step=2,
        )

        self.assertEqual(adjusted["suggested_tool_ref"], OPERATION_TOOL_REFS["preview_structured_edit"])
        self.assertEqual(adjusted["suggested_tool_input"]["edit_kind"], "replace")
        self.assertIn("preview step", adjusted["adjustment_reason"])

    def test_apply_policy_stops_structured_replace_when_preview_is_not_applicable(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message='replace "old_value" with "new_value" in src/auth/login.py',
            llm_profile_ref=None,
            system_prompt="test",
            available_tool_refs=[
                OPERATION_TOOL_REFS["preview_structured_edit"],
                OPERATION_TOOL_REFS["replace_in_file"],
            ],
        )

        adjusted = _apply_policy_to_decision(
            {
                "decision_type": "tool_call",
                "reply": "apply exact replace",
                "reasoning_summary": "use structured edit",
                "should_use_tools": True,
                "suggested_tool_ref": OPERATION_TOOL_REFS["replace_in_file"],
                "suggested_tool_input": {
                    "path": "src/auth/login.py",
                    "old_text": "old_value",
                    "new_text": "new_value",
                    "expected_occurrences": 1,
                },
                "task_kind": "edit",
                "next_step": "replace the target text",
            },
            normalized_input=normalized_input,
            execution_trace=[],
            tool_context={
                "step_1:read": {
                    "tool_output": {"path": "src/auth/login.py"},
                },
                "step_2:preview": {
                    "tool_ref": OPERATION_TOOL_REFS["preview_structured_edit"],
                    "tool_input": {
                        "path": "src/auth/login.py",
                        "edit_kind": "replace",
                        "old_text": "old_value",
                        "expected_occurrences": 1,
                    },
                    "tool_output": {
                        "applicable": False,
                        "ambiguous": True,
                        "reason": "multiple matches found",
                    },
                },
            },
            current_step=3,
        )

        self.assertEqual(adjusted["decision_type"], "respond")
        self.assertFalse(adjusted["should_use_tools"])
        self.assertIn("not safely applicable", adjusted["adjustment_reason"])

    def test_edit_readiness_reports_missing_target_context(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="请修改 src/auth/login.py 的登录逻辑",
            llm_profile_ref=None,
            system_prompt="test",
            raw_selected_input={
                "task_goal": "fix login bug",
                "changed_files_hint": ["src/auth/login.py"],
            },
        )

        status = _edit_readiness_status(
            normalized_input=normalized_input,
            execution_trace=[],
            tool_context={},
            latest_decision={
                "suggested_tool_ref": OPERATION_TOOL_REFS["apply_patch"],
                "suggested_tool_input": {"path": "src/auth/login.py"},
            },
        )

        self.assertTrue(status["edit_requested"])
        self.assertFalse(status["ready"])
        self.assertEqual(status["target_path"], "src/auth/login.py")
        self.assertIn("read_target_context", status["missing_requirements"])

    def test_validation_plan_requires_follow_up_after_edit_without_validation(self) -> None:
        normalized_input = _NormalizedTestProInput(
            message="please update login handling",
            llm_profile_ref=None,
            system_prompt="test",
            raw_selected_input={
                "changed_files_hint": ["src/auth/login.py"],
                "verification_mode": "run_if_safe",
            },
        )

        plan = _validation_plan(
            normalized_input,
            execution_trace=[
                {
                    "kind": "tool_call",
                    "tool_ref": OPERATION_TOOL_REFS["apply_patch"],
                    "tool_success": True,
                    "loop_step": 1,
                }
            ],
        )

        self.assertEqual(plan["status"], "required")
        self.assertTrue(plan["suggested_checks"])


if __name__ == "__main__":
    unittest.main()
