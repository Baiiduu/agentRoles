from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import re

from core.agents import AgentImplementation
from core.contracts import ExecutionContext, NodeExecutionResult
from core.llm import LLMMessage, LLMMessageRole, LLMRequest, LLMResponseFormatKind
from core.state.models import NodeStatus
from domain_packs.operations import OPERATION_TOOL_REFS


@dataclass
class _NormalizedTestProInput:
    message: str
    llm_profile_ref: str | None
    system_prompt: str
    available_tool_refs: list[str] = field(default_factory=list)
    available_mcp_servers: list[dict[str, object]] = field(default_factory=list)
    available_mcp_tools: list[dict[str, object]] = field(default_factory=list)
    runtime_resource_context: dict[str, object] = field(default_factory=dict)
    workspace_enabled: bool = False
    raw_selected_input: dict[str, object] = field(default_factory=dict)


@dataclass
class _ToolExecutionBundle:
    tool_output: dict[str, object] | None
    side_effects: list[object] = field(default_factory=list)
    policy_decisions: list[object] = field(default_factory=list)
    error_message: str | None = None


_PREFERRED_TOOL_ORDER = [
    OPERATION_TOOL_REFS["list_files"],
    OPERATION_TOOL_REFS["ripgrep_search"],
    OPERATION_TOOL_REFS["find_in_file"],
    OPERATION_TOOL_REFS["read_file_segment"],
    OPERATION_TOOL_REFS["read_file"],
    OPERATION_TOOL_REFS["apply_patch"],
    OPERATION_TOOL_REFS["git_status"],
    OPERATION_TOOL_REFS["git_diff"],
    OPERATION_TOOL_REFS["list_dir"],
    OPERATION_TOOL_REFS["shell_run"],
]

_READ_SEARCH_TOOL_REFS = {
    OPERATION_TOOL_REFS["list_dir"],
    OPERATION_TOOL_REFS["list_files"],
    OPERATION_TOOL_REFS["read_file"],
    OPERATION_TOOL_REFS["read_file_segment"],
    OPERATION_TOOL_REFS["find_in_file"],
    OPERATION_TOOL_REFS["search_files"],
    OPERATION_TOOL_REFS["ripgrep_search"],
    OPERATION_TOOL_REFS["git_status"],
    OPERATION_TOOL_REFS["git_diff"],
}

_SHELL_FALLBACK_MESSAGE = (
    "Only use shell.run when the task cannot be handled cleanly by list/search/read/git/patch tools."
)


