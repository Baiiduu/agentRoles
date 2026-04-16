from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.events import RuntimeEvent
from core.state.models import (
    InterruptRecord,
    JsonMap,
    PolicyDecisionRecord,
    ReducedSnapshot,
    SideEffectRecord,
)


@dataclass
class RunObservation:
    run_id: str
    snapshot: ReducedSnapshot
    events: list[RuntimeEvent] = field(default_factory=list)


@dataclass
class TimelineEntry:
    source_kind: str
    occurred_at: datetime
    label: str
    run_id: str
    node_id: str | None = None
    event_type: str | None = None
    sequence_no: int | None = None
    actor_type: str | None = None
    actor_ref: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    payload: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class ObservabilityDigest:
    run_id: str
    tool_event_count: int
    interrupt_count: int
    policy_decision_count: int
    side_effect_count: int
    node_count: int
    completed_node_count: int
    metadata: JsonMap = field(default_factory=dict)


def event_to_timeline_entry(event: RuntimeEvent) -> TimelineEntry:
    return TimelineEntry(
        source_kind="event",
        occurred_at=event.timestamp,
        label=event.event_type,
        run_id=event.run_id or "",
        node_id=event.node_id,
        event_type=event.event_type,
        sequence_no=event.sequence_no,
        actor_type=event.actor_type,
        actor_ref=event.actor_ref,
        trace_id=event.trace_id,
        span_id=event.span_id,
        parent_span_id=event.parent_span_id,
        payload=dict(event.payload),
        metadata=dict(event.metadata),
    )


def side_effect_to_timeline_entry(side_effect: SideEffectRecord) -> TimelineEntry:
    return TimelineEntry(
        source_kind="side_effect",
        occurred_at=side_effect.created_at,
        label=f"side_effect:{side_effect.action}",
        run_id=side_effect.run_id,
        node_id=side_effect.node_id,
        actor_type="tool" if side_effect.target_type == "tool" else side_effect.target_type,
        actor_ref=side_effect.target_ref,
        payload=dict(side_effect.args_summary),
        metadata={
            **dict(side_effect.metadata),
            "kind": str(side_effect.kind),
            "succeeded": side_effect.succeeded,
            "is_idempotent": side_effect.is_idempotent,
        },
    )


def interrupt_to_timeline_entry(interrupt: InterruptRecord) -> TimelineEntry:
    return TimelineEntry(
        source_kind="interrupt",
        occurred_at=interrupt.resolved_at or interrupt.created_at,
        label=f"interrupt:{interrupt.interrupt_type}",
        run_id=interrupt.run_id,
        node_id=interrupt.node_id,
        payload={
            "reason_code": interrupt.reason_code,
            "reason_message": interrupt.reason_message,
            "payload": dict(interrupt.payload),
            "resolution_payload": dict(interrupt.resolution_payload or {}),
        },
        metadata={
            "status": str(interrupt.status),
        },
    )


def policy_decision_to_timeline_entry(decision: PolicyDecisionRecord) -> TimelineEntry:
    return TimelineEntry(
        source_kind="policy_decision",
        occurred_at=decision.created_at,
        label=f"policy:{decision.action}",
        run_id=decision.run_id,
        node_id=decision.node_id,
        payload={
            "reason_code": decision.reason_code,
            "reason_message": decision.reason_message,
            "redactions": list(decision.redactions),
        },
        metadata={
            **dict(decision.metadata),
            "policy_name": decision.policy_name,
        },
    )

