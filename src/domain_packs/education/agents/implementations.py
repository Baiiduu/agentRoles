from __future__ import annotations

from copy import deepcopy
import json
import re
from dataclasses import dataclass, field

from core.agents import AgentImplementation
from core.contracts import ExecutionContext, NodeExecutionResult
from core.llm import LLMMessage, LLMMessageRole, LLMRequest, LLMResponseFormatKind
from core.state.models import NodeStatus, PolicyDecisionRecord, SideEffectRecord

from domain_packs.education.tools.constants import EDUCATION_TOOL_REFS


def _copy_input(context: ExecutionContext) -> dict[str, object]:
    selected_input = deepcopy(dict(context.selected_input))
    if set(selected_input) == {"value"} and isinstance(selected_input["value"], str):
        raw_value = selected_input["value"]
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return selected_input
        if isinstance(parsed, dict):
            return parsed
    return selected_input


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def _primary_memory_scope(context: ExecutionContext) -> str | None:
    binding = context.agent_binding
    if binding is None or not binding.memory_scopes:
        return None
    return binding.memory_scopes[0]


def _llm_profile_ref(context: ExecutionContext) -> str | None:
    binding = context.agent_binding
    if binding is None:
        return None
    value = binding.metadata.get("llm_profile_ref")
    return str(value) if isinstance(value, str) and value else None


def _agent_metadata_text(context: ExecutionContext, key: str) -> str:
    binding = context.agent_binding
    if binding is None:
        return ""
    value = binding.metadata.get(key)
    return str(value).strip() if isinstance(value, str) else ""


def _runtime_resource_context(context: ExecutionContext) -> dict[str, object]:
    binding = context.agent_binding
    if binding is None:
        return {}
    value = binding.metadata.get("runtime_resource_context")
    return deepcopy(value) if isinstance(value, dict) else {}


def _build_agent_system_prompt(
    context: ExecutionContext,
    *,
    output_keys: list[str],
) -> str:
    system_prompt = _agent_metadata_text(context, "system_prompt")
    instruction_appendix = _agent_metadata_text(context, "instruction_appendix")
    quality_bar = _agent_metadata_text(context, "quality_bar")
    response_style = _agent_metadata_text(context, "response_style")
    if not system_prompt:
        raise ValueError("agent system_prompt config is missing")
    parts = [system_prompt]
    if instruction_appendix:
        parts.append(instruction_appendix)
    if quality_bar:
        parts.append(f"Quality bar: {quality_bar}")
    if response_style:
        parts.append(f"Response style: {response_style}")
    runtime_resources = _runtime_resource_context(context)
    if runtime_resources:
        mcp_servers = runtime_resources.get("mcp_servers")
        skills = runtime_resources.get("skills")
        workspace = runtime_resources.get("workspace")
        resource_lines: list[str] = []
        if isinstance(mcp_servers, list) and mcp_servers:
            resource_lines.append(
                "Available MCP servers: "
                + ", ".join(
                    str(item.get("server_ref", ""))
                    for item in mcp_servers
                    if isinstance(item, dict) and item.get("server_ref")
                )
            )
        if isinstance(skills, list) and skills:
            resource_lines.append(
                "Available skills: "
                + ", ".join(
                    str(item.get("skill_name", ""))
                    for item in skills
                    if isinstance(item, dict) and item.get("skill_name")
                )
            )
        if isinstance(workspace, dict) and workspace.get("enabled") and workspace.get("relative_path"):
            resource_lines.append(
                f"Workspace directory available inside project: {workspace.get('relative_path')}"
            )
        if resource_lines:
            parts.append("Runtime resources for this session:\n" + "\n".join(resource_lines))
    parts.append(
        "Return a valid JSON object only. Include all required keys exactly: "
        + ", ".join(output_keys)
        + "."
    )
    return "\n\n".join(parts)


def _strip_json_only_instructions(text: str) -> str:
    cleaned = text
    for pattern in (
        r"只返回\s*JSON[。.]?",
        r"只返回\s*json[。.]?",
        r"Return a valid JSON object only\.?",
        r"Return JSON only\.?",
    ):
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _chat_message(payload: dict[str, object]) -> str:
    value = payload.get("message")
    return str(value).strip() if isinstance(value, str) else ""


def _conversation_messages(payload: dict[str, object], *, current_message: str) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    history = payload.get("conversation_history")
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                messages.append(LLMMessage(role=LLMMessageRole.USER, content=content))
            elif role == "agent":
                messages.append(LLMMessage(role=LLMMessageRole.ASSISTANT, content=content))
    messages.append(LLMMessage(role=LLMMessageRole.USER, content=current_message))
    return messages