def _binding_domain(context: ExecutionContext) -> str:
    binding = context.agent_binding
    if binding is None:
        return "test_pro"
    value = getattr(binding, "domain", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "test_pro"


def _artifact_type(context: ExecutionContext) -> str:
    binding = context.agent_binding
    if binding is None:
        return "test_pro.chat_output"
    output_contract = getattr(binding, "output_contract", None)
    if isinstance(output_contract, dict):
        value = output_contract.get("type")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "test_pro.chat_output"


def _llm_profile_ref(context: ExecutionContext) -> str | None:
    binding = context.agent_binding
    if binding is None:
        return None
    value = binding.metadata.get("llm_profile_ref")
    return str(value).strip() if isinstance(value, str) and str(value).strip() else None


def _metadata_text(context: ExecutionContext, key: str) -> str:
    binding = context.agent_binding
    if binding is None:
        return ""
    value = binding.metadata.get(key)
    return str(value).strip() if isinstance(value, str) else ""


def _build_system_prompt(context: ExecutionContext) -> str:
    base = _metadata_text(context, "system_prompt") or (
        "You are a minimal test chat assistant."
    )
    appendix = _metadata_text(context, "instruction_appendix")
    quality_bar = _metadata_text(context, "quality_bar")
    response_style = _metadata_text(context, "response_style")
    parts = [base]
    if appendix:
        parts.append(appendix)
    if quality_bar:
        parts.append(f"Quality bar: {quality_bar}")
    if response_style:
        parts.append(f"Response style: {response_style}")
    parts.append("Reply naturally in Simplified Chinese unless the user asks for another language.")
    return "\n\n".join(parts)


def _runtime_resource_context(context: ExecutionContext) -> dict[str, object]:
    binding = context.agent_binding
    if binding is None:
        return {}
    value = binding.metadata.get("runtime_resource_context")
    return deepcopy(value) if isinstance(value, dict) else {}


def _workspace_enabled(runtime_resource_context: dict[str, object]) -> bool:
    workspace = runtime_resource_context.get("workspace")
    return bool(isinstance(workspace, dict) and workspace.get("enabled"))


def _normalize_input(context: ExecutionContext) -> _NormalizedTestProInput:
    selected_input = deepcopy(dict(context.selected_input))
    message_value = selected_input.get("message")
    message = str(message_value).strip() if isinstance(message_value, str) else ""
    runtime_resource_context = _runtime_resource_context(context)
    mcp_servers = runtime_resource_context.get("mcp_server_catalog")
    if not isinstance(mcp_servers, list):
        mcp_servers = []
    mcp_tools = runtime_resource_context.get("mcp_tools")
    if not isinstance(mcp_tools, list):
        mcp_tools = []
    return _NormalizedTestProInput(
        message=message,
        llm_profile_ref=_llm_profile_ref(context),
        system_prompt=_build_system_prompt(context),
        available_tool_refs=list(context.agent_binding.tool_refs) if context.agent_binding else [],
        available_mcp_servers=deepcopy(mcp_servers),
        available_mcp_tools=deepcopy(mcp_tools),
        runtime_resource_context=runtime_resource_context,
        workspace_enabled=_workspace_enabled(runtime_resource_context),
        raw_selected_input=selected_input,
    )


def _conversation_history_payload(raw_selected_input: dict[str, object]) -> list[dict[str, str]]:
    value = raw_selected_input.get("conversation_history")
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "agent"} and content:
            items.append({"role": role, "content": content})
    return items


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
    tool_line = (
        ", ".join(normalized_input.available_tool_refs)
        if normalized_input.available_tool_refs
        else "none"
    )
    mcp_server_lines = [
        f"- {item.get('server_ref', '')}: "
        + ", ".join(
            str(tool.get("tool_ref", ""))
            for tool in (item.get("tools") or [])
            if isinstance(tool, dict) and str(tool.get("tool_ref", "")).strip()
        )
        for item in normalized_input.available_mcp_servers
        if isinstance(item, dict) and item.get("server_ref")
    ]
    mcp_server_block = "\n".join(mcp_server_lines) if mcp_server_lines else "none"
    return "\n\n".join(
        [
            normalized_input.system_prompt,
            "You are now operating as a structured decision engine for a sandbox agent loop.",
            "At each step, decide whether the task is already answerable or whether another tool call is needed.",
            "Return a valid JSON object only.",
            "Allowed decision_type values: 'respond' or 'tool_call'.",
            "If no tool is available or tool use is unnecessary, use 'respond'.",
            f"Currently available tool refs: {tool_line}.",
            "Available MCP servers and namespaced MCP tool refs:\n" + mcp_server_block,
            f"Workspace enabled: {'yes' if normalized_input.workspace_enabled else 'no'}.",
            "Prefer these tools when possible, in roughly this order: "
            + ", ".join(
                [tool_ref for tool_ref in _PREFERRED_TOOL_ORDER if tool_ref in normalized_input.available_tool_refs]
            )
            + ".",
            "Use fs.list_files to inspect repository structure before broad shell usage.",
            "Use fs.ripgrep_search for repo-wide search, fs.find_in_file for one file, fs.read_file_segment for focused reads.",
            "Use fs.apply_patch for targeted edits after you have read enough context.",
            "When an MCP tool is needed, always select the namespaced tool_ref shown above rather than the raw MCP operation name.",
            "Prefer local filesystem and git tools for repository work. Prefer MCP tools for external systems, browsers, SaaS APIs, or remote knowledge sources.",
            _SHELL_FALLBACK_MESSAGE,
            "Keep reasoning_summary concise. reply should be the user-facing message for the current turn.",
            "suggested_tool_input must be a JSON object. Use {} when no tool input is needed.",
            "Include all required keys exactly: "
            + ", ".join(_decision_required_keys())
            + ".",
        ]
    )


