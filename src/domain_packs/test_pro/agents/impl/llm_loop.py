from __future__ import annotations

from copy import deepcopy
import json

from core.contracts import ExecutionContext
from core.llm import LLMMessage, LLMMessageRole, LLMRequest, LLMResponseFormatKind

from .shared import (
    _NormalizedTestProInput,
    _ToolExecutionBundle,
    _binding_domain,
    _conversation_history_payload,
    _primary_memory_scope,
    _resource_summary,
    _serializable_selected_input,
)


def _decision_required_keys() -> list[str]:
    return [
        "decision_type",
        "reply",
        "reasoning_summary",
        "should_use_tools",
        "suggested_tool_ref",
        "suggested_tool_input",
        "task_kind",
        "next_step",
    ]


def _build_decision_system_prompt(normalized_input: _NormalizedTestProInput) -> str:
    tool_line = ", ".join(normalized_input.available_tool_refs) if normalized_input.available_tool_refs else "none"
    return "\n\n".join(
        [
            normalized_input.system_prompt,
            "Return a valid JSON object only.",
            "Allowed decision_type values: 'respond' or 'tool_call'.",
            f"Currently available tool refs: {tool_line}.",
            "Prefer repository tools over shell when possible.",
            "Use symbol tools for symbol questions, read/search tools for file context, preview tools before structured edits when applicable, exact replace tools for precise snippet edits, anchored insert tools for safe insertions, and patch tools only after enough context is collected.",
            "Include all required keys exactly: " + ", ".join(_decision_required_keys()) + ".",
        ]
    )


def _build_loop_payload(
    normalized_input: _NormalizedTestProInput,
    *,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    current_phase: str,
    working_summary: dict[str, object],
    current_step: int,
    max_steps: int,
) -> dict[str, object]:
    return {
        "message": normalized_input.message,
        "available_tool_refs": normalized_input.available_tool_refs,
        "available_mcp_servers": normalized_input.available_mcp_servers,
        "available_mcp_tools": normalized_input.available_mcp_tools,
        "resource_summary": _resource_summary(normalized_input),
        "current_step": current_step,
        "max_steps": max_steps,
        "remaining_steps": max_steps - current_step,
        "current_phase": current_phase,
        "working_summary": deepcopy(working_summary),
        "execution_trace": execution_trace,
        "tool_context": tool_context,
        "memory_context": normalized_input.memory_context,
        "task_memory": normalized_input.task_memory,
        "conversation_history": _conversation_history_payload(normalized_input.raw_selected_input),
        "raw_selected_input": _serializable_selected_input(normalized_input.raw_selected_input),
    }


