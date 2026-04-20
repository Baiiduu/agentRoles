from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re


_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_MAX_ACTIVE_SKILL_BODIES = 3


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = str(item).strip()
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _normalize_text(value: object) -> str:
    return " ".join(str(value).lower().split()) if isinstance(value, str) and value.strip() else ""


def _first_body_paragraph(body: str) -> str:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
    for paragraph in paragraphs:
        if paragraph.startswith("#"):
            continue
        return " ".join(line.strip() for line in paragraph.splitlines())
    return ""


def _parse_skill_prompt(prompt_file: str) -> dict[str, str]:
    candidate = Path(prompt_file)
    if not prompt_file or not candidate.exists() or not candidate.is_file():
        return {"body": "", "summary": ""}
    text = candidate.read_text(encoding="utf-8")
    body = text
    match = _FRONTMATTER_PATTERN.match(text)
    if match:
        body = text[match.end() :]
    body = body.strip()
    return {
        "body": body,
        "summary": _first_body_paragraph(body),
    }


def build_runtime_skill_packages(
    *,
    registered_skills: list[dict[str, object]],
    skill_bindings: list[dict[str, object]],
) -> list[dict[str, object]]:
    skill_index = {
        str(item.get("skill_name", "")).strip(): deepcopy(item)
        for item in registered_skills
        if isinstance(item, dict) and str(item.get("skill_name", "")).strip()
    }
    packages: list[dict[str, object]] = []
    for binding in skill_bindings:
        if not isinstance(binding, dict) or not binding.get("enabled", True):
            continue
        skill_name = str(binding.get("skill_name", "")).strip()
        if not skill_name or skill_name not in skill_index:
            continue
        skill = skill_index[skill_name]
        prompt = _parse_skill_prompt(str(skill.get("prompt_file", "")))
        packages.append(
            {
                "skill_name": skill_name,
                "name": str(skill.get("name", "")).strip() or skill_name,
                "description": str(skill.get("description", "")).strip(),
                "source_kind": str(skill.get("source_kind", "")).strip(),
                "source_path": str(skill.get("source_path", "")).strip(),
                "prompt_file": str(skill.get("prompt_file", "")).strip(),
                "metadata": deepcopy(dict(skill.get("metadata") or {})),
                "trigger_kinds": _unique(
                    [str(item) for item in (skill.get("trigger_kinds") or [])]
                    + [str(item) for item in (binding.get("trigger_kinds") or [])]
                ),
                "execution_mode": str(binding.get("execution_mode", "human_confirmed")).strip()
                or "human_confirmed",
                "scope": str(binding.get("scope", "session")).strip() or "session",
                "usage_notes": str(binding.get("usage_notes", "")).strip(),
                "prompt_available": bool(prompt["body"]),
                "prompt_summary": prompt["summary"],
                "prompt_body": prompt["body"],
            }
        )
    return sorted(packages, key=lambda item: str(item.get("skill_name", "")))


def _serialize_activation_text(selected_input: dict[str, object] | None) -> str:
    if not isinstance(selected_input, dict):
        return ""
    values: list[str] = []
    for key in ("message", "task_goal", "goal", "requested_skill", "requested_skills", "skill"):
        value = selected_input.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value if str(item).strip())
    return _normalize_text(" ".join(values))


def _matches_skill(package: dict[str, object], activation_text: str) -> tuple[bool, str]:
    if not activation_text:
        return False, ""
    skill_name = _normalize_text(package.get("skill_name"))
    if skill_name and skill_name in activation_text:
        return True, f"name match: {package.get('skill_name')}"
    display_name = _normalize_text(package.get("name"))
    if display_name and display_name in activation_text:
        return True, f"name match: {package.get('name')}"
    for trigger in package.get("trigger_kinds", []):
        normalized_trigger = _normalize_text(trigger)
        if normalized_trigger and normalized_trigger in activation_text:
            return True, f"trigger match: {trigger}"
    return False, ""


