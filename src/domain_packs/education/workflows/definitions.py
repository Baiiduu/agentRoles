from __future__ import annotations

from copy import deepcopy

from core.state.models import NodeType
from core.workflow.workflow_models import (
    EdgeCondition,
    EdgeConditionType,
    EdgeSpec,
    InputSelector,
    InputSource,
    InputSourceType,
    MergeStrategyKind,
    NodeSpec,
    OutputBinding,
    TerminalCondition,
    TerminalConditionType,
    WorkflowDefinition,
)
from domain_packs.education.tools.constants import EDUCATION_TOOL_REFS


DIAGNOSTIC_PLAN_WORKFLOW_ID = "education.diagnostic_plan"
PRACTICE_REVIEW_WORKFLOW_ID = "education.practice_review"
REMEDIATION_LOOP_WORKFLOW_ID = "education.remediation_loop"


def build_diagnostic_plan_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=DIAGNOSTIC_PLAN_WORKFLOW_ID,
        name="Diagnostic Plan Workflow",
        version="0.1.0",
        entry_node_id="profile_learner",
        node_specs=[
            NodeSpec(
                node_id="profile_learner",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="learner_profiler",
                input_selector=InputSelector(
                    sources=[
                        InputSource(
                            InputSourceType.THREAD_STATE,
                            "thread_context",
                            path="global_context",
                        )
                    ],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.learner_profile"),
                metadata={"domain": "education", "stage": "diagnostic"},
            ),
            NodeSpec(
                node_id="lookup_curriculum_context",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "profile_learner")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.curriculum_reference"),
                config={"tool_ref": EDUCATION_TOOL_REFS["curriculum_lookup"]},
                metadata={"domain": "education", "stage": "curriculum_reference"},
            ),
            NodeSpec(
                node_id="plan_curriculum",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="curriculum_planner",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "profile_learner"),
                        InputSource(InputSourceType.ARTIFACT, "lookup_curriculum_context"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.study_plan"),
                metadata={"domain": "education", "stage": "planning"},
            ),
            NodeSpec(
                node_id="coach_learner",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="tutor_coach",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "profile_learner"),
                        InputSource(InputSourceType.ARTIFACT, "plan_curriculum"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.learner_guidance"),
                metadata={"domain": "education", "stage": "coaching"},
            ),
        ],
        edge_specs=[
            EdgeSpec(
                edge_id="e_profile_to_curriculum_lookup",
                from_node_id="profile_learner",
                to_node_id="lookup_curriculum_context",
            ),
            EdgeSpec(
                edge_id="e_profile_to_plan",
                from_node_id="profile_learner",
                to_node_id="plan_curriculum",
            ),
            EdgeSpec(
                edge_id="e_curriculum_lookup_to_plan",
                from_node_id="lookup_curriculum_context",
                to_node_id="plan_curriculum",
            ),
            EdgeSpec(
                edge_id="e_plan_to_coach",
                from_node_id="plan_curriculum",
                to_node_id="coach_learner",
            ),
        ],
        metadata={
            "domain": "education",
            "workflow_kind": "diagnostic_plan",
            "entry_expectation": "thread_state.global_context must include learner seed data",
        },
    )