def _has_meaningful_signal(payload: dict[str, object], keys: list[str]) -> bool:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(str(item).strip() for item in value):
            return True
        if isinstance(value, dict) and value:
            return True
    return False


def _looks_like_general_chat(message: str) -> bool:
    lowered = message.strip().lower()
    if not lowered:
        return False
    chat_markers = (
        "你好",
        "介绍你自己",
        "你是谁",
        "你能做什么",
        "说说你自己",
        "给出你的上下文",
        "介绍一下你",
        "hello",
        "hi",
        "who are you",
        "introduce yourself",
        "what can you do",
        "your context",
    )
    return any(marker in lowered for marker in chat_markers)


def _should_use_conversation_mode(
    context: ExecutionContext,
    payload: dict[str, object],
    *,
    signal_keys: list[str],
) -> bool:
    if context.trace_context.get("scope") != "agent_playground":
        return False
    message = _chat_message(payload)
    return bool(message)


def _build_chat_system_prompt(context: ExecutionContext, *, role_summary: str) -> str:
    base_prompt = _strip_json_only_instructions(_agent_metadata_text(context, "system_prompt"))
    instruction_appendix = _strip_json_only_instructions(
        _agent_metadata_text(context, "instruction_appendix")
    )
    quality_bar = _agent_metadata_text(context, "quality_bar")
    parts = [
        base_prompt or role_summary,
        "You are in direct chat mode inside Agent Playground.",
        "Reply naturally in Simplified Chinese.",
        "Do not return JSON.",
        "Act like a real educational specialist agent in conversation.",
    ]
    if instruction_appendix:
        parts.append(instruction_appendix)
    if quality_bar:
        parts.append(f"Quality bar: {quality_bar}")
    return "\n\n".join(part for part in parts if part)