def resolve_active_skill_packages(
    runtime_resource_context: dict[str, object],
    selected_input: dict[str, object] | None = None,
) -> dict[str, list[dict[str, object]]]:
    packages = runtime_resource_context.get("skill_packages")
    if not isinstance(packages, list):
        return {"active": [], "inactive": []}
    activation_text = _serialize_activation_text(selected_input)
    active: list[dict[str, object]] = []
    inactive: list[dict[str, object]] = []
    for raw_package in packages:
        if not isinstance(raw_package, dict):
            continue
        package = deepcopy(raw_package)
        matched, reason = _matches_skill(package, activation_text)
        should_activate = matched
        if not should_activate and len(packages) == 1:
            should_activate = True
            reason = "only assigned skill for this agent"
        if (
            not should_activate
            and package.get("execution_mode") == "auto"
            and not package.get("trigger_kinds")
        ):
            should_activate = True
            reason = "auto mode without explicit triggers"
        if should_activate:
            package["activation_reason"] = reason or "assigned skill"
            active.append(package)
        else:
            inactive.append(package)
    return {"active": active, "inactive": inactive}


def build_skill_prompt_appendix(
    runtime_resource_context: dict[str, object],
    selected_input: dict[str, object] | None = None,
) -> str:
    packages = runtime_resource_context.get("skill_packages")
    if not isinstance(packages, list) or not packages:
        return ""

    resolved = resolve_active_skill_packages(runtime_resource_context, selected_input)
    active = resolved["active"]
    inactive = resolved["inactive"]
    lines = [
        "Skills for this session are managed by the central skills controller.",
        "Follow active skill instructions before generic heuristics when they are more specific.",
        "Execution modes: advisory = guidance only; human_confirmed = ask before irreversible or externally visible actions that rely on the skill; auto = you may apply the skill automatically when relevant.",
    ]

    if active:
        lines.append("Active skills for this request:")
        for package in active[:_MAX_ACTIVE_SKILL_BODIES]:
            lines.extend(_skill_prompt_block(package, include_body=True))
        if len(active) > _MAX_ACTIVE_SKILL_BODIES:
            omitted = ", ".join(
                str(item.get("skill_name", ""))
                for item in active[_MAX_ACTIVE_SKILL_BODIES:]
                if str(item.get("skill_name", "")).strip()
            )
            if omitted:
                lines.append(
                    "Additional active skills not expanded inline due to prompt budget: " + omitted
                )
    else:
        lines.append(
            "No skill was explicitly activated by the current request text. Use the available skill summaries below as optional guidance."
        )

    if inactive:
        lines.append("Assigned skills available as summaries:")
        for package in inactive:
            lines.extend(_skill_prompt_block(package, include_body=False))

    return "\n".join(line for line in lines if line.strip()).strip()


def _skill_prompt_block(package: dict[str, object], *, include_body: bool) -> list[str]:
    lines = [
        f"- {package.get('name', package.get('skill_name', 'skill'))} [{package.get('skill_name', '')}]",
        f"  mode={package.get('execution_mode', 'human_confirmed')}; scope={package.get('scope', 'session')}",
    ]
    description = str(package.get("description", "")).strip()
    if description:
        lines.append(f"  description: {description}")
    triggers = package.get("trigger_kinds")
    if isinstance(triggers, list) and triggers:
        lines.append("  triggers: " + ", ".join(str(item) for item in triggers))
    usage_notes = str(package.get("usage_notes", "")).strip()
    if usage_notes:
        lines.append(f"  manager notes: {usage_notes}")
    activation_reason = str(package.get("activation_reason", "")).strip()
    if activation_reason:
        lines.append(f"  activation reason: {activation_reason}")
    prompt_summary = str(package.get("prompt_summary", "")).strip()
    if prompt_summary:
        lines.append(f"  prompt summary: {prompt_summary}")
    if include_body:
        prompt_body = str(package.get("prompt_body", "")).strip()
        if prompt_body:
            lines.append("  skill instructions:")
            lines.extend(f"    {line}" for line in prompt_body.splitlines())
    return lines
