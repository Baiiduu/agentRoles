from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Protocol

from core.events.event_models import EventDraft, RuntimeEvent
from core.events.tracing import TraceContext


class _EventStoreLike(Protocol):
    def append(self, event: RuntimeEvent) -> None: ...

    def append_batch(self, events: list[RuntimeEvent]) -> None: ...

    def latest_for_run(self, run_id: str) -> RuntimeEvent | None: ...


class _ClockLike(Protocol):
    def now(self) -> datetime: ...


class _IdGeneratorLike(Protocol):
    def new(self, prefix: str | None = None) -> str: ...


class RuntimeEventEmitter:
    """Materializes sequence numbers and trace fields for runtime events."""

    def __init__(
        self,
        *,
        event_store: _EventStoreLike,
        clock: _ClockLike,
        id_generator: _IdGeneratorLike,
    ) -> None:
        self._event_store = event_store
        self._clock = clock
        self._id_generator = id_generator

    def emit_thread_event(self, draft: EventDraft) -> RuntimeEvent:
        if draft.run_id is not None:
            raise ValueError("emit_thread_event expects draft.run_id to be None")
        event = self._materialize(draft, sequence_no=0)
        self._event_store.append(event)
        return deepcopy(event)

    def emit_run_events(self, run_id: str, drafts: list[EventDraft]) -> list[RuntimeEvent]:
        if not drafts:
            return []
        next_sequence = self._next_sequence_no(run_id)
        events = [
            self._materialize(draft, sequence_no=next_sequence + offset)
            for offset, draft in enumerate(drafts)
        ]
        self._event_store.append_batch(events)
        return [deepcopy(item) for item in events]

    def _materialize(self, draft: EventDraft, *, sequence_no: int) -> RuntimeEvent:
        trace_context = draft.trace_context
        return RuntimeEvent(
            event_id=self._id_generator.new("event"),
            event_type=draft.event_type,
            thread_id=draft.thread_id,
            run_id=draft.run_id,
            node_id=draft.node_id,
            actor_type=draft.actor_type,
            actor_ref=draft.actor_ref,
            trace_id=trace_context.trace_id if trace_context is not None else None,
            span_id=trace_context.span_id if trace_context is not None else None,
            parent_span_id=trace_context.parent_span_id if trace_context is not None else None,
            sequence_no=sequence_no,
            timestamp=self._clock.now(),
            payload=deepcopy(draft.payload),
            metadata=self._metadata(draft.metadata, trace_context),
        )

    def _metadata(self, metadata: dict[str, object], trace_context: TraceContext | None) -> dict[str, object]:
        merged = deepcopy(metadata)
        if trace_context is not None:
            merged["trace_context"] = trace_context.to_map()
        return merged

    def _next_sequence_no(self, run_id: str) -> int:
        latest = self._event_store.latest_for_run(run_id)
        if latest is None:
            return 1
        return latest.sequence_no + 1
