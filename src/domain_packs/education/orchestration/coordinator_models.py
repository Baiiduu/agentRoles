from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CaseCoordinationInput:
    case_id: str
    current_stage: str
    artifact_types: list[str] = field(default_factory=list)
    session_summaries: list[str] = field(default_factory=list)
    handoff_count: int = 0


@dataclass
class CaseCoordinationRecommendation:
    recommended_mode: str
    recommended_agent_id: str | None
    recommended_workflow_id: str | None
    reason_summary: str
    supporting_signals: list[str] = field(default_factory=list)