def _resource_summary(normalized_input: _NormalizedTestProInput) -> dict[str, object]:
    runtime_resources = normalized_input.runtime_resource_context
    return {
        "mcp_server_count": len(normalized_input.available_mcp_servers),
        "mcp_tool_count": len(normalized_input.available_mcp_tools),
        "skill_count": len(runtime_resources.get("skills", []))
        if isinstance(runtime_resources.get("skills"), list)
        else 0,
        "workspace_enabled": normalized_input.workspace_enabled,
    }


def _extract_candidate_path(message: str) -> str | None:
    for token in re.findall(r"[\w./\\-]+\.\w+|[\w./\\-]+/", message):
        cleaned = token.strip(".,:;!?'\"()[]{}")
        if "/" in cleaned or "\\" in cleaned or "." in cleaned:
            return cleaned.rstrip("/\\")
    return None


def _extract_search_pattern(message: str) -> str | None:
    quoted = re.findall(r"['\"]([^'\"]{2,120})['\"]", message)
    if quoted:
        return quoted[0].strip()
    keyword_match = re.search(r"(?:搜索|查找|grep|search|find)\s+([^\s]+)", message, re.IGNORECASE)
    if keyword_match:
        return keyword_match.group(1).strip(".,:;!?")
    return None


def _extract_line_range(message: str) -> tuple[int | None, int | None]:
    range_match = re.search(r"(\d+)\s*[-~到至]\s*(\d+)", message)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    single_match = re.search(r"(?:line|lines|第)\s*(\d+)", message, re.IGNORECASE)
    if single_match:
        value = int(single_match.group(1))
        return value, value
    return None, None


def _has_tool_result_for_path(tool_context: dict[str, object], path: str) -> bool:
    for value in tool_context.values():
        if not isinstance(value, dict):
            continue
        tool_output = value.get("tool_output")
        if not isinstance(tool_output, dict):
            continue
        if str(tool_output.get("path", "")).strip() == path:
            return True
    return False


def _recent_tool_calls(execution_trace: list[dict[str, object]]) -> list[dict[str, object]]:
    return [entry for entry in execution_trace if entry.get("kind") == "tool_call"]


def _should_avoid_shell(
    *,
    suggested_tool_ref: str,
    message: str,
    available_tool_refs: list[str],
) -> bool:
    if suggested_tool_ref != OPERATION_TOOL_REFS["shell_run"]:
        return False
    lowered = message.lower()
    read_like = any(
        keyword in lowered
        for keyword in [
            "read",
            "open",
            "查看",
            "读取",
            "搜索",
            "查找",
            "find",
            "grep",
            "list",
            "目录",
            "文件",
            "diff",
            "git",
        ]
    )
    if not read_like:
        return False
    return any(tool_ref in available_tool_refs for tool_ref in _READ_SEARCH_TOOL_REFS)


