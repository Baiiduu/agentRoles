from __future__ import annotations

from copy import deepcopy

from core.evaluation import (
    CompletedNodesScorer,
    EvaluationCase,
    EvaluationScorer,
    EvaluationSuite,
    EventPresenceScorer,
    RunStatusScorer,
)


EDUCATION_EVAL_CASE_DIAGNOSTIC_PLAN = "education.eval.diagnostic_plan"
EDUCATION_EVAL_CASE_PRACTICE_REVIEW = "education.eval.practice_review"
EDUCATION_EVAL_CASE_REMEDIATION_WEAK = "education.eval.remediation_weak"
EDUCATION_EVAL_CASE_REMEDIATION_STRONG = "education.eval.remediation_strong"

EDUCATION_EVAL_SUITE_CORE_PATHS = "education.eval_suite.core_paths"
EDUCATION_EVAL_SUITE_REMEDIATION = "education.eval_suite.remediation_paths"
EDUCATION_EVAL_SUITE_SMOKE = "education.eval_suite.smoke"


def build_diagnostic_plan_eval_case() -> EvaluationCase:
    return EvaluationCase(
        case_id=EDUCATION_EVAL_CASE_DIAGNOSTIC_PLAN,
        workflow_id="education.diagnostic_plan",
        goal="validate diagnostic planning flow for a beginner fractions learner",
        title="Education Diagnostic Planning Baseline",
        trigger="evaluation.education",
        trigger_payload={
            "global_context": {
                "learner_id": "eval-learner-001",
                "goal": "fractions mastery",
                "current_level": "beginner",
                "weak_topics": ["fractions", "word problems"],
                "preferences": ["worked examples"],
            }
        },
        metadata={
            "domain": "education",
            "scenario": "diagnostic_plan",
            "required_node_ids": [
                "profile_learner",
                "lookup_curriculum_context",
                "plan_curriculum",
                "coach_learner",
            ],
            "required_event_types": ["run.started", "node.succeeded", "run.completed"],
        },
    )


def build_practice_review_eval_case() -> EvaluationCase:
    return EvaluationCase(
        case_id=EDUCATION_EVAL_CASE_PRACTICE_REVIEW,
        workflow_id="education.practice_review",
        goal="validate practice review with weak performance and coaching feedback",
        title="Education Practice Review Weak Performance",
        trigger="evaluation.education",
        trigger_payload={
            "global_context": {
                "learner_id": "eval-learner-002",
                "goal": "fractions mastery",
                "target_skill": "fraction addition",
                "current_level": "beginner",
                "learner_response": "I added the denominators too.",
                "score": 0.45,
                "error_analysis": "The learner still confuses denominator handling.",
            }
        },
        metadata={
            "domain": "education",
            "scenario": "practice_review",
            "required_node_ids": [
                "design_exercises",
                "lookup_exercise_template",
                "capture_submission",
                "normalize_submission",
                "lookup_review_rubric",
                "review_submission",
                "coach_feedback",
            ],
            "required_event_types": ["run.started", "node.succeeded", "run.completed"],
        },
    )


def build_remediation_weak_eval_case() -> EvaluationCase:
    return EvaluationCase(
        case_id=EDUCATION_EVAL_CASE_REMEDIATION_WEAK,
        workflow_id="education.remediation_loop",
        goal="validate remediation branch after weak learner performance",
        title="Education Remediation Branch Baseline",
        trigger="evaluation.education",
        trigger_payload={
            "global_context": {
                "learner_id": "eval-learner-003",
                "goal": "fractions mastery",
                "target_skill": "fraction addition",
                "current_level": "beginner",
                "learner_response": "I added the denominators too.",
                "score": 0.2,
                "error_analysis": "The learner is still applying whole-number addition rules.",
            }
        },
        metadata={
            "domain": "education",
            "scenario": "remediation_weak",
            "required_node_ids": [
                "design_initial_exercises",
                "capture_attempt",
                "normalize_attempt",
                "lookup_attempt_rubric",
                "review_attempt",
                "decide_remediation_path",
                "lookup_remediation_template",
                "design_remediation_exercises",
                "coach_remediation_path",
            ],
            "required_event_types": ["run.started", "node.succeeded", "run.completed"],
        },
    )


def build_remediation_strong_eval_case() -> EvaluationCase:
    return EvaluationCase(
        case_id=EDUCATION_EVAL_CASE_REMEDIATION_STRONG,
        workflow_id="education.remediation_loop",
        goal="validate non-remediation branch after strong learner performance",
        title="Education Remediation Exit Baseline",
        trigger="evaluation.education",
        trigger_payload={
            "global_context": {
                "learner_id": "eval-learner-004",
                "goal": "fractions mastery",
                "target_skill": "fraction addition",
                "current_level": "intermediate",
                "learner_response": "I found a common denominator and added the numerators.",
                "score": 0.9,
                "error_analysis": "Minor notation slip only.",
            }
        },
        metadata={
            "domain": "education",
            "scenario": "remediation_strong",
            "required_node_ids": [
                "design_initial_exercises",
                "capture_attempt",
                "normalize_attempt",
                "lookup_attempt_rubric",
                "review_attempt",
                "decide_remediation_path",
                "coach_progress_path",
            ],
            "required_event_types": ["run.started", "node.succeeded", "run.completed"],
        },
    )


def get_education_eval_cases() -> list[EvaluationCase]:
    return [
        deepcopy(build_diagnostic_plan_eval_case()),
        deepcopy(build_practice_review_eval_case()),
        deepcopy(build_remediation_weak_eval_case()),
        deepcopy(build_remediation_strong_eval_case()),
    ]


def get_education_eval_suites() -> list[EvaluationSuite]:
    cases = {case.case_id: case for case in get_education_eval_cases()}
    return [
        EvaluationSuite(
            suite_id=EDUCATION_EVAL_SUITE_CORE_PATHS,
            name="Education Core Paths",
            cases=[
                deepcopy(cases[EDUCATION_EVAL_CASE_DIAGNOSTIC_PLAN]),
                deepcopy(cases[EDUCATION_EVAL_CASE_PRACTICE_REVIEW]),
            ],
            metadata={"domain": "education", "suite_kind": "core_paths"},
        ),
        EvaluationSuite(
            suite_id=EDUCATION_EVAL_SUITE_REMEDIATION,
            name="Education Remediation Paths",
            cases=[
                deepcopy(cases[EDUCATION_EVAL_CASE_REMEDIATION_WEAK]),
                deepcopy(cases[EDUCATION_EVAL_CASE_REMEDIATION_STRONG]),
            ],
            metadata={"domain": "education", "suite_kind": "remediation_paths"},
        ),
        EvaluationSuite(
            suite_id=EDUCATION_EVAL_SUITE_SMOKE,
            name="Education Domain Smoke",
            cases=[deepcopy(case) for case in cases.values()],
            metadata={"domain": "education", "suite_kind": "smoke"},
        ),
    ]


def build_default_education_eval_scorers(case: EvaluationCase) -> list[EvaluationScorer]:
    required_nodes = list(case.metadata.get("required_node_ids", []))
    required_events = list(case.metadata.get("required_event_types", []))
    return [
        RunStatusScorer(),
        CompletedNodesScorer(required_nodes),
        EventPresenceScorer(required_events),
    ]
