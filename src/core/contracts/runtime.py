from __future__ import annotations

from typing import Iterable, Protocol

from core.events.event_models import RuntimeEvent
from core.state.models import ReducedSnapshot, RunRecord, ThreadRecord

from .types import ReplayHandle


class Runtime(Protocol):
    def create_thread(
        self,
        thread_type: str,
        goal: str,
        *,
        title: str | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ThreadRecord: ...

    def start_run(
        self,
        thread_id: str,
        workflow_id: str,
        *,
        workflow_version: str | None = None,
        trigger: str = "manual",
        trigger_payload: dict[str, object] | None = None,
    ) -> RunRecord: ...

    def resume_run(
        self,
        run_id: str,
        resolution_payload: dict[str, object] | None = None,
    ) -> RunRecord: ...

    def cancel_run(self, run_id: str, *, reason: str | None = None) -> RunRecord: ...

    def replay_run(
        self,
        run_id: str,
        *,
        checkpoint_id: str | None = None,
        mode: str = "diagnostic",
    ) -> ReplayHandle: ...

    def get_thread(self, thread_id: str) -> ThreadRecord | None: ...

    def get_run(self, run_id: str) -> RunRecord | None: ...

    def get_state(self, run_id: str) -> ReducedSnapshot: ...

    def stream_events(
        self,
        run_id: str,
        *,
        after_sequence_no: int | None = None,
        limit: int | None = None,
    ) -> Iterable[RuntimeEvent]: ...