def _maybe_invoke_llm_text(
    context: ExecutionContext,
    *,
    system_prompt: str,
    user_message: str,
    payload: dict[str, object] | None = None,
) -> tuple[str | None, dict[str, object]]:
    services = context.services
    if services is None or services.llm_invoker is None:
        return None, {
            "mode": "failed",
            "reason": "missing_llm_invoker",
            "error_code": "MISSING_LLM_INVOKER",
        }
    request = LLMRequest(
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}:chat",
        profile_ref=_llm_profile_ref(context),
        messages=_conversation_messages(payload or {}, current_message=user_message),
        system_prompt=system_prompt,
        response_format=LLMResponseFormatKind.TEXT,
        metadata={
            "agent_ref": context.agent_binding.agent_ref if context.agent_binding else None,
            "node_id": context.node_spec.node_id,
            "mode": "conversation",
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
    text = (result.output_text or "").strip()
    if not text:
        llm_context["error_code"] = "LLM_EMPTY_OUTPUT"
        llm_context["error_message"] = "LLM returned no text output"
        return None, llm_context
    return text, llm_context


def _conversation_result(
    context: ExecutionContext,
    *,
    reply: str,
    llm_context: dict[str, object],
    tool_bundle: _ToolUseBundle | None = None,
    artifact_type: str = "education.agent_conversation",
) -> NodeExecutionResult:
    output = {
        "reply": reply,
        "summary": reply,
        "mode": "conversation",
        "llm_context": llm_context,
    }
    if tool_bundle is not None and tool_bundle.outputs:
        output["tool_context"] = tool_bundle.outputs
    return NodeExecutionResult(
        status=NodeStatus.SUCCEEDED,
        output=output,
        side_effects=tool_bundle.side_effects if tool_bundle is not None else [],
        policy_decisions=tool_bundle.policy_decisions if tool_bundle is not None else [],
        artifact_type=artifact_type,
    )


@dataclass
class _ToolUseBundle:
    outputs: dict[str, dict[str, object]] = field(default_factory=dict)
    side_effects: list[SideEffectRecord] = field(default_factory=list)
    policy_decisions: list[PolicyDecisionRecord] = field(default_factory=list)


def _tool_allowed(context: ExecutionContext, tool_ref: str) -> bool:
    binding = context.agent_binding
    if binding is None:
        return False
    return tool_ref in binding.tool_refs


def _invoke_tool_if_available(
    context: ExecutionContext,
    *,
    tool_ref: str,
    tool_input: dict[str, object],
) -> tuple[dict[str, object] | None, list[SideEffectRecord], list[PolicyDecisionRecord]]:
    services = context.services
    if services is None or services.tool_invoker is None:
        return None, [], []
    if not _tool_allowed(context, tool_ref):
        return None, [], []

    result = services.tool_invoker.invoke(tool_ref, deepcopy(tool_input), context)
    if not result.success or result.output is None:
        return None, deepcopy(result.side_effects), deepcopy(result.policy_decisions)
    return (
        deepcopy(result.output),
        deepcopy(result.side_effects),
        deepcopy(result.policy_decisions),
    )


def _merge_tool_bundle(
    bundle: _ToolUseBundle,
    *,
    key: str,
    output: dict[str, object] | None,
    side_effects: list[SideEffectRecord],
    policy_decisions: list[PolicyDecisionRecord],
) -> None:
    if output is not None:
        bundle.outputs[key] = output
    bundle.side_effects.extend(side_effects)
    bundle.policy_decisions.extend(policy_decisions)


def _workspace_tool_available(context: ExecutionContext, tool_ref: str) -> bool:
    return _tool_allowed(context, tool_ref)


def _match_path(message: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        matched = re.search(pattern, message, flags=re.IGNORECASE)
        if matched:
            return matched.group(1).strip().strip("\"'")
    return None


def _maybe_handle_workspace_request(
    context: ExecutionContext,
    payload: dict[str, object],
) -> tuple[str, dict[str, object], _ToolUseBundle] | None:
    message = _chat_message(payload)
    if not message:
        return None

    tool_ref: str | None = None
    tool_input: dict[str, object] = {}

    if (
        ("列出" in message or "查看" in message or "list" in message.lower())
        and ("目录" in message or "workspace" in message.lower() or "文件" in message)
        and _workspace_tool_available(context, "fs.list_dir")
    ):
        tool_ref = "fs.list_dir"
        tool_input = {"path": "."}
    else:
        read_path = _match_path(
            message,
            [
                r"(?:读取|打开|查看)\s*文件\s*[:：]?\s*([^\s]+)",
                r"(?:read|open)\s+file\s+([^\s]+)",
            ],
        )
        if read_path and _workspace_tool_available(context, "fs.read_file"):
            tool_ref = "fs.read_file"
            tool_input = {"path": read_path}

    if tool_ref is None:
        mkdir_path = _match_path(
            message,
            [
                r"(?:创建|新建)\s*(?:目录|文件夹)\s*[:：]?\s*([^\s]+)",
                r"(?:make|create)\s+(?:dir|directory|folder)\s+([^\s]+)",
            ],
        )
        if mkdir_path and _workspace_tool_available(context, "fs.make_dir"):
            tool_ref = "fs.make_dir"
            tool_input = {"path": mkdir_path}

    if tool_ref is None:
        delete_path = _match_path(
            message,
            [
                r"(?:删除)\s*文件\s*[:：]?\s*([^\s]+)",
                r"(?:delete|remove)\s+file\s+([^\s]+)",
            ],
        )
        if delete_path and _workspace_tool_available(context, "fs.delete_file"):
            tool_ref = "fs.delete_file"
            tool_input = {"path": delete_path}

    if tool_ref is None:
        write_match = re.search(
            r"(?:写入|创建)\s*文件\s*[:：]?\s*([^\s]+)\s*(?:内容(?:为)?|内容是)\s*[:：]?\s*([\s\S]+)",
            message,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:write|create)\s+file\s+([^\s]+)\s+(?:content|with content)\s*[:：]?\s*([\s\S]+)",
            message,
            flags=re.IGNORECASE,
        )
        if write_match and _workspace_tool_available(context, "fs.write_file"):
            tool_ref = "fs.write_file"
            tool_input = {
                "path": write_match.group(1).strip().strip("\"'"),
                "content": write_match.group(2).strip(),
            }

    if tool_ref is None:
        search_match = re.search(
            r"(?:搜索|查找)\s*(?:文件)?\s*[:：]?\s*([^\s]+)",
            message,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:search|find)\s+(?:files?\s+)?([^\s]+)",
            message,
            flags=re.IGNORECASE,
        )
        if search_match and _workspace_tool_available(context, "fs.search_files"):
            tool_ref = "fs.search_files"
            tool_input = {"pattern": search_match.group(1).strip()}

    if tool_ref is None:
        return None

    output, side_effects, policy_decisions = _invoke_tool_if_available(
        context,
        tool_ref=tool_ref,
        tool_input=tool_input,
    )
    if output is None:
        reply = f"我尝试调用 `{tool_ref}`，但这次没有执行成功。"
        llm_context = {"mode": "mcp_tool", "tool_ref": tool_ref, "success": False}
        return reply, llm_context, _ToolUseBundle()

    bundle = _ToolUseBundle()
    _merge_tool_bundle(
        bundle,
        key=tool_ref,
        output=output,
        side_effects=side_effects,
        policy_decisions=policy_decisions,
    )
    reply = _workspace_tool_reply(tool_ref, output)
    llm_context = {"mode": "mcp_tool", "tool_ref": tool_ref, "success": True}
    return reply, llm_context, bundle


