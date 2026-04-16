from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


JsonMap = dict[str, Any]


def _new_handoff_id() -> str:
    return f"handoff_{uuid4().hex}"


@dataclass
class CaseHandoffRequest:
    case_id: str
    target_agent_id: str
    requested_by: str = "teacher"
    reason: str = ""
    context_overrides: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.case_id = self.case_id.strip()
        self.target_agent_id = self.target_agent_id.strip()
        self.requested_by = self.requested_by.strip() or "teacher"
        self.reason = self.reason.strip()
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.target_agent_id:
            raise ValueError("target_agent_id must be non-empty")


@dataclass
class CaseHandoffRecord:
    case_id: str
    target_agent_id: str
    requested_by: str
    reason: str = ""
    context_overrides: JsonMap = field(default_factory=dict)
    handoff_id: str = field(default_factory=_new_handoff_id)
    source: str = "manual_case_workspace"
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    resolved_session_id: str | None = None


@dataclass
class CaseSessionFeedItem:
    case_id: str
    session_id: str
    agent_id: str
    agent_name: str
    status: str
    summary: str
    artifact_type: str | None = None
    source: str = "agent_playground"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
