from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.state.models import (
    ArtifactId,
    CheckpointId,
    EventId,
    InterruptId,
    JsonMap,
    NodeId,
    NodeState,
    PolicyDecisionId,
    RunId,
    RunRecord,
    SideEffectId,
    RunState,
    ThreadId,
    ThreadRecord,
    ThreadState,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class CheckpointRecord:
    checkpoint_id: CheckpointId
    thread_id: ThreadId
    run_id: RunId
    sequence_no: int
    created_at: datetime = field(default_factory=_utcnow)
    reason: str = "auto"
    schema_version: str = "1.0"
    snapshot_ref: str = ""
    frontier_snapshot: list[NodeId] = field(default_factory=list)
    event_cursor: EventId | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("checkpoint_id", self.checkpoint_id),
            ("thread_id", self.thread_id),
            ("run_id", self.run_id),
            ("reason", self.reason),
            ("schema_version", self.schema_version),
        ):
            if not value:
                raise ValueError(f"{name} must be non-empty")
        if self.sequence_no < 0:
            raise ValueError("sequence_no must be >= 0")


@dataclass
class SnapshotPayload:
    thread_record: ThreadRecord
    run_record: RunRecord
    thread_state: ThreadState
    run_state: RunState
    node_states: list[NodeState] = field(default_factory=list)
    artifact_ids: list[ArtifactId] = field(default_factory=list)
    interrupt_ids: list[InterruptId] = field(default_factory=list)
    policy_decision_ids: list[PolicyDecisionId] = field(default_factory=list)
    side_effect_ids: list[SideEffectId] = field(default_factory=list)
    last_event_id: EventId | None = None
