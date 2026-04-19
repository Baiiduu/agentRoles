from __future__ import annotations

from copy import deepcopy

from .shared import (
    _EDIT_TOOL_REFS,
    _NormalizedTestProInput,
    _VALIDATION_TOOL_REFS,
    _changed_files_hints,
    _extract_candidate_path,
    _has_any_tool_result,
    _has_edit_activity,
    _has_tool_result_for_path,
    _has_validation_activity,
    _is_edit_request,
    _recent_tool_calls,
)


def _summarize_memory_context(memory_context: dict[str, list[dict[str, object]]]) -> list[str]:
    lines: list[str] = []
    for scope, items in memory_context.items():
        for item in items[:2]:
            payload = item.get("payload")
            if not isinstance(payload, dict):
                continue
            snippet = str(payload.get("summary") or payload.get("content") or "").strip()
            if snippet:
                lines.append(f"{scope}: {snippet}")
    return lines[:3]


def _infer_current_phase(
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    latest_decision: dict[str, object] | None,
    loop_stop_reason: str | None = None,
) -> str:
    if loop_stop_reason in {"decision_respond", "max_steps_reached"}:
        return "report"
    if _has_validation_activity(execution_trace):
        return "validate"
    if _has_edit_activity(execution_trace):
        return "edit"
    if _recent_tool_calls(execution_trace):
        return "explore"
    if latest_decision is not None:
        task_kind = str(latest_decision.get("task_kind", "")).strip().lower()
        if task_kind in {"edit", "patch", "modify", "change", "fix"}:
            return "edit"
        if task_kind in {"validate", "verification", "test"}:
            return "validate"
        if task_kind in {"read", "search", "explore"}:
            return "explore"
    if _is_edit_request(normalized_input.message.lower()):
        return "explore"
    return "understand"


def _build_working_summary(
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    latest_decision: dict[str, object] | None,
    current_phase: str,
) -> dict[str, object]:
    recent_tool_refs = [
        str(entry.get("tool_ref", "")).strip()
        for entry in _recent_tool_calls(execution_trace)[-3:]
        if str(entry.get("tool_ref", "")).strip()
    ]
    known_facts: list[str] = []
    memory_lines = _summarize_memory_context(normalized_input.memory_context)
    if memory_lines:
        known_facts.extend(f"Memory: {line}" for line in memory_lines)
    changed_hints = _changed_files_hints(normalized_input.raw_selected_input)
    if changed_hints:
        known_facts.append("Changed file hints: " + ", ".join(changed_hints))
    if recent_tool_refs:
        known_facts.append("Recent tools: " + ", ".join(recent_tool_refs))
    if tool_context:
        known_facts.append(f"Collected tool results: {len(tool_context)}")
    pending_by_phase = {
        "understand": "Clarify the concrete repository target and minimal next step.",
        "explore": "Collect enough local context before proposing changes.",
        "edit": "Confirm the planned mutation matches the gathered context.",
        "validate": "Check the diff and the smallest relevant validation path.",
        "report": "Summarize findings, changes, validation status, and remaining risks.",
    }
    next_focus = str(latest_decision.get("next_step", "")).strip() if latest_decision else ""
    next_focus = next_focus or pending_by_phase[current_phase]
    return {
        "current_phase": current_phase,
        "known_facts": known_facts,
        "pending_questions": [pending_by_phase[current_phase]],
        "recent_tool_refs": recent_tool_refs,
        "memory_hits": sum(len(items) for items in normalized_input.memory_context.values()),
        "next_focus": next_focus,
    }


def _current_edit_target_path(
    *,
    normalized_input: _NormalizedTestProInput,
    latest_decision: dict[str, object] | None,
) -> str | None:
    if latest_decision is not None:
        tool_input = latest_decision.get("suggested_tool_input")
        if isinstance(tool_input, dict):
            for key in ("path", "source_path", "destination_path", "target_path"):
                value = tool_input.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    candidate = _extract_candidate_path(normalized_input.message)
    if candidate:
        return candidate
    hints = _changed_files_hints(normalized_input.raw_selected_input)
    return hints[0] if hints else None


def _edit_readiness_status(
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    latest_decision: dict[str, object] | None = None,
) -> dict[str, object]:
    edit_requested = _is_edit_request(normalized_input.message.lower()) or (
        latest_decision is not None
        and str(latest_decision.get("suggested_tool_ref", "")).strip() in _EDIT_TOOL_REFS
    )
    target_path = _current_edit_target_path(normalized_input=normalized_input, latest_decision=latest_decision)
    target_context_loaded = bool(target_path and _has_tool_result_for_path(tool_context, target_path))
    repository_context_seen = bool(
        _has_any_tool_result(tool_context)
        or normalized_input.memory_context
        or _changed_files_hints(normalized_input.raw_selected_input)
    )
    task_goal = normalized_input.raw_selected_input.get("task_goal")
    acceptance = normalized_input.raw_selected_input.get("acceptance_criteria")
    success_conditions_known = bool(
        (isinstance(task_goal, str) and task_goal.strip())
        or acceptance is not None
        or _changed_files_hints(normalized_input.raw_selected_input)
    )
    missing: list[str] = []
    if edit_requested:
        if not target_path:
            missing.append("identify_target_path")
        if target_path and not target_context_loaded:
            missing.append("read_target_context")
        if not repository_context_seen:
            missing.append("collect_repository_context")
        if not success_conditions_known:
            missing.append("clarify_success_conditions")
    return {
        "edit_requested": edit_requested,
        "ready": edit_requested and not missing,
        "target_path": target_path,
        "target_context_loaded": target_context_loaded,
        "repository_context_seen": repository_context_seen,
        "success_conditions_known": success_conditions_known,
        "missing_requirements": missing,
    }


