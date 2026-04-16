"""Education workflow declarations."""

from .definitions import (
    DIAGNOSTIC_PLAN_WORKFLOW_ID,
    PRACTICE_REVIEW_WORKFLOW_ID,
    REMEDIATION_LOOP_WORKFLOW_ID,
    build_diagnostic_plan_workflow,
    build_practice_review_workflow,
    build_remediation_loop_workflow,
    get_education_workflow_definitions,
)

__all__ = [
    "DIAGNOSTIC_PLAN_WORKFLOW_ID",
    "PRACTICE_REVIEW_WORKFLOW_ID",
    "REMEDIATION_LOOP_WORKFLOW_ID",
    "build_diagnostic_plan_workflow",
    "build_practice_review_workflow",
    "build_remediation_loop_workflow",
    "get_education_workflow_definitions",
]