def _preferred_tool_decision(
    *,
    normalized_input: _NormalizedTestProInput,
    tool_context: dict[str, object],
) -> tuple[str, dict[str, object], str] | None:
    message = normalized_input.message
    lowered = message.lower()
    available = set(normalized_input.available_tool_refs)
    candidate_path = _extract_candidate_path(message)
    search_pattern = _extract_search_pattern(message)
    start_line, end_line = _extract_line_range(message)

    if candidate_path and start_line and OPERATION_TOOL_REFS["read_file_segment"] in available:
        return (
            OPERATION_TOOL_REFS["read_file_segment"],
            {
                "path": candidate_path,
                "start_line": start_line,
                "end_line": end_line or start_line,
            },
            "The request points to a specific file segment, so segment read is preferred.",
        )

    if candidate_path and search_pattern and OPERATION_TOOL_REFS["find_in_file"] in available:
        return (
            OPERATION_TOOL_REFS["find_in_file"],
            {
                "path": candidate_path,
                "pattern": search_pattern,
                "limit": 20,
            },
            "The request points to one file and one pattern, so in-file search is preferred.",
        )

    if candidate_path and any(keyword in lowered for keyword in ["read", "open", "查看", "读取"]):
        if OPERATION_TOOL_REFS["read_file"] in available:
            return (
                OPERATION_TOOL_REFS["read_file"],
                {"path": candidate_path},
                "The request points to one file, so direct file read is preferred.",
            )

    if search_pattern and OPERATION_TOOL_REFS["ripgrep_search"] in available:
        return (
            OPERATION_TOOL_REFS["ripgrep_search"],
            {"pattern": search_pattern, "limit": 20},
            "A repository-wide search request should prefer ripgrep-style search.",
        )

    if any(keyword in lowered for keyword in ["list", "目录", "结构", "files", "file tree"]) and OPERATION_TOOL_REFS["list_files"] in available:
        return (
            OPERATION_TOOL_REFS["list_files"],
            {"path": ".", "recursive": True, "limit": 200},
            "A structure inspection request should prefer listing files first.",
        )

    if any(keyword in lowered for keyword in ["patch", "edit", "modify", "修改", "替换"]) and candidate_path:
        if not _has_tool_result_for_path(tool_context, candidate_path) and OPERATION_TOOL_REFS["read_file"] in available:
            return (
                OPERATION_TOOL_REFS["read_file"],
                {"path": candidate_path},
                "Before patching, read the target file to gather context.",
            )

    return None


def _apply_policy_to_decision(
    decision: dict[str, object],
    *,
    normalized_input: _NormalizedTestProInput,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
    current_step: int,
) -> dict[str, object]:
    adjusted_decision = deepcopy(decision)
    adjusted = bool(adjusted_decision.get("adjusted"))
    adjustment_reasons: list[str] = []
    if adjusted and adjusted_decision.get("adjustment_reason"):
        adjustment_reasons.append(str(adjusted_decision["adjustment_reason"]))

    preferred = _preferred_tool_decision(
        normalized_input=normalized_input,
        tool_context=tool_context,
    )
    if preferred is not None:
        preferred_tool_ref, preferred_tool_input, preferred_reason = preferred
        current_tool_ref = str(adjusted_decision.get("suggested_tool_ref", "")).strip()
        current_decision_type = str(adjusted_decision.get("decision_type", "respond"))
        if (
            current_decision_type == "respond"
            or current_tool_ref == OPERATION_TOOL_REFS["shell_run"]
            or current_tool_ref not in normalized_input.available_tool_refs
        ):
            adjusted_decision["decision_type"] = "tool_call"
            adjusted_decision["should_use_tools"] = True
            adjusted_decision["suggested_tool_ref"] = preferred_tool_ref
            adjusted_decision["suggested_tool_input"] = preferred_tool_input
            adjusted = True
            adjustment_reasons.append(preferred_reason)

    if _should_avoid_shell(
        suggested_tool_ref=str(adjusted_decision.get("suggested_tool_ref", "")).strip(),
        message=normalized_input.message,
        available_tool_refs=normalized_input.available_tool_refs,
    ):
        preferred = _preferred_tool_decision(
            normalized_input=normalized_input,
            tool_context=tool_context,
        )
        if preferred is not None:
            preferred_tool_ref, preferred_tool_input, preferred_reason = preferred
            adjusted_decision["suggested_tool_ref"] = preferred_tool_ref
            adjusted_decision["suggested_tool_input"] = preferred_tool_input
            adjusted = True
            adjustment_reasons.append(
                f"shell.run was downgraded because a more specific tool is available. {preferred_reason}"
            )

    recent_calls = _recent_tool_calls(execution_trace)
    if recent_calls:
        last_call = recent_calls[-1]
        current_tool_ref = str(adjusted_decision.get("suggested_tool_ref", "")).strip()
        current_tool_input = adjusted_decision.get("suggested_tool_input")
        if (
            str(adjusted_decision.get("decision_type")) == "tool_call"
            and current_tool_ref == str(last_call.get("tool_ref", "")).strip()
            and isinstance(current_tool_input, dict)
            and current_tool_input == last_call.get("tool_input")
        ):
            adjusted_decision["decision_type"] = "respond"
            adjusted_decision["should_use_tools"] = False
            adjusted_decision["suggested_tool_ref"] = ""
            adjusted_decision["suggested_tool_input"] = {}
            adjusted_decision["reply"] = str(adjusted_decision.get("reply") or "I have enough information to summarize the current findings.")
            adjusted_decision["next_step"] = "Summarize the findings instead of repeating the same tool call."
            adjusted = True
            adjustment_reasons.append("Repeated identical tool call was prevented.")

    if current_step >= 3 and str(adjusted_decision.get("decision_type")) == "tool_call":
        same_tool_count = sum(
            1
            for entry in recent_calls
            if str(entry.get("tool_ref", "")).strip()
            == str(adjusted_decision.get("suggested_tool_ref", "")).strip()
        )
        if same_tool_count >= 2:
            adjusted_decision["decision_type"] = "respond"
            adjusted_decision["should_use_tools"] = False
            adjusted_decision["suggested_tool_ref"] = ""
            adjusted_decision["suggested_tool_input"] = {}
            adjusted_decision["next_step"] = "Stop the loop and summarize the most useful evidence already collected."
            adjusted = True
            adjustment_reasons.append("The same tool has already been used multiple times in this run.")

    adjusted_decision["adjusted"] = adjusted
    adjusted_decision["adjustment_reason"] = " ".join(adjustment_reasons).strip()
    return adjusted_decision