def _workspace_tool_reply(tool_ref: str, output: dict[str, object]) -> str:
    if tool_ref == "fs.list_dir":
        items = output.get("items") or []
        if not isinstance(items, list) or not items:
            return "工作目录目前是空的。"
        lines = ["我已经列出当前目录内容："]
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            kind = "目录" if item.get("kind") == "directory" else "文件"
            lines.append(f"- {kind}：{item.get('path')}")
        return "\n".join(lines)
    if tool_ref == "fs.read_file":
        return f"我已经读取文件 `{output.get('path', '')}`，内容如下：\n{output.get('content', '')}"
    if tool_ref == "fs.write_file":
        return f"我已经写入文件 `{output.get('path', '')}`。"
    if tool_ref == "fs.make_dir":
        return f"我已经创建目录 `{output.get('path', '')}`。"
    if tool_ref == "fs.search_files":
        matches = output.get("matches") or []
        if not isinstance(matches, list) or not matches:
            return "没有找到匹配的文件。"
        lines = ["我找到这些匹配文件："]
        for item in matches[:20]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('path')}")
        return "\n".join(lines)
    if tool_ref == "fs.delete_file":
        return f"我已经删除文件 `{output.get('path', '')}`。"
    return "我已经执行了工作目录相关操作。"


def _maybe_handle_generic_tool_request(
    context: ExecutionContext,
    payload: dict[str, object],
) -> tuple[str, dict[str, object], _ToolUseBundle] | None:
    message = _chat_message(payload).strip()
    matched = re.match(r"^/tool\s+([a-zA-Z0-9._:-]+)(?:\s+([\s\S]+))?$", message)
    if not matched:
        return None
    tool_ref = matched.group(1).strip()
    if not _tool_allowed(context, tool_ref):
        return (
            f"当前 agent 没有被分发工具 `{tool_ref}`。",
            {"mode": "manual_tool", "tool_ref": tool_ref, "success": False},
            _ToolUseBundle(),
        )
    raw_args = (matched.group(2) or "").strip()
    tool_input: dict[str, object] = {}
    if raw_args:
        try:
            parsed = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            return (
                f"工具参数不是合法 JSON：{exc}",
                {"mode": "manual_tool", "tool_ref": tool_ref, "success": False},
                _ToolUseBundle(),
            )
        if not isinstance(parsed, dict):
            return (
                "工具参数必须是 JSON object。",
                {"mode": "manual_tool", "tool_ref": tool_ref, "success": False},
                _ToolUseBundle(),
            )
        tool_input = parsed
    output, side_effects, policy_decisions = _invoke_tool_if_available(
        context,
        tool_ref=tool_ref,
        tool_input=tool_input,
    )
    bundle = _ToolUseBundle()
    if output is not None:
        _merge_tool_bundle(
            bundle,
            key=tool_ref,
            output=output,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        return (
            f"工具 `{tool_ref}` 已执行。\n{json.dumps(output, ensure_ascii=False, indent=2)}",
            {"mode": "manual_tool", "tool_ref": tool_ref, "success": True},
            bundle,
        )
    return (
        f"工具 `{tool_ref}` 执行失败。",
        {"mode": "manual_tool", "tool_ref": tool_ref, "success": False},
        bundle,
    )


def _maybe_invoke_llm_json(
    context: ExecutionContext,
    *,
    system_prompt: str,
    user_payload: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object]]:
    services = context.services
    if services is None or services.llm_invoker is None:
        return None, {
            "mode": "failed",
            "reason": "missing_llm_invoker",
            "error_code": "MISSING_LLM_INVOKER",
        }

    request = LLMRequest(
        request_id=f"{context.run_record.run_id}:{context.node_spec.node_id}",
        profile_ref=_llm_profile_ref(context),
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=json.dumps(user_payload, ensure_ascii=False),
            )
        ],
        system_prompt=system_prompt,
        response_format=LLMResponseFormatKind.JSON_OBJECT,
        metadata={
            "agent_ref": context.agent_binding.agent_ref if context.agent_binding else None,
            "node_id": context.node_spec.node_id,
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
    if result.output_json is not None:
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


def _require_llm_output(
    *,
    llm_output: dict[str, object] | None,
    llm_context: dict[str, object],
    required_keys: list[str],
) -> tuple[dict[str, object] | None, str | None, str | None]:
    if llm_output is None:
        return (
            None,
            str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
            str(llm_context.get("error_message", "LLM output is missing")),
        )
    missing_keys = [key for key in required_keys if key not in llm_output]
    if missing_keys:
        return (
            None,
            "LLM_OUTPUT_INCOMPLETE",
            f"LLM output is missing required keys: {', '.join(missing_keys)}",
        )
    return llm_output, None, None


def _merge_planner_output(
    fallback_output: dict[str, object],
    llm_output: dict[str, object] | None,
) -> dict[str, object]:
    if llm_output is None:
        return fallback_output
    merged = deepcopy(fallback_output)
    for key in (
        "goal",
        "focus_areas",
        "prerequisites",
        "milestones",
        "unit_sequence",
        "remediation_needed",
    ):
        value = llm_output.get(key)
        if value is not None:
            merged[key] = deepcopy(value)
    return merged


def _merge_coach_output(
    fallback_output: dict[str, object],
    llm_output: dict[str, object] | None,
) -> dict[str, object]:
    if llm_output is None:
        return fallback_output
    merged = deepcopy(fallback_output)
    for key in ("explanation", "encouragement", "next_steps", "tone"):
        value = llm_output.get(key)
        if value is not None:
            merged[key] = deepcopy(value)
    return merged


def _merge_profiler_output(
    fallback_output: dict[str, object],
    llm_output: dict[str, object] | None,
) -> dict[str, object]:
    if llm_output is None:
        return fallback_output
    merged = deepcopy(fallback_output)
    for key in (
        "learner_id",
        "goal",
        "current_level",
        "preferences",
        "weaknesses",
        "recent_signals",
        "focus_areas",
        "common_misconceptions",
        "summary",
    ):
        value = llm_output.get(key)
        if value is not None:
            merged[key] = deepcopy(value)
    return merged


def _merge_exercise_output(
    fallback_output: dict[str, object],
    llm_output: dict[str, object] | None,
) -> dict[str, object]:
    if llm_output is None:
        return fallback_output
    merged = deepcopy(fallback_output)
    for key in ("target_skill", "template_type", "questions", "hints", "answer_schema"):
        value = llm_output.get(key)
        if value is not None:
            merged[key] = deepcopy(value)
    return merged


def _merge_review_output(
    fallback_output: dict[str, object],
    llm_output: dict[str, object] | None,
) -> dict[str, object]:
    if llm_output is None:
        return fallback_output
    merged = deepcopy(fallback_output)
    for key in (
        "target_skill",
        "mastery_signal",
        "normalized_response",
        "rubric_criteria",
        "error_analysis",
        "remediation_recommendation",
    ):
        value = llm_output.get(key)
        if value is not None:
            merged[key] = deepcopy(value)
    return merged


class LearnerProfilerImplementation:
    implementation_ref = "education.learner_profiler"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        payload = _copy_input(context)
        if _should_use_conversation_mode(
            context,
            payload,
            signal_keys=[
                "learner_id",
                "goal",
                "current_level",
                "preferences",
                "weak_topics",
                "recent_signals",
            ],
        ):
            reply, llm_context = _maybe_invoke_llm_text(
                context,
                system_prompt=_build_chat_system_prompt(
                    context,
                    role_summary=(
                        "You are Learner Profiler, an education specialist who builds grounded learner profiles from evidence."
                    ),
                ),
                user_message=_chat_message(payload),
                payload=payload,
            )
            if reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
                    error_message=str(llm_context.get("error_message", "LLM output is missing")),
                    metadata={"llm_context": llm_context},
                )
            return _conversation_result(context, reply=reply, llm_context=llm_context)
        learner_id = str(payload.get("learner_id", "unknown"))
        goal = str(payload.get("goal", "general improvement"))
        preferences = [str(item) for item in _as_list(payload.get("preferences"))]
        weak_topics = [str(item) for item in _as_list(payload.get("weak_topics"))]
        recent_signals = [str(item) for item in _as_list(payload.get("recent_signals"))]
        tool_bundle = _ToolUseBundle()
        curriculum_lookup, side_effects, policy_decisions = _invoke_tool_if_available(
            context,
            tool_ref=EDUCATION_TOOL_REFS["curriculum_lookup"],
            tool_input={
                "target_skill": weak_topics[0] if weak_topics else goal,
                "goal": goal,
                "current_level": payload.get("current_level", "unknown"),
            },
        )
        _merge_tool_bundle(
            tool_bundle,
            key="curriculum_lookup",
            output=curriculum_lookup,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        reference_focus = []
        reference_misconceptions = []
        if curriculum_lookup is not None:
            reference_focus = [str(item) for item in _as_list(curriculum_lookup.get("focus_areas"))]
            reference_misconceptions = [
                str(item) for item in _as_list(curriculum_lookup.get("common_misconceptions"))
            ]

        required_keys = [
            "learner_id",
            "goal",
            "current_level",
            "preferences",
            "weaknesses",
            "recent_signals",
            "focus_areas",
            "common_misconceptions",
            "summary",
        ]
        llm_output, llm_context = _maybe_invoke_llm_json(
            context,
            system_prompt=_build_agent_system_prompt(context, output_keys=required_keys),
            user_payload={
                "learner_id": learner_id,
                "goal": goal,
                "current_level": payload.get("current_level", "unknown"),
                "preferences": preferences,
                "weak_topics": weak_topics,
                "recent_signals": recent_signals,
                "reference_focus": reference_focus,
                "reference_misconceptions": reference_misconceptions,
            },
        )
        output, error_code, error_message = _require_llm_output(
            llm_output=llm_output,
            llm_context=llm_context,
            required_keys=required_keys,
        )
        if output is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                side_effects=tool_bundle.side_effects,
                policy_decisions=tool_bundle.policy_decisions,
                metadata={"llm_context": llm_context},
            )
        output = deepcopy(output)
        output["llm_context"] = llm_context
        output["recommended_memory_scope"] = _primary_memory_scope(context)
        if tool_bundle.outputs:
            output["tool_context"] = tool_bundle.outputs
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=output,
            side_effects=tool_bundle.side_effects,
            policy_decisions=tool_bundle.policy_decisions,
        )


