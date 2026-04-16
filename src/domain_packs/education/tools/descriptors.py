from __future__ import annotations

from copy import deepcopy

from core.state.models import SideEffectKind
from core.tools import ToolApprovalMode, ToolDescriptor, ToolTransportKind

from .constants import EDUCATION_TOOL_REFS


_EDUCATION_TOOL_DESCRIPTORS = [
    ToolDescriptor(
        tool_ref=EDUCATION_TOOL_REFS["curriculum_lookup"],
        name="Education Curriculum Lookup",
        description=(
            "Look up curriculum guidance, prerequisite knowledge, common "
            "misconceptions, and target objectives for an education skill."
        ),
        transport_kind=ToolTransportKind.LOCAL_FUNCTION,
        input_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "goal": {"type": "string"},
                "current_level": {"type": "string"},
            },
            "required": ["target_skill"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "prerequisites": {"type": "array"},
                "focus_areas": {"type": "array"},
                "common_misconceptions": {"type": "array"},
            },
        },
        side_effect_kind=SideEffectKind.READ_ONLY,
        approval_mode=ToolApprovalMode.NONE,
        provider_ref="education.local_reference",
        operation_ref="curriculum_lookup",
        timeout_ms=2_000,
        is_idempotent=True,
        tags=["education", "curriculum", "lookup", "reference"],
        metadata={"domain": "education", "tool_kind": "reference_lookup"},
    ),
    ToolDescriptor(
        tool_ref=EDUCATION_TOOL_REFS["exercise_template_lookup"],
        name="Education Exercise Template Lookup",
        description=(
            "Retrieve exercise templates, prompt patterns, and scaffold "
            "suggestions for a target skill and learner level."
        ),
        transport_kind=ToolTransportKind.LOCAL_FUNCTION,
        input_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "current_level": {"type": "string"},
                "mastery_signal": {"type": "string"},
            },
            "required": ["target_skill"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "template_type": {"type": "string"},
                "question_stems": {"type": "array"},
                "hint_styles": {"type": "array"},
            },
        },
        side_effect_kind=SideEffectKind.READ_ONLY,
        approval_mode=ToolApprovalMode.NONE,
        provider_ref="education.local_reference",
        operation_ref="exercise_template_lookup",
        timeout_ms=2_000,
        is_idempotent=True,
        tags=["education", "exercise", "template", "reference"],
        metadata={"domain": "education", "tool_kind": "reference_lookup"},
    ),
    ToolDescriptor(
        tool_ref=EDUCATION_TOOL_REFS["rubric_lookup"],
        name="Education Rubric Lookup",
        description=(
            "Return rubric criteria and mastery band guidance for a target "
            "skill so review agents can grade consistently."
        ),
        transport_kind=ToolTransportKind.LOCAL_FUNCTION,
        input_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "exercise_type": {"type": "string"},
            },
            "required": ["target_skill"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "target_skill": {"type": "string"},
                "criteria": {"type": "array"},
                "mastery_bands": {"type": "object"},
            },
        },
        side_effect_kind=SideEffectKind.READ_ONLY,
        approval_mode=ToolApprovalMode.NONE,
        provider_ref="education.local_reference",
        operation_ref="rubric_lookup",
        timeout_ms=2_000,
        is_idempotent=True,
        tags=["education", "rubric", "grading", "reference"],
        metadata={"domain": "education", "tool_kind": "reference_lookup"},
    ),
    ToolDescriptor(
        tool_ref=EDUCATION_TOOL_REFS["answer_normalizer"],
        name="Education Answer Normalizer",
        description=(
            "Normalize learner responses into a cleaner structured form for "
            "review, rubric matching, and misconception analysis."
        ),
        transport_kind=ToolTransportKind.LOCAL_FUNCTION,
        input_schema={
            "type": "object",
            "properties": {
                "learner_response": {"type": "string"},
                "target_skill": {"type": "string"},
            },
            "required": ["learner_response"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "normalized_response": {"type": "string"},
                "keywords": {"type": "array"},
                "token_count": {"type": "integer"},
            },
        },
        side_effect_kind=SideEffectKind.READ_ONLY,
        approval_mode=ToolApprovalMode.NONE,
        provider_ref="education.local_reference",
        operation_ref="answer_normalizer",
        timeout_ms=1_000,
        is_idempotent=True,
        tags=["education", "normalization", "review", "utility"],
        metadata={"domain": "education", "tool_kind": "normalization"},
    ),
]


def get_education_tool_descriptors() -> list[ToolDescriptor]:
    return [deepcopy(descriptor) for descriptor in _EDUCATION_TOOL_DESCRIPTORS]
