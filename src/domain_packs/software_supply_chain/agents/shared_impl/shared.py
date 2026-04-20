from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re

from core.contracts import ExecutionContext, MemoryResult
from application.runtime.skill_prompt_service import (
    build_skill_prompt_appendix,
    resolve_active_skill_packages,
)
from domain_packs.operations import OPERATION_TOOL_REFS


@dataclass
class _NormalizedSupplyChainInput:
    message: str
    llm_profile_ref: str | None
    system_prompt: str
    current_repo_url: str = ""
    saved_repo_urls: list[str] = field(default_factory=list)
    available_tool_refs: list[str] = field(default_factory=list)
    available_mcp_servers: list[dict[str, object]] = field(default_factory=list)
    available_mcp_tools: list[dict[str, object]] = field(default_factory=list)
    runtime_resource_context: dict[str, object] = field(default_factory=dict)
    workspace_enabled: bool = False
    memory_scopes: list[str] = field(default_factory=list)
    memory_context: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    task_memory: dict[str, object] = field(default_factory=dict)
    raw_selected_input: dict[str, object] = field(default_factory=dict)


@dataclass
class _ToolExecutionBundle:
    tool_output: dict[str, object] | None
    side_effects: list[object] = field(default_factory=list)
    policy_decisions: list[object] = field(default_factory=list)
    error_message: str | None = None


_PREFERRED_TOOL_ORDER = [
    OPERATION_TOOL_REFS["list_files"],
    OPERATION_TOOL_REFS["symbol_search"],
    OPERATION_TOOL_REFS["lookup_definition"],
    OPERATION_TOOL_REFS["find_references"],
    OPERATION_TOOL_REFS["symbol_outline"],
    OPERATION_TOOL_REFS["ripgrep_search"],
    OPERATION_TOOL_REFS["find_in_file"],
    OPERATION_TOOL_REFS["read_file_segment"],
    OPERATION_TOOL_REFS["read_file"],
    OPERATION_TOOL_REFS["preview_structured_edit"],
    OPERATION_TOOL_REFS["replace_in_file"],
    OPERATION_TOOL_REFS["insert_in_file"],
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
    OPERATION_TOOL_REFS["symbol_outline"],
    OPERATION_TOOL_REFS["symbol_search"],
    OPERATION_TOOL_REFS["lookup_definition"],
    OPERATION_TOOL_REFS["find_references"],
    OPERATION_TOOL_REFS["find_in_file"],
    OPERATION_TOOL_REFS["search_files"],
    OPERATION_TOOL_REFS["ripgrep_search"],
    OPERATION_TOOL_REFS["git_status"],
    OPERATION_TOOL_REFS["git_diff"],
}

_BROAD_EXPLORATION_TOOL_REFS = {
    OPERATION_TOOL_REFS["list_dir"],
    OPERATION_TOOL_REFS["list_files"],
    OPERATION_TOOL_REFS["search_files"],
    OPERATION_TOOL_REFS["ripgrep_search"],
}

_EDIT_TOOL_REFS = {
    OPERATION_TOOL_REFS["replace_in_file"],
    OPERATION_TOOL_REFS["insert_in_file"],
    OPERATION_TOOL_REFS["apply_patch"],
    OPERATION_TOOL_REFS["write_file"],
    OPERATION_TOOL_REFS["move_file"],
    OPERATION_TOOL_REFS["delete_file"],
}

_VALIDATION_TOOL_REFS = {
    OPERATION_TOOL_REFS["git_diff"],
    OPERATION_TOOL_REFS["git_status"],
    OPERATION_TOOL_REFS["shell_run"],
}


def _artifact_type(context: ExecutionContext) -> str:
    binding = context.agent_binding
    if binding is None:
        return "software_supply_chain.chat_output"
    output_contract = getattr(binding, "output_contract", None)
    if isinstance(output_contract, dict):
        value = output_contract.get("type")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "software_supply_chain.chat_output"


def _binding_domain(context: ExecutionContext) -> str:
    binding = context.agent_binding
    value = getattr(binding, "domain", None) if binding is not None else None
    return value.strip() if isinstance(value, str) and value.strip() else "software_supply_chain"


def _metadata_text(context: ExecutionContext, key: str) -> str:
    binding = context.agent_binding
    if binding is None:
        return ""
    value = binding.metadata.get(key)
    return value.strip() if isinstance(value, str) else ""


def _llm_profile_ref(context: ExecutionContext) -> str | None:
    value = _metadata_text(context, "llm_profile_ref")
    return value or None