def _normalize_decision_output(
    llm_output: dict[str, object] | None,
    *,
    normalized_input: _NormalizedTestProInput,
    llm_context: dict[str, object],
) -> tuple[dict[str, object] | None, str | None, str | None]:
    if llm_output is None:
        return None, str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")), str(
            llm_context.get("error_message", "LLM output is missing")
        )
    missing = [key for key in _decision_required_keys() if key not in llm_output]
    if missing:
        return None, "TEST_PRO_DECISION_INCOMPLETE", "Structured decision is missing required keys: " + ", ".join(missing)
    decision_type = str(llm_output.get("decision_type", "")).strip().lower()
    if decision_type not in {"respond", "tool_call"}:
        return None, "TEST_PRO_DECISION_INVALID", "decision_type must be either 'respond' or 'tool_call'"
    tool_ref = str(llm_output.get("suggested_tool_ref", "")).strip()
    tool_input = llm_output.get("suggested_tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    adjusted = False
    adjustment_reason = ""
    if decision_type == "tool_call":
        if not normalized_input.available_tool_refs:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = "No tools are assigned to this agent."
        elif not tool_ref:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = "Decision requested tool_call without a suggested_tool_ref."
        elif tool_ref not in normalized_input.available_tool_refs:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = f"Suggested tool '{tool_ref}' is not assigned to this agent."
    reply = str(llm_output.get("reply", "")).strip() or ("I can answer directly." if decision_type == "respond" else "I should call a tool next.")
    return (
        {
            "decision_type": decision_type,
            "reply": reply,
            "reasoning_summary": str(llm_output.get("reasoning_summary", "")).strip(),
            "should_use_tools": bool(llm_output.get("should_use_tools")),
            "suggested_tool_ref": tool_ref if decision_type == "tool_call" else "",
            "suggested_tool_input": tool_input if decision_type == "tool_call" else {},
            "task_kind": str(llm_output.get("task_kind", "")).strip() or "general",
            "next_step": str(llm_output.get("next_step", "")).strip() or reply,
            "adjusted": adjusted,
            "adjustment_reason": adjustment_reason,
        },
        None,
        None,
    )


def _invoke_structured_decision(
    context: ExecutionContext,
    normalized_input: _NormalizedTestProInput,
    *,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    current_phase: str,
    working_summary: dict[str, object],
    current_step: int,
    max_steps: int,
) -> tuple[dict[str, object] | None, dict[str, object]]:
    services = context.services
    if services is None or services.llm_invoker is None:
        return None, {
            "mode": "failed",
            "error_code": "MISSING_LLM_INVOKER",
            "error_message": "No LLM provider is configured",
        }
    request = LLMRequest(
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}:decision",
        profile_ref=normalized_input.llm_profile_ref,
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=json.dumps(
                    _build_loop_payload(
                        normalized_input,
                        execution_trace=execution_trace,
                        tool_context=tool_context,
                        current_phase=current_phase,
                        working_summary=working_summary,
                        current_step=current_step,
                        max_steps=max_steps,
                    ),
                    ensure_ascii=False,
                ),
            )
        ],
        system_prompt=_build_decision_system_prompt(normalized_input),
        response_format=LLMResponseFormatKind.JSON_OBJECT,
        metadata={"domain": _binding_domain(context), "mode": "structured_decision"},
    )
    result = services.llm_invoker.invoke(request, context)
    llm_context = {
        "mode": "llm" if result.success else "failed",
        "provider_ref": result.provider_ref,
        "model_name": result.model_name,
        "finish_reason": result.finish_reason,
    }
    if not result.success:
        llm_context["error_code"] = result.error_code
        llm_context["error_message"] = result.error_message
        return None, llm_context
    if isinstance(result.output_json, dict):
        return deepcopy(result.output_json), llm_context
    if result.output_text:
        try:
            parsed = json.loads(result.output_text)
        except json.JSONDecodeError:
            llm_context["error_code"] = "LLM_OUTPUT_PARSE_ERROR"
            llm_context["error_message"] = "LLM output was not valid JSON"
            return None, llm_context
        if isinstance(parsed, dict):
            return parsed, llm_context
    llm_context["error_code"] = "LLM_EMPTY_OUTPUT"
    llm_context["error_message"] = "LLM returned no structured output"
    return None, llm_context


def _build_final_response_system_prompt(normalized_input: _NormalizedTestProInput) -> str:
    return "\n\n".join(
        [
            normalized_input.system_prompt,
            "You are now in the final response step of an agent loop.",
            "Be concise, developer-facing, and mention findings, validation, and remaining risks when relevant.",
        ]
    )


def _invoke_final_response(
    context: ExecutionContext,
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    finish_reason: str,
    latest_decision: dict[str, object] | None,
    current_phase: str,
    working_summary: dict[str, object],
) -> tuple[str | None, dict[str, object]]:
    services = context.services
    if services is None or services.llm_invoker is None:
        return None, {
            "mode": "failed",
            "error_code": "MISSING_LLM_INVOKER",
            "error_message": "No LLM provider is configured",
        }
    request = LLMRequest(
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}:final",
        profile_ref=normalized_input.llm_profile_ref,
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=json.dumps(
                    {
                        "message": normalized_input.message,
                        "finish_reason": finish_reason,
                        "current_phase": current_phase,
                        "working_summary": deepcopy(working_summary),
                        "latest_decision": latest_decision,
                        "execution_trace": execution_trace,
                        "tool_context": tool_context,
                        "conversation_history": _conversation_history_payload(normalized_input.raw_selected_input),
                    },
                    ensure_ascii=False,
                ),
            )
        ],
        system_prompt=_build_final_response_system_prompt(normalized_input),
        response_format=LLMResponseFormatKind.TEXT,
        metadata={"domain": _binding_domain(context), "mode": "finalize"},
    )
    result = services.llm_invoker.invoke(request, context)
    llm_context = {
        "mode": "llm" if result.success else "failed",
        "provider_ref": result.provider_ref,
        "model_name": result.model_name,
        "finish_reason": result.finish_reason,
    }
    if not result.success:
        llm_context["error_code"] = result.error_code
        llm_context["error_message"] = result.error_message
        return None, llm_context
    reply = (result.output_text or "").strip()
    if not reply:
        llm_context["error_code"] = "LLM_EMPTY_OUTPUT"
        llm_context["error_message"] = "LLM returned no final text output"
        return None, llm_context
    return reply, llm_context


