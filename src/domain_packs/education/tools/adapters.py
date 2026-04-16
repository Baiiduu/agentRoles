from __future__ import annotations

from copy import deepcopy
from re import findall

from core.contracts import ExecutionContext, ToolInvocationResult
from core.tools import FunctionToolAdapter

from .constants import EDUCATION_TOOL_REFS


_CURRICULUM_REFERENCE = {
    "fraction addition": {
        "prerequisites": ["equivalent fractions", "common denominators"],
        "focus_areas": ["finding a common denominator", "adding numerators correctly"],
        "common_misconceptions": [
            "adding denominators directly",
            "treating fractions like whole numbers",
        ],
        "example_objectives": [
            "identify a common denominator",
            "solve same-denominator addition accurately",
        ],
    },
    "fractions mastery": {
        "prerequisites": ["part-whole understanding", "equivalent fractions"],
        "focus_areas": ["fraction comparison", "fraction addition", "word problem transfer"],
        "common_misconceptions": [
            "larger denominator means larger fraction",
            "denominators should always be added",
        ],
        "example_objectives": [
            "compare fractions with visual reasoning",
            "add fractions with shared or converted denominators",
        ],
    },
}

_EXERCISE_TEMPLATE_REFERENCE = {
    "fraction addition": {
        "core": {
            "template_type": "worked-example-plus-practice",
            "question_stems": [
                "Add the fractions after finding a common denominator.",
                "Explain why the denominator stays the same after conversion.",
            ],
            "hint_styles": ["show-one-step", "use-visual-model"],
        },
        "remediation": {
            "template_type": "scaffolded-remediation",
            "question_stems": [
                "Rewrite each fraction with a common denominator before adding.",
                "Circle the denominator that both fractions can share.",
            ],
            "hint_styles": ["guided-denominator-choice", "worked-example"],
        },
    }
}

_RUBRIC_REFERENCE = {
    "fraction addition": {
        "criteria": [
            "chooses a valid common denominator",
            "converts numerators correctly",
            "adds numerators without changing the denominator incorrectly",
        ],
        "mastery_bands": {
            "strong": "All rubric criteria are consistently satisfied.",
            "partial": "Some criteria are satisfied, but errors still appear.",
            "weak": "Core fraction-addition reasoning is still unstable.",
        },
    },
    "fractions mastery": {
        "criteria": [
            "uses fraction vocabulary accurately",
            "reasons about equivalence and comparison correctly",
            "transfers knowledge into word problems",
        ],
        "mastery_bands": {
            "strong": "The learner demonstrates connected fraction understanding.",
            "partial": "The learner can solve routine tasks but lacks consistency.",
            "weak": "The learner still holds foundational misconceptions.",
        },
    },
}


def build_education_function_tool_adapter() -> FunctionToolAdapter:
    adapter = FunctionToolAdapter()
    register_education_tool_handlers(adapter)
    return adapter


def register_education_tool_handlers(adapter: FunctionToolAdapter) -> None:
    adapter.register_handler(
        EDUCATION_TOOL_REFS["curriculum_lookup"],
        _curriculum_lookup_handler,
    )
    adapter.register_handler(
        EDUCATION_TOOL_REFS["exercise_template_lookup"],
        _exercise_template_lookup_handler,
    )
    adapter.register_handler(
        EDUCATION_TOOL_REFS["rubric_lookup"],
        _rubric_lookup_handler,
    )
    adapter.register_handler(
        EDUCATION_TOOL_REFS["answer_normalizer"],
        _answer_normalizer_handler,
    )


