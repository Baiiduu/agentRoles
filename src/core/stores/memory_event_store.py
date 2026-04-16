from __future__ import annotations

from copy import deepcopy

from core.events.event_models import RuntimeEvent


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events_by_id: dict[str, RuntimeEvent] = {}
        self._events_by_run: dict[str, list[RuntimeEvent]] = {}

    def append(self, event: RuntimeEvent) -> None:
        if event.event_id in self._events_by_id:
            raise ValueError(f"event_id '{event.event_id}' already exists")

        stored = deepcopy(event)
        self._events_by_id[event.event_id] = stored
        if event.run_id is not None:
            run_events = self._events_by_run.setdefault(event.run_id, [])
            previous = run_events[-1].sequence_no if run_events else -1
            if stored.sequence_no <= previous:
                raise ValueError(
                    f"event sequence_no must increase for run '{event.run_id}'"
                )
            run_events.append(stored)

    def append_batch(self, events: list[RuntimeEvent]) -> None:
        pending = [deepcopy(event) for event in events]
        seen_ids = set(self._events_by_id)
        run_previous: dict[str, int] = {
            run_id: run_events[-1].sequence_no
            for run_id, run_events in self._events_by_run.items()
            if run_events
        }

        for event in pending:
            if event.event_id in seen_ids:
                raise ValueError(f"event_id '{event.event_id}' already exists")
            seen_ids.add(event.event_id)

            if event.run_id is None:
                continue

            previous = run_previous.get(event.run_id, -1)
            if event.sequence_no <= previous:
                raise ValueError(
                    f"event sequence_no must increase for run '{event.run_id}'"
                )
            run_previous[event.run_id] = event.sequence_no

        for event in pending:
            self.append(event)

    def get(self, event_id: str) -> RuntimeEvent | None:
        event = self._events_by_id.get(event_id)
        return deepcopy(event) if event is not None else None

    def list_by_run(
        self,
        run_id: str,
        *,
        after_sequence_no: int | None = None,
        limit: int | None = None,
    ) -> list[RuntimeEvent]:
        events = self._events_by_run.get(run_id, [])
        filtered = [
            deepcopy(event)
            for event in events
            if after_sequence_no is None or event.sequence_no > after_sequence_no
        ]
        if limit is not None:
            return filtered[:limit]
        return filtered

    def latest_for_run(self, run_id: str) -> RuntimeEvent | None:
        events = self._events_by_run.get(run_id, [])
        if not events:
            return None
        return deepcopy(events[-1])