def build_practice_review_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=PRACTICE_REVIEW_WORKFLOW_ID,
        name="Practice Review Workflow",
        version="0.1.0",
        entry_node_id="design_exercises",
        node_specs=[
            NodeSpec(
                node_id="design_exercises",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="exercise_designer",
                input_selector=InputSelector(
                    sources=[
                        InputSource(
                            InputSourceType.THREAD_STATE,
                            "thread_context",
                            path="global_context",
                        )
                    ],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.exercise_set"),
                metadata={"domain": "education", "stage": "practice_generation"},
            ),
            NodeSpec(
                node_id="lookup_exercise_template",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "design_exercises")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.exercise_template_reference"),
                config={"tool_ref": EDUCATION_TOOL_REFS["exercise_template_lookup"]},
                metadata={"domain": "education", "stage": "exercise_template_lookup"},
            ),
            NodeSpec(
                node_id="capture_submission",
                node_type=NodeType.NOOP,
                executor_ref="builtin.noop",
                input_selector=InputSelector(
                    sources=[
                        InputSource(
                            InputSourceType.THREAD_STATE,
                            "thread_context",
                            path="global_context",
                        )
                    ],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.learner_submission"),
                metadata={"domain": "education", "stage": "submission_capture"},
            ),
            NodeSpec(
                node_id="normalize_submission",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "capture_submission")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.normalized_submission"),
                config={"tool_ref": EDUCATION_TOOL_REFS["answer_normalizer"]},
                metadata={"domain": "education", "stage": "submission_normalization"},
            ),
            NodeSpec(
                node_id="lookup_review_rubric",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "design_exercises")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.rubric_reference"),
                config={"tool_ref": EDUCATION_TOOL_REFS["rubric_lookup"]},
                metadata={"domain": "education", "stage": "rubric_lookup"},
            ),
            NodeSpec(
                node_id="review_submission",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="reviewer_grader",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "design_exercises"),
                        InputSource(InputSourceType.ARTIFACT, "lookup_exercise_template"),
                        InputSource(InputSourceType.ARTIFACT, "capture_submission"),
                        InputSource(InputSourceType.ARTIFACT, "normalize_submission"),
                        InputSource(InputSourceType.ARTIFACT, "lookup_review_rubric"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.review_summary"),
                metadata={"domain": "education", "stage": "review"},
            ),
            NodeSpec(
                node_id="coach_feedback",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="tutor_coach",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "review_submission"),
                        InputSource(InputSourceType.ARTIFACT, "capture_submission"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.practice_feedback"),
                metadata={"domain": "education", "stage": "coaching"},
            ),
        ],
        edge_specs=[
            EdgeSpec(
                edge_id="e_exercises_to_submission",
                from_node_id="design_exercises",
                to_node_id="capture_submission",
            ),
            EdgeSpec(
                edge_id="e_exercises_to_template_lookup",
                from_node_id="design_exercises",
                to_node_id="lookup_exercise_template",
            ),
            EdgeSpec(
                edge_id="e_exercises_to_review",
                from_node_id="design_exercises",
                to_node_id="review_submission",
            ),
            EdgeSpec(
                edge_id="e_submission_to_normalize",
                from_node_id="capture_submission",
                to_node_id="normalize_submission",
            ),
            EdgeSpec(
                edge_id="e_exercises_to_rubric_lookup",
                from_node_id="design_exercises",
                to_node_id="lookup_review_rubric",
            ),
            EdgeSpec(
                edge_id="e_submission_to_review",
                from_node_id="capture_submission",
                to_node_id="review_submission",
            ),
            EdgeSpec(
                edge_id="e_normalized_submission_to_review",
                from_node_id="normalize_submission",
                to_node_id="review_submission",
            ),
            EdgeSpec(
                edge_id="e_rubric_lookup_to_review",
                from_node_id="lookup_review_rubric",
                to_node_id="review_submission",
            ),
            EdgeSpec(
                edge_id="e_template_lookup_to_review",
                from_node_id="lookup_exercise_template",
                to_node_id="review_submission",
            ),
            EdgeSpec(
                edge_id="e_review_to_coach",
                from_node_id="review_submission",
                to_node_id="coach_feedback",
            ),
            EdgeSpec(
                edge_id="e_submission_to_coach",
                from_node_id="capture_submission",
                to_node_id="coach_feedback",
            ),
        ],
        metadata={
            "domain": "education",
            "workflow_kind": "practice_review",
            "entry_expectation": (
                "thread_state.global_context must include target_skill, "
                "goal, learner response summary, and score"
            ),
        },
    )