def _build_system_prompt(context: ExecutionContext) -> str:
    parts = [_metadata_text(context, "system_prompt") or "You are a software supply chain assistant."]
    appendix = _metadata_text(context, "instruction_appendix")
    quality_bar = _metadata_text(context, "quality_bar")
    response_style = _metadata_text(context, "response_style")
    runtime_resource_context = _runtime_resource_context(context)
    if appendix:
        parts.append(appendix)
    if quality_bar:
        parts.append(f"Quality bar: {quality_bar}")
    if response_style:
        parts.append(f"Response style: {response_style}")
    repo_context = _extract_repository_context(deepcopy(dict(context.selected_input)))
    repo_lines: list[str] = []
    if repo_context["current_repo_url"]:
        repo_lines.append(
            "Active repository target: "
            + str(repo_context["current_repo_url"])
            + ". Treat this as the primary GitHub investigation context for the current turn."
        )
    if repo_context["saved_repo_urls"]:
        repo_lines.append(
            "Saved repository candidates: "
            + ", ".join(str(item) for item in repo_context["saved_repo_urls"][:5])
            + ". Use them only as supporting context when relevant."
        )
    if repo_lines:
        parts.append("\n".join(repo_lines))
    skill_appendix = build_skill_prompt_appendix(
        runtime_resource_context,
        deepcopy(dict(context.selected_input)),
    )
    if skill_appendix:
        parts.append(skill_appendix)
    parts.append("Reply naturally in Simplified Chinese unless the user asks for another language.")
    return "\n\n".join(parts)


def _runtime_resource_context(context: ExecutionContext) -> dict[str, object]:
    binding = context.agent_binding
    value = binding.metadata.get("runtime_resource_context") if binding is not None else None
    return deepcopy(value) if isinstance(value, dict) else {}


def _workspace_enabled(runtime_resource_context: dict[str, object]) -> bool:
    workspace = runtime_resource_context.get("workspace")
    return bool(isinstance(workspace, dict) and workspace.get("enabled"))


def _resolved_memory_scopes(context: ExecutionContext) -> list[str]:
    binding = context.agent_binding
    if binding is None:
        return []
    replacements = {
        "{thread_id}": context.thread_record.thread_id,
        "{run_id}": context.run_record.run_id,
        "{agent_id}": binding.resolved_agent_id,
    }
    scopes: list[str] = []
    for item in binding.memory_scopes:
        if not isinstance(item, str):
            continue
        scope = item.strip()
        if not scope:
            continue
        for token, value in replacements.items():
            scope = scope.replace(token, value)
        if scope and scope not in scopes:
            scopes.append(scope)
    return scopes


def _primary_memory_scope(context: ExecutionContext) -> str | None:
    scopes = _resolved_memory_scopes(context)
    return scopes[0] if scopes else None


def _serialize_memory_result(result: MemoryResult) -> dict[str, object]:
    return {
        "memory_id": result.memory_id,
        "scope": result.scope,
        "score": result.score,
        "payload": deepcopy(result.payload),
        "source_ref": result.source_ref,
        "metadata": deepcopy(result.metadata),
    }


def _changed_files_hints(raw_selected_input: dict[str, object]) -> list[str]:
    value = raw_selected_input.get("changed_files_hint")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]