def _validation_plan(
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
) -> dict[str, object]:
    from .shared import _verification_mode

    changed_hints = _changed_files_hints(normalized_input.raw_selected_input)
    verification_mode = _verification_mode(normalized_input.raw_selected_input)
    has_edit = _has_edit_activity(execution_trace)
    has_validation = _has_validation_activity(execution_trace)
    executed_checks = [
        {
            "kind": "tool_call",
            "tool_ref": str(entry.get("tool_ref", "")).strip(),
            "loop_step": entry.get("loop_step"),
            "status": "completed" if entry.get("tool_success") else "failed",
        }
        for entry in execution_trace
        if entry.get("kind") == "tool_call" and str(entry.get("tool_ref", "")).strip() in _VALIDATION_TOOL_REFS
    ]
    suggested_checks: list[dict[str, object]] = []
    if has_edit and not has_validation:
        if changed_hints:
            suggested_checks.append(
                {
                    "kind": "diff_review",
                    "status": "pending",
                    "summary": f"Review the diff against changed file hints: {', '.join(changed_hints)}.",
                }
            )
        else:
            suggested_checks.append(
                {
                    "kind": "diff_review",
                    "status": "pending",
                    "summary": "Review git diff to confirm the final mutation scope matches the task.",
                }
            )
        suggested_checks.append(
            {
                "kind": "targeted_validation",
                "status": "pending",
                "summary": (
                    "Run the smallest relevant test, build, or script validation."
                    if verification_mode in {"run", "run_if_safe", "execute"}
                    else "Plan the smallest relevant test, build, or script validation for manual follow-up."
                ),
            }
        )
        suggested_checks.append(
            {
                "kind": "acceptance_review",
                "status": "pending",
                "summary": "Check the final result against the task goal and acceptance criteria.",
            }
        )
    if not has_edit:
        status = "not_needed"
    elif has_validation:
        status = "completed"
    else:
        status = "required"
    return {
        "status": status,
        "verification_mode": verification_mode,
        "changed_files_hint": changed_hints,
        "executed_checks": executed_checks,
        "suggested_checks": suggested_checks,
        "validation_required": has_edit,
    }


def _build_validation_guidance(
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
) -> list[str]:
    plan = _validation_plan(normalized_input, execution_trace)
    return [str(item.get("summary", "")).strip() for item in plan["suggested_checks"] if str(item.get("summary", "")).strip()]


def _enrich_final_reply(
    reply: str,
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
) -> str:
    text = reply.strip() or "已完成当前任务。"
    guidance = _build_validation_guidance(normalized_input, execution_trace)
    if guidance and "验证建议" not in text and "validate" not in text.lower():
        text += "\n\n验证建议：\n- " + "\n- ".join(guidance)
    if _has_edit_activity(execution_trace) and "剩余风险" not in text and "risk" not in text.lower():
        text += "\n\n剩余风险：\n- 如果尚未运行最小验证，改动仍需要通过 diff 和目标测试进一步确认。"
    return text


def _task_state(
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    latest_decision: dict[str, object] | None,
    current_phase: str,
) -> dict[str, object]:
    task_goal = normalized_input.raw_selected_input.get("task_goal")
    acceptance = normalized_input.raw_selected_input.get("acceptance_criteria")
    validation_plan = _validation_plan(normalized_input, execution_trace)
    return {
        "message": normalized_input.message,
        "task_goal": task_goal if isinstance(task_goal, str) and task_goal.strip() else None,
        "acceptance_criteria": deepcopy(acceptance) if acceptance is not None else None,
        "current_phase": current_phase,
        "memory_scopes": list(normalized_input.memory_scopes),
        "changed_files_hint": _changed_files_hints(normalized_input.raw_selected_input),
        "has_edit_activity": _has_edit_activity(execution_trace),
        "has_validation_activity": _has_validation_activity(execution_trace),
        "validation_status": validation_plan["status"],
        "tool_result_count": len(tool_context),
        "latest_decision_type": str(latest_decision.get("decision_type", "")).strip() if latest_decision else "",
        "latest_task_kind": str(latest_decision.get("task_kind", "")).strip() if latest_decision else "",
        "edit_readiness": _edit_readiness_status(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            latest_decision=latest_decision,
        ),
    }