def build_remediation_loop_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=REMEDIATION_LOOP_WORKFLOW_ID,
        name="Remediation Loop Workflow",
        version="0.1.0",
        entry_node_id="design_initial_exercises",
        node_specs=[
            NodeSpec(
                node_id="design_initial_exercises",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="exercise_designer",
                input_selector=InputSelector(
                    sources=[
                        InputSource(
                            InputSourceType.THREAD_STATE,
                            "thread_context",
                            path="global_context",
                        )
                    ],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.initial_exercise_set"),
                metadata={"domain": "education", "stage": "initial_practice_design"},
            ),
            NodeSpec(
                node_id="capture_attempt",
                node_type=NodeType.NOOP,
                executor_ref="builtin.noop",
                input_selector=InputSelector(
                    sources=[
                        InputSource(
                            InputSourceType.THREAD_STATE,
                            "thread_context",
                            path="global_context",
                        )
                    ],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.learner_attempt"),
                metadata={"domain": "education", "stage": "attempt_capture"},
            ),
            NodeSpec(
                node_id="normalize_attempt",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "capture_attempt")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.normalized_attempt"),
                config={"tool_ref": EDUCATION_TOOL_REFS["answer_normalizer"]},
                metadata={"domain": "education", "stage": "attempt_normalization"},
            ),
            NodeSpec(
                node_id="lookup_attempt_rubric",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "design_initial_exercises")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.attempt_rubric_reference"),
                config={"tool_ref": EDUCATION_TOOL_REFS["rubric_lookup"]},
                metadata={"domain": "education", "stage": "attempt_rubric_lookup"},
            ),
            NodeSpec(
                node_id="review_attempt",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="reviewer_grader",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "design_initial_exercises"),
                        InputSource(InputSourceType.ARTIFACT, "capture_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "normalize_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "lookup_attempt_rubric"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.review_summary"),
                metadata={"domain": "education", "stage": "attempt_review"},
            ),
            NodeSpec(
                node_id="decide_remediation_path",
                node_type=NodeType.CONDITION,
                executor_ref="builtin.condition",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "review_attempt")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.remediation_decision"),
                config={
                    "operand_path": "mastery_signal",
                    "operator": "eq",
                    "value": "weak",
                    "branches": {
                        "true": "design_remediation_exercises",
                        "false": "coach_progress_path",
                    },
                },
                metadata={"domain": "education", "stage": "remediation_decision"},
            ),
            NodeSpec(
                node_id="lookup_remediation_template",
                node_type=NodeType.TOOL,
                executor_ref="tool.executor",
                input_selector=InputSelector(
                    sources=[InputSource(InputSourceType.ARTIFACT, "review_attempt")],
                    merge_strategy=MergeStrategyKind.REPLACE,
                ),
                output_binding=OutputBinding(artifact_type="education.remediation_template_reference"),
                config={"tool_ref": EDUCATION_TOOL_REFS["exercise_template_lookup"]},
                metadata={"domain": "education", "stage": "remediation_template_lookup"},
            ),
            NodeSpec(
                node_id="design_remediation_exercises",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="exercise_designer",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "review_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "capture_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "lookup_remediation_template"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.remediation_exercise_set"),
                metadata={"domain": "education", "stage": "remediation_design"},
            ),
            NodeSpec(
                node_id="coach_remediation_path",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="tutor_coach",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "review_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "capture_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "design_remediation_exercises"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.remediation_guidance"),
                metadata={"domain": "education", "stage": "remediation_coaching"},
            ),
            NodeSpec(
                node_id="coach_progress_path",
                node_type=NodeType.AGENT,
                executor_ref="agent.domain",
                agent_ref="tutor_coach",
                input_selector=InputSelector(
                    sources=[
                        InputSource(InputSourceType.ARTIFACT, "review_attempt"),
                        InputSource(InputSourceType.ARTIFACT, "capture_attempt"),
                    ],
                    merge_strategy=MergeStrategyKind.DEEP_MERGE,
                ),
                output_binding=OutputBinding(artifact_type="education.progress_guidance"),
                metadata={"domain": "education", "stage": "progress_coaching"},
            ),
        ],
        edge_specs=[
            EdgeSpec(
                edge_id="e_initial_exercises_to_attempt",
                from_node_id="design_initial_exercises",
                to_node_id="capture_attempt",
            ),
            EdgeSpec(
                edge_id="e_initial_exercises_to_rubric_lookup",
                from_node_id="design_initial_exercises",
                to_node_id="lookup_attempt_rubric",
            ),
            EdgeSpec(
                edge_id="e_initial_exercises_to_review",
                from_node_id="design_initial_exercises",
                to_node_id="review_attempt",
            ),
            EdgeSpec(
                edge_id="e_attempt_to_review",
                from_node_id="capture_attempt",
                to_node_id="review_attempt",
            ),
            EdgeSpec(
                edge_id="e_attempt_to_normalize",
                from_node_id="capture_attempt",
                to_node_id="normalize_attempt",
            ),
            EdgeSpec(
                edge_id="e_normalized_attempt_to_review",
                from_node_id="normalize_attempt",
                to_node_id="review_attempt",
            ),
            EdgeSpec(
                edge_id="e_attempt_rubric_to_review",
                from_node_id="lookup_attempt_rubric",
                to_node_id="review_attempt",
            ),
            EdgeSpec(
                edge_id="e_review_to_decision",
                from_node_id="review_attempt",
                to_node_id="decide_remediation_path",
            ),
            EdgeSpec(
                edge_id="e_decision_to_remediation_template",
                from_node_id="decide_remediation_path",
                to_node_id="lookup_remediation_template",
                condition=EdgeCondition(
                    condition_type=EdgeConditionType.RESULT_FIELD_EQUALS,
                    operand_path="matched",
                    expected_value=True,
                ),
            ),
            EdgeSpec(
                edge_id="e_decision_to_remediation_design",
                from_node_id="lookup_remediation_template",
                to_node_id="design_remediation_exercises",
            ),
            EdgeSpec(
                edge_id="e_decision_to_progress_coach",
                from_node_id="decide_remediation_path",
                to_node_id="coach_progress_path",
                condition=EdgeCondition(
                    condition_type=EdgeConditionType.RESULT_FIELD_EQUALS,
                    operand_path="matched",
                    expected_value=False,
                ),
            ),
            EdgeSpec(
                edge_id="e_remediation_design_to_coach",
                from_node_id="design_remediation_exercises",
                to_node_id="coach_remediation_path",
            ),
        ],
        terminal_conditions=[
            TerminalCondition(
                condition_type=TerminalConditionType.EXPLICIT_NODE_COMPLETED,
                node_id="coach_remediation_path",
            ),
            TerminalCondition(
                condition_type=TerminalConditionType.EXPLICIT_NODE_COMPLETED,
                node_id="coach_progress_path",
            ),
        ],
        metadata={
            "domain": "education",
            "workflow_kind": "remediation_loop",
            "entry_expectation": (
                "thread_state.global_context must include target_skill, goal, "
                "learner response summary, score, and review context"
            ),
        },
    )


def get_education_workflow_definitions() -> list[WorkflowDefinition]:
    return [
        deepcopy(build_diagnostic_plan_workflow()),
        deepcopy(build_practice_review_workflow()),
        deepcopy(build_remediation_loop_workflow()),
    ]
