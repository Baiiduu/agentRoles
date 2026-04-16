from __future__ import annotations

from typing import Protocol

from core.checkpoint.checkpoint_models import CheckpointRecord, SnapshotPayload


class CheckpointStore(Protocol):
    def create(
        self, checkpoint: CheckpointRecord, snapshot: SnapshotPayload
    ) -> CheckpointRecord: ...

    def get(self, checkpoint_id: str) -> CheckpointRecord | None: ...

    def latest(self, run_id: str) -> CheckpointRecord | None: ...

    def list_for_run(self, run_id: str) -> list[CheckpointRecord]: ...

    def restore(self, checkpoint_id: str) -> SnapshotPayload: ...

