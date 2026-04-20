from __future__ import annotations

from copy import deepcopy
import re

from domain_packs.operations import OPERATION_TOOL_REFS

from .shared import (
    _BROAD_EXPLORATION_TOOL_REFS,
    _EDIT_TOOL_REFS,
    _NormalizedSupplyChainInput,
    _READ_SEARCH_TOOL_REFS,
    _changed_files_hints,
    _extract_candidate_path,
    _extract_line_range,
    _extract_search_pattern,
    _extract_symbol_candidate,
    _has_any_tool_result,
    _has_tool_result_for_path,
    _is_edit_request,
    _is_git_diff_request,
    _is_git_status_request,
    _recent_tool_calls,
)
from .state import _edit_readiness_status


def _should_avoid_shell(*, suggested_tool_ref: str, message: str, available_tool_refs: list[str]) -> bool:
    if suggested_tool_ref != OPERATION_TOOL_REFS["shell_run"]:
        return False
    lowered = message.lower()
    read_like = any(
        keyword in lowered
        for keyword in ["read", "open", "search", "find", "grep", "list", "diff", "git", "查看", "搜索", "文件"]
    )
    return read_like and any(tool_ref in available_tool_refs for tool_ref in _READ_SEARCH_TOOL_REFS)


def _extract_replace_directive(message: str) -> tuple[str, str] | None:
    lowered = message.lower()
    if not any(keyword in lowered for keyword in ["replace", "with", "替换", "改成", "改为"]):
        return None
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", message)
    if len(quoted) >= 2:
        return quoted[0], quoted[1]
    return None


def _extract_insert_directive(message: str) -> tuple[str, str, str] | None:
    lowered = message.lower()
    if not any(keyword in lowered for keyword in ["insert", "before", "after", "在", "前插入", "后插入"]):
        return None
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", message)
    if len(quoted) < 2:
        return None
    if any(keyword in lowered for keyword in [" before ", "前"]):
        return quoted[1], quoted[0], "before"
    if any(keyword in lowered for keyword in [" after ", "后"]):
        return quoted[1], quoted[0], "after"
    return None


def _matching_structured_edit_preview(
    *,
    tool_context: dict[str, object],
    path: str,
    edit_kind: str,
    expected_occurrences: int | None,
    old_text: str | None = None,
    anchor_text: str | None = None,
    position: str | None = None,
) -> dict[str, object] | None:
    for item in tool_context.values():
        if not isinstance(item, dict):
            continue
        if str(item.get("tool_ref", "")).strip() != OPERATION_TOOL_REFS["preview_structured_edit"]:
            continue
        tool_input = item.get("tool_input")
        tool_output = item.get("tool_output")
        if not isinstance(tool_input, dict) or not isinstance(tool_output, dict):
            continue
        if str(tool_input.get("path", "")).strip() != path:
            continue
        if str(tool_input.get("edit_kind", "")).strip() != edit_kind:
            continue
        if expected_occurrences is not None and tool_input.get("expected_occurrences") != expected_occurrences:
            continue
        if old_text is not None and str(tool_input.get("old_text", "")) != old_text:
            continue
        if anchor_text is not None and str(tool_input.get("anchor_text", "")) != anchor_text:
            continue
        if position is not None and str(tool_input.get("position", "")) != position:
            continue
        return tool_output
    return None


def _remembered_target_files(normalized_input: _NormalizedSupplyChainInput) -> list[str]:
    value = normalized_input.task_memory.get("target_files")
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
    return items


def _remembered_target_path(normalized_input: _NormalizedSupplyChainInput) -> str | None:
    remembered = _remembered_target_files(normalized_input)
    return remembered[0] if remembered else None


def _has_continue_intent(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ["continue", "继续", "接着", "go on"])