class CurriculumPlannerImplementation:
    implementation_ref = "education.curriculum_planner"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        payload = _copy_input(context)
        if _should_use_conversation_mode(
            context,
            payload,
            signal_keys=["goal", "current_level", "weaknesses", "focus_area", "target_objective"],
        ):
            reply, llm_context = _maybe_invoke_llm_text(
                context,
                system_prompt=_build_chat_system_prompt(
                    context,
                    role_summary=(
                        "You are Curriculum Planner, an education specialist who turns learner evidence into concrete learning plans."
                    ),
                ),
                user_message=_chat_message(payload),
                payload=payload,
            )
            if reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
                    error_message=str(llm_context.get("error_message", "LLM output is missing")),
                    metadata={"llm_context": llm_context},
                )
            return _conversation_result(context, reply=reply, llm_context=llm_context)
        goal = str(payload.get("goal", payload.get("target_objective", "target mastery")))
        weaknesses = [str(item) for item in _as_list(payload.get("weaknesses"))]
        tool_bundle = _ToolUseBundle()
        curriculum_lookup, side_effects, policy_decisions = _invoke_tool_if_available(
            context,
            tool_ref=EDUCATION_TOOL_REFS["curriculum_lookup"],
            tool_input={
                "target_skill": weaknesses[0] if weaknesses else goal,
                "goal": goal,
                "current_level": payload.get("current_level", "unknown"),
            },
        )
        _merge_tool_bundle(
            tool_bundle,
            key="curriculum_lookup",
            output=curriculum_lookup,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        reference_focus = (
            [str(item) for item in _as_list(curriculum_lookup.get("focus_areas"))]
            if curriculum_lookup is not None
            else []
        )
        reference_prerequisites = (
            [str(item) for item in _as_list(curriculum_lookup.get("prerequisites"))]
            if curriculum_lookup is not None
            else []
        )
        reference_objectives = (
            [str(item) for item in _as_list(curriculum_lookup.get("example_objectives"))]
            if curriculum_lookup is not None
            else []
        )
        focus_areas = weaknesses or reference_focus or [str(payload.get("focus_area", "foundations"))]

        required_keys = [
            "goal",
            "focus_areas",
            "prerequisites",
            "milestones",
            "unit_sequence",
            "remediation_needed",
        ]
        llm_output, llm_context = _maybe_invoke_llm_json(
            context,
            system_prompt=_build_agent_system_prompt(context, output_keys=required_keys),
            user_payload={
                "goal": goal,
                "current_level": payload.get("current_level", "unknown"),
                "weaknesses": weaknesses,
                "reference_focus": reference_focus,
                "reference_prerequisites": reference_prerequisites,
                "reference_objectives": reference_objectives,
            },
        )
        output, error_code, error_message = _require_llm_output(
            llm_output=llm_output,
            llm_context=llm_context,
            required_keys=required_keys,
        )
        if output is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                side_effects=tool_bundle.side_effects,
                policy_decisions=tool_bundle.policy_decisions,
                metadata={"llm_context": llm_context},
            )
        output = deepcopy(output)
        output["llm_context"] = llm_context
        output["recommended_memory_scope"] = _primary_memory_scope(context)
        if tool_bundle.outputs:
            output["tool_context"] = tool_bundle.outputs
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=output,
            side_effects=tool_bundle.side_effects,
            policy_decisions=tool_bundle.policy_decisions,
        )


