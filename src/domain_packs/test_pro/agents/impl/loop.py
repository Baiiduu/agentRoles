from __future__ import annotations

from copy import deepcopy

from core.agents import AgentImplementation
from core.contracts import ExecutionContext, NodeExecutionResult
from core.state.models import NodeStatus

from .llm_loop import (
    _invoke_final_response,
    _invoke_structured_decision,
    _invoke_tool_if_available,
    _normalize_decision_output,
    _persist_memory_snapshot,
)
from .policy import _apply_policy_to_decision
from .shared import _NormalizedTestProInput, _artifact_type, _emit_progress, _normalize_input, _primary_memory_scope
from .state import _build_working_summary, _enrich_final_reply, _infer_current_phase, _task_state, _validation_plan


class TestProChatImplementation:
    implementation_ref = "test_pro.chat"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        normalized_input = _normalize_input(context)
        if not normalized_input.message:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code="TEST_PRO_MESSAGE_REQUIRED",
                error_message="message must be non-empty",
            )

        services = context.services
        if services is None or services.llm_invoker is None:
            fallback = "Test Pro Chat is ready, but no LLM provider is configured yet."
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={
                    "reply": fallback,
                    "summary": fallback,
                    "mode": "fallback",
                    "normalized_input": {
                        "available_tool_refs": normalized_input.available_tool_refs,
                        "available_mcp_servers": normalized_input.available_mcp_servers,
                        "available_mcp_tools": normalized_input.available_mcp_tools,
                        "runtime_resource_context": normalized_input.runtime_resource_context,
                        "workspace_enabled": normalized_input.workspace_enabled,
                    },
                    "llm_context": {"mode": "failed", "error_code": "MISSING_LLM_INVOKER"},
                },
                artifact_type=_artifact_type(context),
            )

        max_steps = 4
        execution_trace: list[dict[str, object]] = []
        tool_context: dict[str, object] = {}
        collected_side_effects: list[object] = []
        collected_policy_decisions: list[object] = []
        decision_contexts: list[dict[str, object]] = []
        latest_decision: dict[str, object] | None = None
        final_reply: str | None = None
        final_summary: str | None = None
        loop_stop_reason = "unknown"

        current_phase = _infer_current_phase(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            latest_decision=None,
        )
        working_summary = _build_working_summary(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            latest_decision=None,
            current_phase=current_phase,
        )
        _emit_progress(
            normalized_input,
            kind="phase",
            stage="understand",
            current_phase=current_phase,
            summary="Analyzing the task and current workspace context.",
        )

        for step in range(1, max_steps + 1):
            _emit_progress(
                normalized_input,
                kind="phase",
                stage="reasoning",
                current_phase=current_phase,
                summary=f"Planning step {step} of {max_steps}.",
                current_activity="Thinking about the next best action.",
            )
            llm_output, llm_context = _invoke_structured_decision(
                context,
                normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                current_phase=current_phase,
                working_summary=working_summary,
                current_step=step,
                max_steps=max_steps,
            )
            decision, error_code, error_message = _normalize_decision_output(
                llm_output,
                normalized_input=normalized_input,
                llm_context=llm_context,
            )
            decision_contexts.append({"step": step, "context": llm_context})
            if decision is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=error_code or "TEST_PRO_DECISION_FAILED",
                    error_message=error_message or "Structured decision failed",
                    side_effects=collected_side_effects,
                    policy_decisions=collected_policy_decisions,
                    metadata={"llm_context": {"decision_steps": decision_contexts}},
                )

            decision = _apply_policy_to_decision(
                decision,
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                current_step=step,
            )
            if (
                services.tool_invoker is None
                and str(decision.get("decision_type")) == "tool_call"
            ):
                decision["decision_type"] = "respond"
                decision["should_use_tools"] = False
                decision["suggested_tool_ref"] = ""
                decision["suggested_tool_input"] = {}
                decision["adjusted"] = True
                prior_reason = str(decision.get("adjustment_reason", "")).strip()
                extra_reason = "Tool execution is unavailable in the current runtime."
                decision["adjustment_reason"] = (
                    f"{prior_reason} {extra_reason}".strip() if prior_reason else extra_reason
                )
                next_step = str(decision.get("next_step", "")).strip()
                if next_step:
                    decision["next_step"] = f"{next_step} Summarize the missing prerequisites instead."
                else:
                    decision["next_step"] = "Summarize the missing prerequisites instead."
            latest_decision = decision
            current_phase = _infer_current_phase(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                latest_decision=latest_decision,
            )
            working_summary = _build_working_summary(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                latest_decision=latest_decision,
                current_phase=current_phase,
            )
            _emit_progress(
                normalized_input,
                kind="decision",
                stage="decision",
                current_phase=current_phase,
                summary=str(decision["reasoning_summary"]),
                current_activity=(
                    "Preparing the final response."
                    if str(decision["decision_type"]) == "respond"
                    else f"Preparing to use tool {decision['suggested_tool_ref']}."
                ),
                tool_ref=str(decision["suggested_tool_ref"]),
            )
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "decision",
                    "loop_step": step,
                    "current_phase": current_phase,
                    "decision_type": decision["decision_type"],
                    "task_kind": decision["task_kind"],
                    "reasoning_summary": decision["reasoning_summary"],
                    "adjusted": decision["adjusted"],
                    "adjustment_reason": decision["adjustment_reason"],
                }
            )

            if str(decision["decision_type"]) == "respond":
                final_reply = _enrich_final_reply(
                    str(decision["reply"]),
                    normalized_input=normalized_input,
                    execution_trace=execution_trace,
                )
                final_summary = _enrich_final_reply(
                    str(decision["next_step"]),
                    normalized_input=normalized_input,
                    execution_trace=execution_trace,
                )
                loop_stop_reason = "decision_respond"
                break

            tool_ref = str(decision["suggested_tool_ref"])
            tool_input = deepcopy(decision["suggested_tool_input"]) if isinstance(decision["suggested_tool_input"], dict) else {}
            _emit_progress(
                normalized_input,
                kind="tool",
                stage="tool_call",
                current_phase=current_phase,
                summary=f"Calling tool {tool_ref}.",
                current_activity=f"Running {tool_ref}.",
                tool_ref=tool_ref,
            )
            tool_bundle = _invoke_tool_if_available(context, tool_ref=tool_ref, tool_input=tool_input)
            collected_side_effects.extend(tool_bundle.side_effects)
            collected_policy_decisions.extend(tool_bundle.policy_decisions)
            tool_context[f"step_{step}:{tool_ref}"] = {
                "tool_ref": tool_ref,
                "tool_input": deepcopy(tool_input),
                "tool_output": deepcopy(tool_bundle.tool_output),
                "tool_error": tool_bundle.error_message,
                "loop_step": step,
            }
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "tool_call",
                    "loop_step": step,
                    "current_phase": current_phase,
                    "tool_ref": tool_ref,
                    "tool_input": deepcopy(tool_input),
                    "tool_success": tool_bundle.tool_output is not None,
                    "tool_error": tool_bundle.error_message,
                }
            )
            current_phase = _infer_current_phase(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                latest_decision=latest_decision,
            )
            working_summary = _build_working_summary(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                latest_decision=latest_decision,
                current_phase=current_phase,
            )
            _emit_progress(
                normalized_input,
                kind="tool_result",
                stage="tool_result",
                current_phase=current_phase,
                summary=(f"Tool {tool_ref} finished." if tool_bundle.tool_output is not None else f"Tool {tool_ref} failed."),
                current_activity="Reviewing tool output and deciding the next step.",
                tool_ref=tool_ref,
            )

        if final_reply is None:
            loop_stop_reason = "max_steps_reached"
            current_phase = _infer_current_phase(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                latest_decision=latest_decision,
                loop_stop_reason=loop_stop_reason,
            )
            working_summary = _build_working_summary(
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                latest_decision=latest_decision,
                current_phase=current_phase,
            )
            _emit_progress(
                normalized_input,
                kind="finalize",
                stage="finalize",
                current_phase=current_phase,
                summary="Generating the final response from the collected context.",
                current_activity="Summarizing findings, edits, and remaining risks.",
            )
            final_reply, final_llm_context = _invoke_final_response(
                context,
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                finish_reason=loop_stop_reason,
                latest_decision=latest_decision,
                current_phase=current_phase,
                working_summary=working_summary,
            )
            if final_reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(final_llm_context.get("error_code", "TEST_PRO_FINALIZE_FAILED")),
                    error_message=str(final_llm_context.get("error_message", "Final response generation failed")),
                    side_effects=collected_side_effects,
                    policy_decisions=collected_policy_decisions,
                    metadata={"llm_context": {"decision_steps": decision_contexts, "finalize": final_llm_context}},
                )
            final_reply = _enrich_final_reply(
                final_reply,
                normalized_input=normalized_input,
                execution_trace=execution_trace,
            )
            final_summary = final_reply
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "finalize",
                    "current_phase": current_phase,
                    "finish_reason": loop_stop_reason,
                }
            )

        current_phase = _infer_current_phase(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            latest_decision=latest_decision,
            loop_stop_reason=loop_stop_reason,
        )
        working_summary = _build_working_summary(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            latest_decision=latest_decision,
            current_phase=current_phase,
        )
        validation_plan = _validation_plan(normalized_input, execution_trace)
        task_state = _task_state(
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            latest_decision=latest_decision,
            current_phase=current_phase,
        )
        output = {
            "reply": final_reply,
            "summary": final_summary,
            "mode": "agent_loop",
            "decision": latest_decision,
            "execution_trace": execution_trace,
            "tool_context": tool_context,
            "loop_stop_reason": loop_stop_reason,
            "max_steps": max_steps,
            "current_phase": current_phase,
            "working_summary": working_summary,
            "task_state": task_state,
            "validation_plan": validation_plan,
            "normalized_input": {
                "message": normalized_input.message,
                "llm_profile_ref": normalized_input.llm_profile_ref,
                "available_tool_refs": normalized_input.available_tool_refs,
                "available_mcp_servers": normalized_input.available_mcp_servers,
                "available_mcp_tools": normalized_input.available_mcp_tools,
                "runtime_resource_context": normalized_input.runtime_resource_context,
                "workspace_enabled": normalized_input.workspace_enabled,
                "memory_scopes": normalized_input.memory_scopes,
            },
            "memory_context": normalized_input.memory_context,
            "recommended_memory_scope": _primary_memory_scope(context),
            "llm_context": {"decision_steps": decision_contexts},
        }
        output["memory_write_ids"] = _persist_memory_snapshot(
            context,
            normalized_input=normalized_input,
            execution_trace=execution_trace,
            tool_context=tool_context,
            final_reply=str(final_reply),
            final_summary=final_summary,
            loop_stop_reason=loop_stop_reason,
        )
        _emit_progress(
            normalized_input,
            kind="complete",
            stage="completed",
            current_phase=current_phase,
            summary="Agent completed the turn.",
            current_activity="Final response is ready.",
            status="completed",
            detail={"validation_plan": deepcopy(validation_plan)},
        )
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=deepcopy(output),
            side_effects=collected_side_effects,
            policy_decisions=collected_policy_decisions,
            artifact_type=_artifact_type(context),
        )


_TEST_PRO_AGENT_IMPLEMENTATION_TYPES = [TestProChatImplementation]


def get_test_pro_agent_implementations() -> list[AgentImplementation]:
    return [implementation_type() for implementation_type in _TEST_PRO_AGENT_IMPLEMENTATION_TYPES]