def _preferred_tool_decision(
    *,
    normalized_input: _NormalizedSupplyChainInput,
    tool_context: dict[str, object],
) -> tuple[str, dict[str, object], str] | None:
    message = normalized_input.message
    lowered = message.lower()
    available = set(normalized_input.available_tool_refs)
    candidate_path = _extract_candidate_path(message)
    search_pattern = _extract_search_pattern(message)
    symbol_candidate = search_pattern or _extract_symbol_candidate(message)
    replace_directive = _extract_replace_directive(message)
    insert_directive = _extract_insert_directive(message)
    start_line, end_line = _extract_line_range(message)
    changed_hints = _changed_files_hints(normalized_input.raw_selected_input)
    remembered_target_path = _remembered_target_path(normalized_input)
    is_edit_request = _is_edit_request(lowered)

    if _is_git_status_request(lowered) and OPERATION_TOOL_REFS["git_status"] in available:
        return OPERATION_TOOL_REFS["git_status"], {}, "A git status request should prefer the dedicated git status tool."
    if _is_git_diff_request(lowered) and OPERATION_TOOL_REFS["git_diff"] in available:
        return OPERATION_TOOL_REFS["git_diff"], {}, "A diff request should prefer the dedicated git diff tool."
    if candidate_path and start_line and OPERATION_TOOL_REFS["read_file_segment"] in available:
        return (
            OPERATION_TOOL_REFS["read_file_segment"],
            {"path": candidate_path, "start_line": start_line, "end_line": end_line or start_line},
            "The request points to a specific file segment, so segment read is preferred.",
        )
    if candidate_path and any(word in lowered for word in ["outline", "symbol", "api", "class", "function", "符号"]) and OPERATION_TOOL_REFS["symbol_outline"] in available:
        return OPERATION_TOOL_REFS["symbol_outline"], {"path": candidate_path}, "A file-level symbol inspection request should prefer symbol outline."
    if symbol_candidate and any(word in lowered for word in ["definition", "defined", "where is", "定义"]) and OPERATION_TOOL_REFS["lookup_definition"] in available:
        return OPERATION_TOOL_REFS["lookup_definition"], {"symbol": symbol_candidate, "limit": 20}, "A definition lookup request should prefer the dedicated symbol definition tool."
    if symbol_candidate and any(word in lowered for word in ["reference", "references", "usage", "who calls", "引用", "调用"]) and OPERATION_TOOL_REFS["find_references"] in available:
        return OPERATION_TOOL_REFS["find_references"], {"symbol": symbol_candidate, "limit": 20}, "A symbol usage request should prefer the reference lookup tool."
    if candidate_path and search_pattern and OPERATION_TOOL_REFS["find_in_file"] in available:
        return OPERATION_TOOL_REFS["find_in_file"], {"path": candidate_path, "pattern": search_pattern, "limit": 20}, "The request points to one file and one pattern, so in-file search is preferred."
    if candidate_path and any(word in lowered for word in ["read", "open", "查看", "读取"]) and OPERATION_TOOL_REFS["read_file"] in available:
        return OPERATION_TOOL_REFS["read_file"], {"path": candidate_path}, "The request points to one file, so direct file read is preferred."
    if symbol_candidate and any(word in lowered for word in ["symbol", "class", "function", "method", "仓库", "文件"]) and OPERATION_TOOL_REFS["symbol_search"] in available:
        return OPERATION_TOOL_REFS["symbol_search"], {"query": symbol_candidate, "limit": 20}, "A repo-level symbol discovery request should prefer symbol search before raw text search."
    if search_pattern and OPERATION_TOOL_REFS["ripgrep_search"] in available:
        return OPERATION_TOOL_REFS["ripgrep_search"], {"pattern": search_pattern, "limit": 20}, "A repository-wide search request should prefer ripgrep-style search."
    if any(word in lowered for word in ["list", "files", "file tree", "目录", "结构"]) and OPERATION_TOOL_REFS["list_files"] in available:
        return OPERATION_TOOL_REFS["list_files"], {"path": ".", "recursive": True, "limit": 200}, "A structure inspection request should prefer listing files first."
    if (
        is_edit_request
        and candidate_path
        and replace_directive is not None
        and _has_tool_result_for_path(tool_context, candidate_path)
        and OPERATION_TOOL_REFS["replace_in_file"] in available
    ):
        old_text, new_text = replace_directive
        return (
            OPERATION_TOOL_REFS["replace_in_file"],
            {
                "path": candidate_path,
                "old_text": old_text,
                "new_text": new_text,
                "expected_occurrences": 1,
            },
            "A precise edit request with explicit old/new text should prefer exact replace over raw patch.",
        )
    if (
        is_edit_request
        and candidate_path
        and insert_directive is not None
        and _has_tool_result_for_path(tool_context, candidate_path)
        and OPERATION_TOOL_REFS["insert_in_file"] in available
    ):
        anchor_text, insert_text, position = insert_directive
        return (
            OPERATION_TOOL_REFS["insert_in_file"],
            {
                "path": candidate_path,
                "anchor_text": anchor_text,
                "insert_text": insert_text,
                "position": position,
                "expected_occurrences": 1,
            },
            "A precise insertion request with an explicit anchor should prefer anchored insert over raw patch.",
        )
    if (
        is_edit_request
        and not candidate_path
        and remembered_target_path
        and not _has_tool_result_for_path(tool_context, remembered_target_path)
        and OPERATION_TOOL_REFS["read_file"] in available
    ):
        return (
            OPERATION_TOOL_REFS["read_file"],
            {"path": remembered_target_path},
            "Task memory already identifies a likely target file, so read it before exploring the whole repository again.",
        )
    if (
        _has_continue_intent(message)
        and remembered_target_path
        and not _has_tool_result_for_path(tool_context, remembered_target_path)
        and OPERATION_TOOL_REFS["read_file"] in available
    ):
        return (
            OPERATION_TOOL_REFS["read_file"],
            {"path": remembered_target_path},
            "Task memory remembers the active target file, so a continue request should resume from that file first.",
        )
    if is_edit_request and candidate_path and not _has_tool_result_for_path(tool_context, candidate_path) and OPERATION_TOOL_REFS["read_file"] in available:
        return OPERATION_TOOL_REFS["read_file"], {"path": candidate_path}, "Before patching, read the target file to gather context."
    if is_edit_request and not candidate_path and changed_hints:
        hinted = changed_hints[0]
        if not _has_tool_result_for_path(tool_context, hinted) and OPERATION_TOOL_REFS["read_file"] in available:
            return OPERATION_TOOL_REFS["read_file"], {"path": hinted}, "An edit request with changed_files_hint should read the hinted file before acting."
    if is_edit_request and not candidate_path and OPERATION_TOOL_REFS["list_files"] in available and not _has_any_tool_result(tool_context):
        return OPERATION_TOOL_REFS["list_files"], {"path": ".", "recursive": True, "limit": 200}, "An edit request without file context should inspect the repository structure first."
    return None