def _build_loop_payload(
    normalized_input: _NormalizedTestProInput,
    *,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
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
        "execution_trace": execution_trace,
        "tool_context": tool_context,
        "conversation_history": _conversation_history_payload(normalized_input.raw_selected_input),
        "raw_selected_input": normalized_input.raw_selected_input,
    }


def _invoke_structured_decision(
    context: ExecutionContext,
    normalized_input: _NormalizedTestProInput,
    *,
    execution_trace: list[dict[str, object]],
    tool_context: dict[str, object],
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
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}:test-pro-decision",
        profile_ref=normalized_input.llm_profile_ref,
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=json.dumps(
                    _build_loop_payload(
                        normalized_input,
                        execution_trace=execution_trace,
                        tool_context=tool_context,
                        current_step=current_step,
                        max_steps=max_steps,
                    ),
                    ensure_ascii=False,
                ),
            )
        ],
        system_prompt=_build_decision_system_prompt(normalized_input),
        response_format=LLMResponseFormatKind.JSON_OBJECT,
        metadata={
            "agent_ref": context.agent_binding.agent_ref if context.agent_binding else None,
            "node_id": context.node_spec.node_id,
            "domain": _binding_domain(context),
            "mode": "structured_decision",
        },
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
    if result.output_json is not None and isinstance(result.output_json, dict):
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


