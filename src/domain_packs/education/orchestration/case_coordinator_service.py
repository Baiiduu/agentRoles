from __future__ import annotations

from .coordinator_models import (
    CaseCoordinationInput,
    CaseCoordinationRecommendation,
)


class CaseCoordinatorService:
    """
    Advisory case-level coordinator.

    This layer recommends the next mode of collaboration but never executes it.
    """

    def recommend(
        self,
        coordination_input: CaseCoordinationInput,
    ) -> CaseCoordinationRecommendation:
        artifact_types = set(coordination_input.artifact_types)
        stage = coordination_input.current_stage.strip().lower()
        session_summaries = " ".join(coordination_input.session_summaries).lower()

        if "education.learner_profile" not in artifact_types:
            return CaseCoordinationRecommendation(
                recommended_mode="agent_session",
                recommended_agent_id="learner_profiler",
                recommended_workflow_id=None,
                reason_summary="当前 case 还缺少稳定的 learner profile，先补学情画像。",
                supporting_signals=[
                    "missing learner profile artifact",
                    f"current stage: {stage or 'unknown'}",
                ],
            )

        if "education.study_plan" not in artifact_types:
            return CaseCoordinationRecommendation(
                recommended_mode="agent_session",
                recommended_agent_id="curriculum_planner",
                recommended_workflow_id=None,
                reason_summary="画像已具备，但学习计划还不完整，先补计划层协作。",
                supporting_signals=[
                    "learner profile already exists",
                    "missing study plan artifact",
                ],
            )

        if (
            stage in {"practice", "practice_review"}
            and "education.review_summary" not in artifact_types
        ):
            return CaseCoordinationRecommendation(
                recommended_mode="workflow_run",
                recommended_agent_id=None,
                recommended_workflow_id="education.practice_review",
                reason_summary="当前进入练习阶段，适合进入正式评审 workflow。",
                supporting_signals=[
                    f"current stage: {stage}",
                    "review summary missing",
                ],
            )

        if "补救" in session_summaries or "weak" in session_summaries or "薄弱" in session_summaries:
            return CaseCoordinationRecommendation(
                recommended_mode="human_review",
                recommended_agent_id=None,
                recommended_workflow_id=None,
                reason_summary="最近协作信号显示需要补救，建议教师先确认下一步。",
                supporting_signals=[
                    "recent session feed signals remediation need",
                    f"handoff count: {coordination_input.handoff_count}",
                ],
            )

        return CaseCoordinationRecommendation(
            recommended_mode="agent_session",
            recommended_agent_id="tutor_coach",
            recommended_workflow_id=None,
            reason_summary="当前 case 已有画像和计划，适合继续由 tutor coach 做解释与推进。",
            supporting_signals=[
                "profile and plan artifacts exist",
                f"handoff count: {coordination_input.handoff_count}",
            ],
        )