class ExerciseDesignerImplementation:
    implementation_ref = "education.exercise_designer"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        payload = _copy_input(context)
        if _should_use_conversation_mode(
            context,
            payload,
            signal_keys=["target_skill", "goal", "current_level", "mastery_signal"],
        ):
            reply, llm_context = _maybe_invoke_llm_text(
                context,
                system_prompt=_build_chat_system_prompt(
                    context,
                    role_summary=(
                        "You are Exercise Designer, an education specialist who creates practice tasks and instructional exercises."
                    ),
                ),
                user_message=_chat_message(payload),
                payload=payload,
            )
            if reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
                    error_message=str(llm_context.get("error_message", "LLM output is missing")),
                    metadata={"llm_context": llm_context},
                )
            return _conversation_result(context, reply=reply, llm_context=llm_context)
        target_skill = str(payload.get("target_skill", payload.get("goal", "core skill")))
        level = str(payload.get("current_level", "intermediate"))
        tool_bundle = _ToolUseBundle()
        template_lookup, side_effects, policy_decisions = _invoke_tool_if_available(
            context,
            tool_ref=EDUCATION_TOOL_REFS["exercise_template_lookup"],
            tool_input={
                "target_skill": target_skill,
                "current_level": level,
                "mastery_signal": payload.get("mastery_signal", payload.get("mastery_signal")),
            },
        )
        _merge_tool_bundle(
            tool_bundle,
            key="exercise_template_lookup",
            output=template_lookup,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        question_stems = (
            [str(item) for item in _as_list(template_lookup.get("question_stems"))]
            if template_lookup is not None
            else []
        )
        hint_styles = (
            [str(item) for item in _as_list(template_lookup.get("hint_styles"))]
            if template_lookup is not None
            else []
        )
        template_type = (
            str(template_lookup.get("template_type", "generic-practice"))
            if template_lookup is not None
            else "generic-practice"
        )
        required_keys = [
            "target_skill",
            "template_type",
            "questions",
            "hints",
            "answer_schema",
        ]
        llm_output, llm_context = _maybe_invoke_llm_json(
            context,
            system_prompt=_build_agent_system_prompt(context, output_keys=required_keys),
            user_payload={
                "target_skill": target_skill,
                "current_level": level,
                "template_type": template_type,
                "question_stems": question_stems,
                "hint_styles": hint_styles,
            },
        )
        output, error_code, error_message = _require_llm_output(
            llm_output=llm_output,
            llm_context=llm_context,
            required_keys=required_keys,
        )
        if output is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                side_effects=tool_bundle.side_effects,
                policy_decisions=tool_bundle.policy_decisions,
                metadata={"llm_context": llm_context},
            )
        output = deepcopy(output)
        output["llm_context"] = llm_context
        if tool_bundle.outputs:
            output["tool_context"] = tool_bundle.outputs
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=output,
            side_effects=tool_bundle.side_effects,
            policy_decisions=tool_bundle.policy_decisions,
        )