def _curriculum_lookup_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_skill = _string_value(tool_input, "target_skill") or _string_value(tool_input, "goal")
    if not target_skill or not target_skill.strip():
        return ToolInvocationResult(
            success=False,
            error_code="MISSING_TARGET_SKILL",
            error_message="curriculum_lookup requires target_skill or goal",
        )
    entry = _lookup_reference(_CURRICULUM_REFERENCE, target_skill)
    if entry is None:
        return ToolInvocationResult(
            success=False,
            error_code="CURRICULUM_REFERENCE_NOT_FOUND",
            error_message=f"no curriculum reference found for '{target_skill}'",
        )
    return ToolInvocationResult(
        success=True,
        output={
            "target_skill": target_skill,
            "goal": _string_value(tool_input, "goal"),
            "current_level": _string_value(tool_input, "current_level"),
            "prerequisites": deepcopy(entry["prerequisites"]),
            "focus_areas": deepcopy(entry["focus_areas"]),
            "common_misconceptions": deepcopy(entry["common_misconceptions"]),
            "example_objectives": deepcopy(entry["example_objectives"]),
            "resolved_from": "education.local_reference",
            "node_id": context.node_state.node_id,
        },
    )


def _exercise_template_lookup_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_skill = _string_value(tool_input, "target_skill")
    if not target_skill or not target_skill.strip():
        return ToolInvocationResult(
            success=False,
            error_code="MISSING_TARGET_SKILL",
            error_message="exercise_template_lookup requires target_skill",
        )
    mastery_signal = _string_value(tool_input, "mastery_signal")
    templates = _lookup_reference(_EXERCISE_TEMPLATE_REFERENCE, target_skill)
    if templates is None:
        return ToolInvocationResult(
            success=False,
            error_code="EXERCISE_TEMPLATE_NOT_FOUND",
            error_message=f"no exercise template found for '{target_skill}'",
        )
    template_key = "remediation" if mastery_signal == "weak" else "core"
    template = templates.get(template_key, templates.get("core", {}))
    return ToolInvocationResult(
        success=True,
        output={
            "target_skill": target_skill,
            "current_level": _string_value(tool_input, "current_level"),
            "mastery_signal": mastery_signal,
            "template_type": template.get("template_type", "generic-practice"),
            "question_stems": deepcopy(template.get("question_stems", [])),
            "hint_styles": deepcopy(template.get("hint_styles", [])),
            "resolved_from": "education.local_reference",
            "node_id": context.node_state.node_id,
        },
    )


def _rubric_lookup_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_skill = _string_value(tool_input, "target_skill")
    if not target_skill or not target_skill.strip():
        return ToolInvocationResult(
            success=False,
            error_code="MISSING_TARGET_SKILL",
            error_message="rubric_lookup requires target_skill",
        )
    rubric = _lookup_reference(_RUBRIC_REFERENCE, target_skill)
    if rubric is None:
        return ToolInvocationResult(
            success=False,
            error_code="RUBRIC_REFERENCE_NOT_FOUND",
            error_message=f"no rubric reference found for '{target_skill}'",
        )
    return ToolInvocationResult(
        success=True,
        output={
            "target_skill": target_skill,
            "exercise_type": _string_value(tool_input, "exercise_type"),
            "criteria": deepcopy(rubric["criteria"]),
            "mastery_bands": deepcopy(rubric["mastery_bands"]),
            "resolved_from": "education.local_reference",
            "node_id": context.node_state.node_id,
        },
    )


def _answer_normalizer_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    learner_response = _string_value(tool_input, "learner_response")
    normalized = " ".join((learner_response or "").strip().lower().split())
    keywords = sorted(set(findall(r"[a-z0-9]+", normalized)))
    return ToolInvocationResult(
        success=True,
        output={
            "target_skill": _string_value(tool_input, "target_skill"),
            "normalized_response": normalized,
            "keywords": keywords,
            "token_count": len(keywords),
            "resolved_from": "education.local_reference",
            "node_id": context.node_state.node_id,
        },
    )


def _lookup_reference(
    reference_map: dict[str, dict[str, object]],
    key: str | None,
) -> dict[str, object] | None:
    if key is not None and key in reference_map:
        return reference_map[key]
    if key is not None:
        lowered = key.strip().lower()
        if lowered in reference_map:
            return reference_map[lowered]
    return None


def _string_value(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