def _normalize_repo_url(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _dedupe_repo_urls(values: list[object]) -> list[str]:
    urls: list[str] = []
    for value in values:
        normalized = _normalize_repo_url(value)
        if normalized and normalized not in urls:
            urls.append(normalized)
    return urls


def _extract_repository_context(raw_selected_input: dict[str, object]) -> dict[str, object]:
    context = raw_selected_input.get("software_supply_chain_context")
    context_map = context if isinstance(context, dict) else {}

    current_repo_url = ""
    for candidate in (
        context_map.get("current_repo_url"),
        raw_selected_input.get("current_repo_url"),
        raw_selected_input.get("github_repository"),
        raw_selected_input.get("repo_url"),
    ):
        current_repo_url = _normalize_repo_url(candidate)
        if current_repo_url:
            break

    saved_candidates: list[object] = []
    saved_values = context_map.get("saved_repo_urls")
    if isinstance(saved_values, list):
        saved_candidates.extend(saved_values)
    raw_saved_values = raw_selected_input.get("saved_repo_urls")
    if isinstance(raw_saved_values, list):
        saved_candidates.extend(raw_saved_values)
    if current_repo_url:
        saved_candidates.insert(0, current_repo_url)

    return {
        "current_repo_url": current_repo_url,
        "saved_repo_urls": _dedupe_repo_urls(saved_candidates),
    }


def _repository_context_payload(normalized_input: _NormalizedSupplyChainInput) -> dict[str, object]:
    return {
        "current_repo_url": normalized_input.current_repo_url or None,
        "saved_repo_urls": list(normalized_input.saved_repo_urls),
        "has_repository_target": bool(normalized_input.current_repo_url),
    }


def _memory_query(normalized_input: _NormalizedSupplyChainInput) -> str:
    parts = [normalized_input.message]
    task_goal = normalized_input.raw_selected_input.get("task_goal")
    if isinstance(task_goal, str) and task_goal.strip():
        parts.append(task_goal.strip())
    if normalized_input.current_repo_url:
        parts.append(normalized_input.current_repo_url)
    parts.extend(_changed_files_hints(normalized_input.raw_selected_input)[:3])
    return " ".join(part for part in parts if part).strip()


def _load_memory_context(
    context: ExecutionContext,
    *,
    normalized_input: _NormalizedSupplyChainInput,
    scopes: list[str],
) -> dict[str, list[dict[str, object]]]:
    services = context.services
    if services is None or services.memory_provider is None or not scopes:
        return {}
    query = _memory_query(normalized_input)
    memory_context: dict[str, list[dict[str, object]]] = {}
    for scope in scopes:
        try:
            results = services.memory_provider.retrieve(query=query, scope=scope, top_k=3, context=context)
        except Exception:
            continue
        serialized = [_serialize_memory_result(result) for result in results]
        if serialized:
            memory_context[scope] = serialized
    return memory_context


def _memory_scope_priority(scope: str) -> tuple[int, str]:
    if scope.startswith("session:"):
        return (0, scope)
    if scope.startswith("domain:"):
        return (1, scope)
    return (2, scope)


def _derive_task_memory(
    memory_context: dict[str, list[dict[str, object]]],
    raw_selected_input: dict[str, object],
    message: str,
    repository_context: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for scope in sorted(memory_context.keys(), key=_memory_scope_priority):
        for item in memory_context.get(scope, []):
            payload = item.get("payload")
            if not isinstance(payload, dict):
                continue
            task_memory = payload.get("task_memory")
            if not isinstance(task_memory, dict):
                continue
            for key, value in task_memory.items():
                if key not in merged and value not in (None, "", [], {}):
                    merged[key] = deepcopy(value)
    task_goal = raw_selected_input.get("task_goal")
    if isinstance(task_goal, str) and task_goal.strip():
        merged["objective"] = task_goal.strip()
    elif "objective" not in merged and message.strip():
        merged["objective"] = message.strip()
    acceptance = raw_selected_input.get("acceptance_criteria")
    if acceptance is not None and "acceptance_criteria" not in merged:
        merged["acceptance_criteria"] = deepcopy(acceptance)
    changed_files = _changed_files_hints(raw_selected_input)
    if changed_files:
        existing = merged.get("target_files")
        base = list(existing) if isinstance(existing, list) else []
        for item in changed_files:
            if item not in base:
                base.append(item)
        merged["target_files"] = base
    current_repo_url = _normalize_repo_url(repository_context.get("current_repo_url"))
    if current_repo_url:
        merged["current_repo_url"] = current_repo_url
    saved_repo_urls = repository_context.get("saved_repo_urls")
    if isinstance(saved_repo_urls, list) and saved_repo_urls:
        merged["saved_repo_urls"] = _dedupe_repo_urls(saved_repo_urls)
    return merged


def _normalize_input(context: ExecutionContext) -> _NormalizedSupplyChainInput:
    selected_input = deepcopy(dict(context.selected_input))
    message_value = selected_input.get("message")
    message = message_value.strip() if isinstance(message_value, str) else ""
    runtime_resource_context = _runtime_resource_context(context)
    mcp_servers = runtime_resource_context.get("mcp_server_catalog")
    mcp_tools = runtime_resource_context.get("mcp_tools")
    repository_context = _extract_repository_context(selected_input)
    normalized = _NormalizedSupplyChainInput(
        message=message,
        llm_profile_ref=_llm_profile_ref(context),
        system_prompt=_build_system_prompt(context),
        current_repo_url=str(repository_context["current_repo_url"]),
        saved_repo_urls=list(repository_context["saved_repo_urls"]),
        available_tool_refs=list(context.agent_binding.tool_refs) if context.agent_binding else [],
        available_mcp_servers=deepcopy(mcp_servers) if isinstance(mcp_servers, list) else [],
        available_mcp_tools=deepcopy(mcp_tools) if isinstance(mcp_tools, list) else [],
        runtime_resource_context=runtime_resource_context,
        workspace_enabled=_workspace_enabled(runtime_resource_context),
        raw_selected_input=selected_input,
    )
    normalized.memory_scopes = _resolved_memory_scopes(context)
    normalized.memory_context = _load_memory_context(
        context,
        normalized_input=normalized,
        scopes=normalized.memory_scopes,
    )
    normalized.task_memory = _derive_task_memory(
        normalized.memory_context,
        normalized.raw_selected_input,
        normalized.message,
        repository_context,
    )
    return normalized


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


def _serializable_selected_input(raw_selected_input: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in raw_selected_input.items():
        if str(key).startswith("_") or callable(value):
            continue
        result[str(key)] = deepcopy(value)
    return result


def _progress_callback(normalized_input: _NormalizedSupplyChainInput):
    callback = normalized_input.raw_selected_input.get("_progress_callback")
    return callback if callable(callback) else None


def _emit_progress(
    normalized_input: _NormalizedSupplyChainInput,
    *,
    kind: str,
    stage: str,
    current_phase: str,
    summary: str,
    current_activity: str | None = None,
    status: str = "running",
    tool_ref: str | None = None,
    detail: dict[str, object] | None = None,
) -> None:
    callback = _progress_callback(normalized_input)
    if callback is None:
        return
    payload: dict[str, object] = {
        "kind": kind,
        "stage": stage,
        "status": status,
        "current_phase": current_phase,
        "summary": summary,
        "current_activity": current_activity or summary,
    }
    if isinstance(tool_ref, str) and tool_ref.strip():
        payload["tool_ref"] = tool_ref
    if isinstance(detail, dict) and detail:
        payload["detail"] = deepcopy(detail)
    try:
        callback(payload)
    except Exception:
        return


def _extract_candidate_path(message: str) -> str | None:
    for token in re.findall(r"[\w./\\-]+\.\w+|[\w./\\-]+/", message):
        cleaned = token.strip(".,:;!?\'\"()[]{}")
        if "/" in cleaned or "\\" in cleaned or "." in cleaned:
            return cleaned.rstrip("/\\")
    return None


def _extract_search_pattern(message: str) -> str | None:
    quoted = re.findall(r"['\"]([^'\"]{2,120})['\"]", message)
    if quoted:
        return quoted[0].strip()
    match = re.search(r"(?:search|find|grep|搜索|查找)\s+([^\s]+)", message, re.IGNORECASE)
    if match:
        return match.group(1).strip(".,:;!?")
    return None


def _extract_symbol_candidate(message: str) -> str | None:
    quoted = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", message)
    if quoted:
        return quoted[0]
    match = re.search(
        r"(?:symbol|class|function|method|definition|reference|usage|定义|引用|调用)\s+([A-Za-z_][A-Za-z0-9_]*)",
        message,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def _extract_line_range(message: str) -> tuple[int | None, int | None]:
    pair = re.search(r"(\d+)\s*[-~到至]\s*(\d+)", message)
    if pair:
        return int(pair.group(1)), int(pair.group(2))
    single = re.search(r"(?:line|lines|第)\s*(\d+)", message, re.IGNORECASE)
    if single:
        value = int(single.group(1))
        return value, value
    return None, None


def _verification_mode(raw_selected_input: dict[str, object]) -> str:
    value = raw_selected_input.get("verification_mode")
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return "suggest"


def _recent_tool_calls(execution_trace: list[dict[str, object]]) -> list[dict[str, object]]:
    return [entry for entry in execution_trace if entry.get("kind") == "tool_call"]


def _has_tool_result_for_path(tool_context: dict[str, object], path: str) -> bool:
    for item in tool_context.values():
        if not isinstance(item, dict):
            continue
        output = item.get("tool_output")
        if isinstance(output, dict) and str(output.get("path", "")).strip() == path:
            return True
    return False


def _has_any_tool_result(tool_context: dict[str, object]) -> bool:
    return any(isinstance(item, dict) and item.get("tool_output") is not None for item in tool_context.values())


def _has_tool_call(execution_trace: list[dict[str, object]], tool_refs: set[str]) -> bool:
    return any(
        entry.get("kind") == "tool_call" and str(entry.get("tool_ref", "")).strip() in tool_refs
        for entry in execution_trace
    )


def _has_edit_activity(execution_trace: list[dict[str, object]]) -> bool:
    return _has_tool_call(execution_trace, _EDIT_TOOL_REFS)


def _has_validation_activity(execution_trace: list[dict[str, object]]) -> bool:
    return _has_tool_call(execution_trace, _VALIDATION_TOOL_REFS)


def _is_edit_request(lowered: str) -> bool:
    return any(
        keyword in lowered
        for keyword in ["patch", "edit", "modify", "change", "update", "fix", "replace", "insert", "修改", "修复", "更新", "替换", "插入"]
    )


def _is_git_status_request(lowered: str) -> bool:
    return "git status" in lowered or ("git" in lowered and "status" in lowered)


def _is_git_diff_request(lowered: str) -> bool:
    return "git diff" in lowered or "diff" in lowered


def _resource_summary(normalized_input: _NormalizedSupplyChainInput) -> dict[str, object]:
    runtime_resources = normalized_input.runtime_resource_context
    return {
        "mcp_server_count": len(normalized_input.available_mcp_servers),
        "mcp_tool_count": len(normalized_input.available_mcp_tools),
        "skill_count": len(runtime_resources.get("skills", [])) if isinstance(runtime_resources.get("skills"), list) else 0,
        "workspace_enabled": normalized_input.workspace_enabled,
        "memory_scope_count": len(normalized_input.memory_scopes),
        "memory_item_count": sum(len(items) for items in normalized_input.memory_context.values()),
        "has_repository_target": bool(normalized_input.current_repo_url),
        "saved_repository_count": len(normalized_input.saved_repo_urls),
    }


def _is_skill_inventory_request(message: str) -> bool:
    lowered = " ".join(message.lower().split())
    if not lowered:
        return False
    direct_patterns = (
        "what skills",
        "which skills",
        "available skills",
        "assigned skills",
        "你有哪些skill",
        "你有哪些skills",
        "你现在有哪些skill",
        "你现在有哪些skills",
        "你能看到哪些skill",
        "你能看到哪些skills",
        "你看到了哪些skill",
        "你看到了哪些skills",
        "当前skills",
        "分配给你",
    )
    if any(pattern in lowered for pattern in direct_patterns):
        return True
    has_skill_word = any(token in lowered for token in ("skill", "skills", "技能"))
    has_inventory_word = any(
        token in lowered
        for token in ("哪些", "有什么", "有哪", "能看到", "看到", "available", "assigned", "current")
    )
    return has_skill_word and has_inventory_word


def _skill_inventory_reply(normalized_input: _NormalizedSupplyChainInput) -> str:
    runtime_resources = normalized_input.runtime_resource_context
    packages = runtime_resources.get("skill_packages")
    if not isinstance(packages, list) or not packages:
        return "当前没有给这个 agent 分配任何 skill。"

    resolved = resolve_active_skill_packages(
        runtime_resources,
        normalized_input.raw_selected_input,
    )
    active_names = {
        str(item.get("skill_name", "")).strip()
        for item in resolved["active"]
        if isinstance(item, dict) and str(item.get("skill_name", "")).strip()
    }
    lines = ["当前分配给我的 skills 如下："]
    for package in packages:
        if not isinstance(package, dict):
            continue
        skill_name = str(package.get("skill_name", "")).strip()
        if not skill_name:
            continue
        display_name = str(package.get("name", "")).strip() or skill_name
        mode = str(package.get("execution_mode", "human_confirmed")).strip() or "human_confirmed"
        status = "active" if skill_name in active_names else "assigned"
        line = f"- {display_name} [{skill_name}]"
        description = str(package.get("description", "")).strip()
        extras: list[str] = [f"status={status}", f"mode={mode}"]
        if description:
            extras.append(f"description={description}")
        triggers = package.get("trigger_kinds")
        if isinstance(triggers, list) and triggers:
            extras.append("triggers=" + ", ".join(str(item) for item in triggers if str(item).strip()))
        lines.append(line)
        lines.append("  " + "; ".join(extras))
    if active_names:
        lines.append(
            "当前这次请求已激活的 skills："
            + ", ".join(
                str(item.get("name", item.get("skill_name", ""))).strip()
                for item in resolved["active"]
                if isinstance(item, dict)
            )
        )
    else:
        lines.append("当前这次请求还没有命中显式激活的 skill，所以它们目前是已分配但未激活状态。")
    return "\n".join(lines)