class ReviewerGraderImplementation:
    implementation_ref = "education.reviewer_grader"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        payload = _copy_input(context)
        if _should_use_conversation_mode(
            context,
            payload,
            signal_keys=["score", "target_skill", "learner_response", "exercise_type"],
        ):
            reply, llm_context = _maybe_invoke_llm_text(
                context,
                system_prompt=_build_chat_system_prompt(
                    context,
                    role_summary=(
                        "You are Reviewer Grader, an education specialist who evaluates learner work and explains mastery signals."
                    ),
                ),
                user_message=_chat_message(payload),
                payload=payload,
            )
            if reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
                    error_message=str(llm_context.get("error_message", "LLM output is missing")),
                    metadata={"llm_context": llm_context},
                )
            return _conversation_result(context, reply=reply, llm_context=llm_context)
        score = float(payload.get("score", 0.0))
        target_skill = str(payload.get("target_skill", "core skill"))
        tool_bundle = _ToolUseBundle()
        normalized_answer, side_effects, policy_decisions = _invoke_tool_if_available(
            context,
            tool_ref=EDUCATION_TOOL_REFS["answer_normalizer"],
            tool_input={
                "learner_response": payload.get("learner_response", ""),
                "target_skill": target_skill,
            },
        )
        _merge_tool_bundle(
            tool_bundle,
            key="answer_normalizer",
            output=normalized_answer,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        rubric_lookup, side_effects, policy_decisions = _invoke_tool_if_available(
            context,
            tool_ref=EDUCATION_TOOL_REFS["rubric_lookup"],
            tool_input={
                "target_skill": target_skill,
                "exercise_type": payload.get("exercise_type", "free_response"),
            },
        )
        _merge_tool_bundle(
            tool_bundle,
            key="rubric_lookup",
            output=rubric_lookup,
            side_effects=side_effects,
            policy_decisions=policy_decisions,
        )
        required_keys = [
            "target_skill",
            "mastery_signal",
            "normalized_response",
            "rubric_criteria",
            "error_analysis",
            "remediation_recommendation",
        ]
        llm_output, llm_context = _maybe_invoke_llm_json(
            context,
            system_prompt=_build_agent_system_prompt(context, output_keys=required_keys),
            user_payload={
                "target_skill": target_skill,
                "score": score,
                "normalized_response": (
                    normalized_answer.get("normalized_response")
                    if normalized_answer is not None
                    else None
                ),
                "rubric_criteria": (
                    [str(item) for item in _as_list(rubric_lookup.get("criteria"))]
                    if rubric_lookup is not None
                    else []
                ),
                "exercise_type": payload.get("exercise_type", "free_response"),
                "learner_response": payload.get("learner_response", ""),
            },
        )
        output, error_code, error_message = _require_llm_output(
            llm_output=llm_output,
            llm_context=llm_context,
            required_keys=required_keys,
        )
        if output is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                side_effects=tool_bundle.side_effects,
                policy_decisions=tool_bundle.policy_decisions,
                metadata={"llm_context": llm_context},
            )
        output = deepcopy(output)
        output["llm_context"] = llm_context
        output["recommended_memory_scope"] = _primary_memory_scope(context)
        if tool_bundle.outputs:
            output["tool_context"] = tool_bundle.outputs
        return NodeExecutionResult(
            status=NodeStatus.SUCCEEDED,
            output=output,
            side_effects=tool_bundle.side_effects,
            policy_decisions=tool_bundle.policy_decisions,
        )