def _invoke_tool_if_available(
    context: ExecutionContext,
    *,
    tool_ref: str,
    tool_input: dict[str, object],
) -> _ToolExecutionBundle:
    services = context.services
    binding = context.agent_binding
    if services is None or services.tool_invoker is None:
        return _ToolExecutionBundle(tool_output=None, error_message="No tool invoker is configured")
    if binding is None or tool_ref not in binding.tool_refs:
        return _ToolExecutionBundle(tool_output=None, error_message=f"Tool '{tool_ref}' is not assigned to this agent")
    result = services.tool_invoker.invoke(tool_ref, deepcopy(tool_input), context)
    if not result.success:
        return _ToolExecutionBundle(
            tool_output=None,
            side_effects=deepcopy(result.side_effects),
            policy_decisions=deepcopy(result.policy_decisions),
            error_message=f"Tool '{tool_ref}' execution failed",
        )
    return _ToolExecutionBundle(
        tool_output=deepcopy(result.output) if result.output is not None else {},
        side_effects=deepcopy(result.side_effects),
        policy_decisions=deepcopy(result.policy_decisions),
    )


def _persist_memory_snapshot(
    context: ExecutionContext,
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    latest_decision: dict[str, object] | None,
    current_phase: str,
    final_reply: str,
    final_summary: str | None,
    loop_stop_reason: str,
) -> list[str]:
    services = context.services
    if services is None or services.memory_provider is None or not normalized_input.memory_scopes:
        return []
    from .shared import _changed_files_hints, _has_edit_activity, _has_validation_activity
    from .state import _task_memory_snapshot

    task_memory = _task_memory_snapshot(
        normalized_input=normalized_input,
        execution_trace=execution_trace,
        tool_context=tool_context,
        latest_decision=latest_decision,
        current_phase=current_phase,
        final_summary=final_summary or final_reply,
        loop_stop_reason=loop_stop_reason,
    )
    payload = {
        "message": normalized_input.message,
        "task_goal": normalized_input.raw_selected_input.get("task_goal"),
        "acceptance_criteria": deepcopy(normalized_input.raw_selected_input.get("acceptance_criteria")),
        "changed_files_hint": _changed_files_hints(normalized_input.raw_selected_input),
        "loop_stop_reason": loop_stop_reason,
        "summary": final_summary or final_reply,
        "reply": final_reply,
        "edited": _has_edit_activity(execution_trace),
        "validated": _has_validation_activity(execution_trace),
        "task_memory": task_memory,
        "touched_tool_refs": [
            str(entry.get("tool_ref", "")).strip()
            for entry in execution_trace
            if entry.get("kind") == "tool_call" and str(entry.get("tool_ref", "")).strip()
        ],
        "tool_context_keys": list(tool_context.keys()),
    }
    content = "\n".join(
        [
            f"User request: {normalized_input.message}",
            f"Summary: {final_summary or final_reply}",
            f"Loop stop reason: {loop_stop_reason}",
        ]
    )
    memory_ids: list[str] = []
    for scope in normalized_input.memory_scopes:
        try:
            memory_id = services.memory_provider.write(
                {
                    "scope": scope,
                    "content": content,
                    "payload": deepcopy(payload),
                    "tags": ["test_pro", "coding_task", "edit" if payload["edited"] else "read_only", loop_stop_reason],
                    "source_ref": context.run_record.run_id,
                    "metadata": {
                        "thread_id": context.thread_record.thread_id,
                        "agent_ref": context.agent_binding.agent_ref if context.agent_binding else None,
                        "recommended_memory_scope": _primary_memory_scope(context),
                    },
                },
                context=context,
            )
        except Exception:
            continue
        memory_ids.append(memory_id)
    return memory_ids