def _apply_policy_to_decision(
    decision: dict[str, object],
    *,
    normalized_input: _NormalizedSupplyChainInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    current_step: int,
) -> dict[str, object]:
    adjusted = deepcopy(decision)
    reasons: list[str] = []
    preferred = _preferred_tool_decision(normalized_input=normalized_input, tool_context=tool_context)
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    current_tool_input = adjusted.get("suggested_tool_input")
    if preferred is not None:
        tool_ref, tool_input, reason = preferred
        if (
            str(adjusted.get("decision_type", "respond")) == "respond"
            or current_tool_ref == OPERATION_TOOL_REFS["shell_run"]
            or current_tool_ref not in normalized_input.available_tool_refs
        ):
            adjusted["decision_type"] = "tool_call"
            adjusted["should_use_tools"] = True
            adjusted["suggested_tool_ref"] = tool_ref
            adjusted["suggested_tool_input"] = tool_input
            reasons.append(reason)
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    if _should_avoid_shell(
        suggested_tool_ref=current_tool_ref,
        message=normalized_input.message,
        available_tool_refs=normalized_input.available_tool_refs,
    ):
        tool_ref, tool_input, reason = preferred or ("", {}, "")
        if tool_ref:
            adjusted["suggested_tool_ref"] = tool_ref
            adjusted["suggested_tool_input"] = tool_input
            reasons.append("shell.run was downgraded because a more specific tool is available. " + reason)
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    remembered_target_path = _remembered_target_path(normalized_input)
    if (
        str(adjusted.get("decision_type")) == "tool_call"
        and current_tool_ref in _BROAD_EXPLORATION_TOOL_REFS
        and remembered_target_path
        and not _has_tool_result_for_path(tool_context, remembered_target_path)
        and OPERATION_TOOL_REFS["read_file"] in normalized_input.available_tool_refs
    ):
        adjusted["suggested_tool_ref"] = OPERATION_TOOL_REFS["read_file"]
        adjusted["suggested_tool_input"] = {"path": remembered_target_path}
        reasons.append("Task memory redirected broad exploration back to the remembered target file.")
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    if (
        str(adjusted.get("decision_type")) == "tool_call"
        and current_tool_ref == OPERATION_TOOL_REFS["replace_in_file"]
        and OPERATION_TOOL_REFS["preview_structured_edit"] in normalized_input.available_tool_refs
    ):
        tool_input = adjusted.get("suggested_tool_input")
        if isinstance(tool_input, dict):
            target_path = str(tool_input.get("path", "")).strip()
            old_text = str(tool_input.get("old_text", ""))
            expected_occurrences = tool_input.get("expected_occurrences")
            preview = _matching_structured_edit_preview(
                tool_context=tool_context,
                path=target_path,
                edit_kind="replace",
                expected_occurrences=expected_occurrences if isinstance(expected_occurrences, int) else None,
                old_text=old_text,
            )
            if preview is None:
                adjusted["suggested_tool_ref"] = OPERATION_TOOL_REFS["preview_structured_edit"]
                adjusted["suggested_tool_input"] = {
                    "path": target_path,
                    "edit_kind": "replace",
                    "old_text": old_text,
                    "expected_occurrences": expected_occurrences,
                }
                reasons.append("Structured replace now requires a preview step before mutation.")
            elif not bool(preview.get("applicable")):
                adjusted["decision_type"] = "respond"
                adjusted["should_use_tools"] = False
                adjusted["suggested_tool_ref"] = ""
                adjusted["suggested_tool_input"] = {}
                adjusted["next_step"] = "Explain why the structured replace is not safely applicable."
                reasons.append("Structured replace preview reported the edit is not safely applicable.")
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    if (
        str(adjusted.get("decision_type")) == "tool_call"
        and current_tool_ref == OPERATION_TOOL_REFS["insert_in_file"]
        and OPERATION_TOOL_REFS["preview_structured_edit"] in normalized_input.available_tool_refs
    ):
        tool_input = adjusted.get("suggested_tool_input")
        if isinstance(tool_input, dict):
            target_path = str(tool_input.get("path", "")).strip()
            anchor_text = str(tool_input.get("anchor_text", ""))
            position = str(tool_input.get("position", ""))
            expected_occurrences = tool_input.get("expected_occurrences")
            preview = _matching_structured_edit_preview(
                tool_context=tool_context,
                path=target_path,
                edit_kind="insert",
                expected_occurrences=expected_occurrences if isinstance(expected_occurrences, int) else None,
                anchor_text=anchor_text,
                position=position,
            )
            if preview is None:
                adjusted["suggested_tool_ref"] = OPERATION_TOOL_REFS["preview_structured_edit"]
                adjusted["suggested_tool_input"] = {
                    "path": target_path,
                    "edit_kind": "insert",
                    "anchor_text": anchor_text,
                    "position": position,
                    "expected_occurrences": expected_occurrences,
                }
                reasons.append("Anchored insert now requires a preview step before mutation.")
            elif not bool(preview.get("applicable")):
                adjusted["decision_type"] = "respond"
                adjusted["should_use_tools"] = False
                adjusted["suggested_tool_ref"] = ""
                adjusted["suggested_tool_input"] = {}
                adjusted["next_step"] = "Explain why the anchored insert is not safely applicable."
                reasons.append("Anchored insert preview reported the edit is not safely applicable.")
    current_tool_ref = str(adjusted.get("suggested_tool_ref", "")).strip()
    if str(adjusted.get("decision_type")) == "tool_call" and current_tool_ref in _EDIT_TOOL_REFS:
        readiness = _edit_readiness_status(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            latest_decision=adjusted,
        )
        if not readiness["ready"]:
            target_path = str(readiness.get("target_path") or "").strip()
            if target_path and not readiness["target_context_loaded"] and OPERATION_TOOL_REFS["read_file"] in normalized_input.available_tool_refs:
                adjusted["suggested_tool_ref"] = OPERATION_TOOL_REFS["read_file"]
                adjusted["suggested_tool_input"] = {"path": target_path}
                reasons.append("Edit readiness blocked direct mutation until the target file is read.")
            elif not readiness["repository_context_seen"] and OPERATION_TOOL_REFS["list_files"] in normalized_input.available_tool_refs:
                adjusted["suggested_tool_ref"] = OPERATION_TOOL_REFS["list_files"]
                adjusted["suggested_tool_input"] = {"path": ".", "recursive": True, "limit": 200}
                reasons.append("Edit readiness blocked direct mutation until repository context is collected.")
            else:
                adjusted["decision_type"] = "respond"
                adjusted["should_use_tools"] = False
                adjusted["suggested_tool_ref"] = ""
                adjusted["suggested_tool_input"] = {}
                adjusted["next_step"] = "Collect the missing edit prerequisites before changing files."
                reasons.append("Edit readiness blocked direct mutation because prerequisites are missing.")
    recent_calls = _recent_tool_calls(execution_trace)
    if recent_calls:
        last_call = recent_calls[-1]
        if (
            str(adjusted.get("decision_type")) == "tool_call"
            and current_tool_ref == str(last_call.get("tool_ref", "")).strip()
            and isinstance(current_tool_input, dict)
            and current_tool_input == last_call.get("tool_input")
        ):
            adjusted["decision_type"] = "respond"
            adjusted["should_use_tools"] = False
            adjusted["suggested_tool_ref"] = ""
            adjusted["suggested_tool_input"] = {}
            adjusted["next_step"] = "Summarize the findings instead of repeating the same tool call."
            reasons.append("Repeated identical tool call was prevented.")
    if current_step >= 3 and str(adjusted.get("decision_type")) == "tool_call":
        same_tool_count = sum(1 for entry in recent_calls if str(entry.get("tool_ref", "")).strip() == current_tool_ref)
        if same_tool_count >= 2 and current_tool_ref in _BROAD_EXPLORATION_TOOL_REFS:
            adjusted["decision_type"] = "respond"
            adjusted["should_use_tools"] = False
            adjusted["suggested_tool_ref"] = ""
            adjusted["suggested_tool_input"] = {}
            adjusted["next_step"] = "Stop the loop and summarize the most useful evidence already collected."
            reasons.append("The same broad exploration tool has already been used multiple times in this run.")
    adjusted["adjusted"] = bool(reasons) or bool(adjusted.get("adjusted"))
    adjusted["adjustment_reason"] = " ".join(reasons).strip()
    return adjusted
