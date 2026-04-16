from __future__ import annotations

from copy import deepcopy

from core.checkpoint.checkpoint_models import CheckpointRecord, SnapshotPayload


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointRecord] = {}
        self._payloads: dict[str, SnapshotPayload] = {}
        self._checkpoint_ids_by_run: dict[str, list[str]] = {}

    def create(
        self, checkpoint: CheckpointRecord, snapshot: SnapshotPayload
    ) -> CheckpointRecord:
        if checkpoint.checkpoint_id in self._checkpoints:
            raise ValueError(
                f"checkpoint_id '{checkpoint.checkpoint_id}' already exists"
            )
        self._validate_consistency(checkpoint, snapshot)

        stored_checkpoint = deepcopy(checkpoint)
        stored_snapshot = deepcopy(snapshot)
        self._checkpoints[checkpoint.checkpoint_id] = stored_checkpoint
        self._payloads[checkpoint.checkpoint_id] = stored_snapshot
        self._checkpoint_ids_by_run.setdefault(checkpoint.run_id, []).append(
            checkpoint.checkpoint_id
        )
        return deepcopy(stored_checkpoint)

    def get(self, checkpoint_id: str) -> CheckpointRecord | None:
        checkpoint = self._checkpoints.get(checkpoint_id)
        return deepcopy(checkpoint) if checkpoint is not None else None

    def latest(self, run_id: str) -> CheckpointRecord | None:
        checkpoints = self.list_for_run(run_id)
        if not checkpoints:
            return None
        return checkpoints[-1]

    def list_for_run(self, run_id: str) -> list[CheckpointRecord]:
        checkpoint_ids = self._checkpoint_ids_by_run.get(run_id, [])
        checkpoints = [
            deepcopy(self._checkpoints[checkpoint_id]) for checkpoint_id in checkpoint_ids
        ]
        checkpoints.sort(key=lambda item: (item.sequence_no, item.created_at))
        return checkpoints

    def restore(self, checkpoint_id: str) -> SnapshotPayload:
        payload = self._payloads.get(checkpoint_id)
        if payload is None:
            raise KeyError(f"checkpoint '{checkpoint_id}' not found")
        return deepcopy(payload)

    def _validate_consistency(
        self, checkpoint: CheckpointRecord, snapshot: SnapshotPayload
    ) -> None:
        if checkpoint.run_id != snapshot.run_record.run_id:
            raise ValueError("checkpoint run_id must match snapshot.run_record.run_id")
        if checkpoint.thread_id != snapshot.thread_record.thread_id:
            raise ValueError(
                "checkpoint thread_id must match snapshot.thread_record.thread_id"
            )
        if snapshot.run_record.thread_id != snapshot.thread_record.thread_id:
            raise ValueError(
                "snapshot run_record.thread_id must match thread_record.thread_id"
            )
        if snapshot.run_state.run_id != snapshot.run_record.run_id:
            raise ValueError("snapshot run_state.run_id must match run_record.run_id")
        if snapshot.run_state.thread_id != snapshot.thread_record.thread_id:
            raise ValueError(
                "snapshot run_state.thread_id must match thread_record.thread_id"
            )
        if snapshot.thread_state.thread_id != snapshot.thread_record.thread_id:
            raise ValueError(
                "snapshot thread_state.thread_id must match thread_record.thread_id"
            )
        for node_state in snapshot.node_states:
            if node_state.run_id != snapshot.run_record.run_id:
                raise ValueError("snapshot node_state.run_id must match run_record.run_id")
