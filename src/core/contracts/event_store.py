from __future__ import annotations

from typing import Protocol

from core.events.event_models import RuntimeEvent


class EventStore(Protocol):
    def append(self, event: RuntimeEvent) -> None: ...

    def append_batch(self, events: list[RuntimeEvent]) -> None: ...

    def get(self, event_id: str) -> RuntimeEvent | None: ...

    def list_by_run(
        self,
        run_id: str,
        *,
        after_sequence_no: int | None = None,
        limit: int | None = None,
    ) -> list[RuntimeEvent]: ...

    def latest_for_run(self, run_id: str) -> RuntimeEvent | None: ...