class TutorCoachImplementation:
    implementation_ref = "education.tutor_coach"

    def can_handle(self, binding) -> bool:
        return binding.implementation_ref == self.implementation_ref

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult:
        payload = _copy_input(context)
        if _should_use_conversation_mode(
            context,
            payload,
            signal_keys=["goal", "mastery_signal", "remediation_recommendation", "next_step", "focus_areas"],
        ):
            reply, llm_context = _maybe_invoke_llm_text(
                context,
                system_prompt=_build_chat_system_prompt(
                    context,
                    role_summary=(
                        "You are Tutor Coach, an education specialist who explains learning next steps in a warm and concrete way."
                    ),
                ),
                user_message=_chat_message(payload),
                payload=payload,
            )
            if reply is None:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code=str(llm_context.get("error_code", "LLM_OUTPUT_MISSING")),
                    error_message=str(llm_context.get("error_message", "LLM output is missing")),
                    metadata={"llm_context": llm_context},
                )
            return _conversation_result(context, reply=reply, llm_context=llm_context)
        goal = str(payload.get("goal", "your learning goal"))
        mastery_signal = str(payload.get("mastery_signal", "developing"))
        next_step = str(
            payload.get(
                "remediation_recommendation",
                payload.get("next_step", "continue with the next guided exercise"),
            )
        )
        required_keys = ["explanation", "encouragement", "next_steps", "tone"]
        llm_output, llm_context = _maybe_invoke_llm_json(
            context,
            system_prompt=_build_agent_system_prompt(context, output_keys=required_keys),
            user_payload={
                "goal": goal,
                "mastery_signal": mastery_signal,
                "next_step": next_step,
                "error_analysis": payload.get("error_analysis"),
                "focus_areas": payload.get("focus_areas"),
            },
        )
        output, error_code, error_message = _require_llm_output(
            llm_output=llm_output,
            llm_context=llm_context,
            required_keys=required_keys,
        )
        if output is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                metadata={"llm_context": llm_context},
            )
        output = deepcopy(output)
        output["llm_context"] = llm_context
        return NodeExecutionResult(status=NodeStatus.SUCCEEDED, output=output)


_EDUCATION_AGENT_IMPLEMENTATION_TYPES = [
    LearnerProfilerImplementation,
    CurriculumPlannerImplementation,
    ExerciseDesignerImplementation,
    ReviewerGraderImplementation,
    TutorCoachImplementation,
]


def get_education_agent_implementations() -> list[AgentImplementation]:
    return [implementation_type() for implementation_type in _EDUCATION_AGENT_IMPLEMENTATION_TYPES]
