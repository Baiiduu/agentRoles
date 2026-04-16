from __future__ import annotations

from copy import deepcopy

from core.agents import AgentDescriptor
from domain_packs.education.tools.constants import EDUCATION_TOOL_REFS

EDUCATION_MEMORY_SCOPES = {
    "domain": "domain:education",
    "learner": "learner:{learner_id}",
    "session": "session:{thread_id}",
    "course": "course:{course_id}",
    "plan": "plan:{thread_id}",
}


_EDUCATION_AGENT_DESCRIPTORS = [
    AgentDescriptor(
        agent_id="learner_profiler",
        name="Learner Profiler",
        version="0.1.0",
        role="profiler",
        description=(
            "Organizes learner profile, goals, weaknesses, preferences, and "
            "recent performance into a structured learner model."
        ),
        executor_ref="agent.domain",
        implementation_ref="education.learner_profiler",
        domain="education",
        tags=["education", "profile", "diagnostic"],
        tool_refs=[
            EDUCATION_TOOL_REFS["curriculum_lookup"],
            EDUCATION_TOOL_REFS["answer_normalizer"],
        ],
        memory_scopes=[
            EDUCATION_MEMORY_SCOPES["domain"],
            EDUCATION_MEMORY_SCOPES["learner"],
            EDUCATION_MEMORY_SCOPES["session"],
        ],
        policy_profiles=["edu_default"],
        capabilities=[
            "learner_profiling",
            "weakness_detection",
            "preference_summarization",
        ],
        input_contract={
            "type": "learner_profile_seed",
            "required_fields": ["learner_id", "goal"],
        },
        output_contract={
            "type": "learner_profile_summary",
            "produces": ["current_level", "weaknesses", "preferences", "goals"],
        },
        metadata={
            "stage": "diagnostic",
            "writes_memory": True,
            "primary_scope": EDUCATION_MEMORY_SCOPES["learner"],
            "llm_profile_ref": "education.learner_profiler.default",
        },
    ),
    AgentDescriptor(
        agent_id="curriculum_planner",
        name="Curriculum Planner",
        version="0.1.0",
        role="planner",
        description=(
            "Transforms learner profile and target objectives into a staged "
            "study plan with sequencing and remediation guidance."
        ),
        executor_ref="agent.domain",
        implementation_ref="education.curriculum_planner",
        domain="education",
        tags=["education", "planning", "curriculum"],
        tool_refs=[
            EDUCATION_TOOL_REFS["curriculum_lookup"],
        ],
        memory_scopes=[
            EDUCATION_MEMORY_SCOPES["domain"],
            EDUCATION_MEMORY_SCOPES["learner"],
            EDUCATION_MEMORY_SCOPES["course"],
            EDUCATION_MEMORY_SCOPES["plan"],
        ],
        policy_profiles=["edu_default"],
        capabilities=[
            "curriculum_planning",
            "goal_decomposition",
            "remediation_planning",
        ],
        input_contract={
            "type": "planning_request",
            "required_fields": ["learner_summary", "target_objective"],
        },
        output_contract={
            "type": "study_plan",
            "produces": ["milestones", "unit_sequence", "focus_areas"],
        },
        metadata={
            "stage": "planning",
            "writes_memory": True,
            "primary_scope": EDUCATION_MEMORY_SCOPES["plan"],
            "llm_profile_ref": "education.curriculum_planner.default",
        },
    ),
    AgentDescriptor(
        agent_id="exercise_designer",
        name="Exercise Designer",
        version="0.1.0",
        role="designer",
        description=(
            "Generates level-appropriate exercises, examples, and hints from "
            "the current study plan and target concepts."
        ),
        executor_ref="agent.domain",
        implementation_ref="education.exercise_designer",
        domain="education",
        tags=["education", "practice", "content-generation"],
        tool_refs=[
            EDUCATION_TOOL_REFS["exercise_template_lookup"],
            EDUCATION_TOOL_REFS["curriculum_lookup"],
        ],
        memory_scopes=[
            EDUCATION_MEMORY_SCOPES["learner"],
            EDUCATION_MEMORY_SCOPES["plan"],
            EDUCATION_MEMORY_SCOPES["course"],
        ],
        policy_profiles=["edu_default"],
        capabilities=[
            "exercise_generation",
            "difficulty_adjustment",
            "hint_generation",
        ],
        input_contract={
            "type": "exercise_request",
            "required_fields": ["study_plan", "target_skill"],
        },
        output_contract={
            "type": "exercise_set",
            "produces": ["questions", "hints", "answer_schema"],
        },
        metadata={
            "stage": "practice_generation",
            "writes_memory": False,
            "primary_scope": EDUCATION_MEMORY_SCOPES["plan"],
            "llm_profile_ref": "education.exercise_designer.default",
        },
    ),
    AgentDescriptor(
        agent_id="reviewer_grader",
        name="Reviewer Grader",
        version="0.1.0",
        role="reviewer",
        description=(
            "Reviews learner answers, grades mastery, identifies errors, and "
            "recommends remediation or progression."
        ),
        executor_ref="agent.domain",
        implementation_ref="education.reviewer_grader",
        domain="education",
        tags=["education", "review", "grading"],
        tool_refs=[
            EDUCATION_TOOL_REFS["rubric_lookup"],
            EDUCATION_TOOL_REFS["answer_normalizer"],
        ],
        memory_scopes=[
            EDUCATION_MEMORY_SCOPES["learner"],
            EDUCATION_MEMORY_SCOPES["session"],
            EDUCATION_MEMORY_SCOPES["plan"],
        ],
        policy_profiles=["edu_default"],
        capabilities=[
            "answer_review",
            "mastery_estimation",
            "misconception_detection",
        ],
        input_contract={
            "type": "review_request",
            "required_fields": ["exercise_set", "learner_response"],
        },
        output_contract={
            "type": "review_summary",
            "produces": [
                "mastery_signal",
                "error_analysis",
                "remediation_recommendation",
            ],
        },
        metadata={
            "stage": "review",
            "writes_memory": True,
            "primary_scope": EDUCATION_MEMORY_SCOPES["learner"],
            "llm_profile_ref": "education.reviewer_grader.default",
        },
    ),
    AgentDescriptor(
        agent_id="tutor_coach",
        name="Tutor Coach",
        version="0.1.0",
        role="coach",
        description=(
            "Turns plan and review artifacts into learner-facing explanation, "
            "encouragement, and next-step guidance."
        ),
        executor_ref="agent.domain",
        implementation_ref="education.tutor_coach",
        domain="education",
        tags=["education", "tutoring", "communication"],
        tool_refs=[],
        memory_scopes=[
            EDUCATION_MEMORY_SCOPES["learner"],
            EDUCATION_MEMORY_SCOPES["session"],
            EDUCATION_MEMORY_SCOPES["plan"],
        ],
        policy_profiles=["edu_default"],
        capabilities=[
            "learner_explanation",
            "coaching_feedback",
            "next_step_guidance",
        ],
        input_contract={
            "type": "coaching_request",
            "required_fields": ["learner_summary", "review_summary"],
        },
        output_contract={
            "type": "learner_guidance",
            "produces": ["explanation", "encouragement", "next_steps"],
        },
        metadata={
            "stage": "coaching",
            "writes_memory": False,
            "primary_scope": EDUCATION_MEMORY_SCOPES["session"],
            "llm_profile_ref": "education.tutor_coach.default",
        },
    ),
]


def get_education_agent_descriptors() -> list[AgentDescriptor]:
    return [deepcopy(descriptor) for descriptor in _EDUCATION_AGENT_DESCRIPTORS]