def _normalize_decision_output(
    llm_output: dict[str, object] | None,
    *,
    normalized_input: _NormalizedTestProInput,
    llm_context: dict[str, object],
) -> tuple[dict[str, object] | None, str | None, str | None]:
    if llm_output is None:
        return (
            None,
            str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
            str(llm_context.get("error_message", "LLM output is missing")),
        )

    missing_keys = [key for key in _decision_required_keys() if key not in llm_output]
    if missing_keys:
        return (
            None,
            "TEST_PRO_DECISION_INCOMPLETE",
            f"Structured decision is missing required keys: {', '.join(missing_keys)}",
        )

    decision_type = str(llm_output.get("decision_type", "")).strip().lower()
    if decision_type not in {"respond", "tool_call"}:
        return (
            None,
            "TEST_PRO_DECISION_INVALID",
            "decision_type must be either 'respond' or 'tool_call'",
        )

    suggested_tool_ref = str(llm_output.get("suggested_tool_ref", "")).strip()
    suggested_tool_input = llm_output.get("suggested_tool_input")
    if not isinstance(suggested_tool_input, dict):
        suggested_tool_input = {}

    adjusted = False
    adjustment_reason = ""
    if decision_type == "tool_call":
        if not normalized_input.available_tool_refs:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = "No tools are assigned to this agent."
        elif not suggested_tool_ref:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = "Decision requested tool_call without a suggested_tool_ref."
        elif suggested_tool_ref not in normalized_input.available_tool_refs:
            decision_type = "respond"
            adjusted = True
            adjustment_reason = (
                f"Suggested tool '{suggested_tool_ref}' is not assigned to this agent."
            )

    reply = str(llm_output.get("reply", "")).strip()
    if not reply:
        reply = (
            "I can answer directly."
            if decision_type == "respond"
            else "I should call a tool next."
        )

    normalized_decision = {
        "decision_type": decision_type,
        "reply": reply,
        "reasoning_summary": str(llm_output.get("reasoning_summary", "")).strip(),
        "should_use_tools": bool(llm_output.get("should_use_tools")),
        "suggested_tool_ref": suggested_tool_ref if decision_type == "tool_call" else "",
        "suggested_tool_input": suggested_tool_input if decision_type == "tool_call" else {},
        "task_kind": str(llm_output.get("task_kind", "")).strip() or "general",
        "next_step": str(llm_output.get("next_step", "")).strip() or reply,
        "adjusted": adjusted,
        "adjustment_reason": adjustment_reason,
    }
    return normalized_decision, None, None


def _invoke_tool_if_available(
    context: ExecutionContext,
    *,
    tool_ref: str,
    tool_input: dict[str, object],
) -> _ToolExecutionBundle:
    services = context.services
    if services is None or services.tool_invoker is None:
        return _ToolExecutionBundle(
            tool_output=None,
            error_message="No tool invoker is configured",
        )
    binding = context.agent_binding
    if binding is None or tool_ref not in binding.tool_refs:
        return _ToolExecutionBundle(
            tool_output=None,
            error_message=f"Tool '{tool_ref}' is not assigned to this agent",
        )

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


