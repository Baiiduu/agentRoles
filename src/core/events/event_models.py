from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.state.models import EventId, JsonMap, NodeId, RunId, ThreadId

from .tracing import TraceContext


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class RuntimeEvent:
    event_id: EventId
    event_type: str
    thread_id: ThreadId
    run_id: RunId | None
    node_id: NodeId | None
    actor_type: str | None = None
    actor_ref: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    sequence_no: int = 0
    timestamp: datetime = field(default_factory=_utcnow)
    payload: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.event_type:
            raise ValueError("event_type must be non-empty")
        if not self.thread_id:
            raise ValueError("thread_id must be non-empty")
        if self.sequence_no < 0:
            raise ValueError("sequence_no must be >= 0")
        if self.trace_id is not None and not self.trace_id:
            raise ValueError("trace_id must be non-empty when provided")
        if self.span_id is not None and not self.span_id:
            raise ValueError("span_id must be non-empty when provided")


@dataclass
class EventDraft:
    event_type: str
    thread_id: ThreadId
    run_id: RunId | None
    node_id: NodeId | None = None
    actor_type: str | None = None
    actor_ref: str | None = None
    payload: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)
    trace_context: TraceContext | None = None

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type must be non-empty")
        if not self.thread_id:
            raise ValueError("thread_id must be non-empty")