def _build_final_response_system_prompt(normalized_input: _NormalizedTestProInput) -> str:
    return "\n\n".join(
        [
            normalized_input.system_prompt,
            "You are now in the final response step of an agent loop.",
            "Use the collected tool results and trace when they are relevant and available.",
            "Explain what you accomplished in clear Simplified Chinese.",
            "Be concise but concrete. Mention limitations if the tool failed or returned incomplete data.",
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
) -> tuple[str | None, dict[str, object]]:
    services = context.services
    if services is None or services.llm_invoker is None:
        return None, {
            "mode": "failed",
            "error_code": "MISSING_LLM_INVOKER",
            "error_message": "No LLM provider is configured",
        }

    request = LLMRequest(
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}:test-pro-final",
        profile_ref=normalized_input.llm_profile_ref,
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=json.dumps(
                    {
                        "message": normalized_input.message,
                        "finish_reason": finish_reason,
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
        metadata={
            "agent_ref": context.agent_binding.agent_ref if context.agent_binding else None,
            "node_id": context.node_spec.node_id,
            "domain": _binding_domain(context),
            "mode": "agent_loop_finalize",
        },
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
                    "llm_context": {
                        "mode": "failed",
                        "error_code": "MISSING_LLM_INVOKER",
                    },
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

        for current_step in range(1, max_steps + 1):
            llm_output, llm_context = _invoke_structured_decision(
                context,
                normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                current_step=current_step,
                max_steps=max_steps,
            )
            decision, error_code, error_message = _normalize_decision_output(
                llm_output,
                normalized_input=normalized_input,
                llm_context=llm_context,
            )
            decision_contexts.append(
                {
                    "step": current_step,
                    "context": llm_context,
                }
            )
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
                current_step=current_step,
            )
            latest_decision = decision
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "decision",
                    "loop_step": current_step,
                    "decision_type": decision["decision_type"],
                    "task_kind": decision["task_kind"],
                    "reasoning_summary": decision["reasoning_summary"],
                    "adjusted": decision["adjusted"],
                    "adjustment_reason": decision["adjustment_reason"],
                }
            )

            if str(decision["decision_type"]) == "respond":
                final_reply = str(decision["reply"])
                final_summary = str(decision["next_step"])
                loop_stop_reason = "decision_respond"
                break

            tool_ref = str(decision["suggested_tool_ref"])
            tool_input = (
                deepcopy(decision["suggested_tool_input"])
                if isinstance(decision["suggested_tool_input"], dict)
                else {}
            )
            tool_bundle = _invoke_tool_if_available(
                context,
                tool_ref=tool_ref,
                tool_input=tool_input,
            )
            collected_side_effects.extend(tool_bundle.side_effects)
            collected_policy_decisions.extend(tool_bundle.policy_decisions)
            tool_key = f"step_{current_step}:{tool_ref}"
            tool_context[tool_key] = {
                "tool_ref": tool_ref,
                "tool_input": tool_input,
                "tool_output": tool_bundle.tool_output,
                "tool_error": tool_bundle.error_message,
                "loop_step": current_step,
            }
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "tool_call",
                    "loop_step": current_step,
                    "tool_ref": tool_ref,
                    "tool_input": tool_input,
                    "tool_success": tool_bundle.tool_output is not None,
                    "tool_error": tool_bundle.error_message,
                }
            )

        if final_reply is None:
            loop_stop_reason = "max_steps_reached"
            final_reply, final_llm_context = _invoke_final_response(
                context,
                normalized_input=normalized_input,
                execution_trace=execution_trace,
                tool_context=tool_context,
                finish_reason=loop_stop_reason,
                latest_decision=latest_decision,
            )
            if final_reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(final_llm_context.get("error_code", "TEST_PRO_FINALIZE_FAILED")),
                    error_message=str(
                        final_llm_context.get("error_message", "Final response generation failed")
                    ),
                    side_effects=collected_side_effects,
                    policy_decisions=collected_policy_decisions,
                    metadata={
                        "llm_context": {
                            "decision_steps": decision_contexts,
                            "finalize": final_llm_context,
                        }
                    },
                )
            final_summary = final_reply
            execution_trace.append(
                {
                    "step": len(execution_trace) + 1,
                    "kind": "finalize",
                    "finish_reason": loop_stop_reason,
                }
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
            "normalized_input": {
                "message": normalized_input.message,
                "llm_profile_ref": normalized_input.llm_profile_ref,
                "available_tool_refs": normalized_input.available_tool_refs,
                "available_mcp_servers": normalized_input.available_mcp_servers,
                "available_mcp_tools": normalized_input.available_mcp_tools,
                "runtime_resource_context": normalized_input.runtime_resource_context,
                "workspace_enabled": normalized_input.workspace_enabled,
            },
            "llm_context": {
                "decision_steps": decision_contexts,
            },
        }
        if loop_stop_reason == "max_steps_reached":
            output["llm_context"]["finalize"] = final_llm_context
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=deepcopy(output),
            side_effects=collected_side_effects,
            policy_decisions=collected_policy_decisions,
            artifact_type=_artifact_type(context),
        )


_TEST_PRO_AGENT_IMPLEMENTATION_TYPES = [
    TestProChatImplementation,
]


def get_test_pro_agent_implementations() -> list[AgentImplementation]:
    return [implementation_type() for implementation_type in _TEST_PRO_AGENT_IMPLEMENTATION_TYPES]
