from __future__ import annotations

from copy import deepcopy

from core.contracts.types import StateStoreSnapshot
from core.state.models import (
    ArtifactRecord,
    InterruptRecord,
    NodeState,
    PolicyDecisionRecord,
    RunRecord,
    RunState,
    SideEffectRecord,
    ThreadRecord,
    ThreadState,
)


class InMemoryStateStore:
    def __init__(self) -> None:
        self._thread_records: dict[str, ThreadRecord] = {}
        self._run_records: dict[str, RunRecord] = {}
        self._thread_states: dict[str, ThreadState] = {}
        self._run_states: dict[str, RunState] = {}
        self._node_states: dict[tuple[str, str], NodeState] = {}
        self._artifacts: dict[str, ArtifactRecord] = {}
        self._interrupts: dict[str, InterruptRecord] = {}
        self._policy_decisions: dict[str, PolicyDecisionRecord] = {}
        self._side_effects: dict[str, SideEffectRecord] = {}

    def get_thread_record(self, thread_id: str) -> ThreadRecord | None:
        record = self._thread_records.get(thread_id)
        return deepcopy(record) if record is not None else None

    def save_thread_record(self, thread_record: ThreadRecord) -> ThreadRecord:
        stored = deepcopy(thread_record)
        self._thread_records[thread_record.thread_id] = stored
        return deepcopy(stored)

    def get_run_record(self, run_id: str) -> RunRecord | None:
        record = self._run_records.get(run_id)
        return deepcopy(record) if record is not None else None

    def save_run_record(self, run_record: RunRecord) -> RunRecord:
        stored = deepcopy(run_record)
        self._run_records[run_record.run_id] = stored
        return deepcopy(stored)

    def get_thread_state(self, thread_id: str) -> ThreadState | None:
        state = self._thread_states.get(thread_id)
        return deepcopy(state) if state is not None else None

    def save_thread_state(self, thread_state: ThreadState) -> ThreadState:
        stored = deepcopy(thread_state)
        self._thread_states[thread_state.thread_id] = stored
        return deepcopy(stored)

    def get_run_state(self, run_id: str) -> RunState | None:
        state = self._run_states.get(run_id)
        return deepcopy(state) if state is not None else None

    def save_run_state(self, run_state: RunState) -> RunState:
        stored = deepcopy(run_state)
        self._run_states[run_state.run_id] = stored
        return deepcopy(stored)

    def get_node_state(self, run_id: str, node_id: str) -> NodeState | None:
        state = self._node_states.get((run_id, node_id))
        return deepcopy(state) if state is not None else None

    def save_node_state(self, node_state: NodeState) -> NodeState:
        stored = deepcopy(node_state)
        self._node_states[(node_state.run_id, node_state.node_id)] = stored
        return deepcopy(stored)

    def list_node_states(self, run_id: str) -> list[NodeState]:
        states = [
            deepcopy(state)
            for (candidate_run_id, _), state in self._node_states.items()
            if candidate_run_id == run_id
        ]
        states.sort(key=lambda item: item.node_id)
        return states

    def save_artifact(self, artifact_record: ArtifactRecord) -> ArtifactRecord:
        stored = deepcopy(artifact_record)
        self._artifacts[artifact_record.artifact_id] = stored
        return deepcopy(stored)

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        artifact = self._artifacts.get(artifact_id)
        return deepcopy(artifact) if artifact is not None else None

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        records = [
            deepcopy(record)
            for record in self._artifacts.values()
            if record.run_id == run_id
        ]
        records.sort(key=lambda item: (item.created_at, item.artifact_id))
        return records

    def save_interrupt(self, interrupt_record: InterruptRecord) -> InterruptRecord:
        stored = deepcopy(interrupt_record)
        self._interrupts[interrupt_record.interrupt_id] = stored
        return deepcopy(stored)

    def get_interrupt(self, interrupt_id: str) -> InterruptRecord | None:
        interrupt = self._interrupts.get(interrupt_id)
        return deepcopy(interrupt) if interrupt is not None else None

    def list_interrupts(self, run_id: str) -> list[InterruptRecord]:
        records = [
            deepcopy(record)
            for record in self._interrupts.values()
            if record.run_id == run_id
        ]
        records.sort(key=lambda item: (item.created_at, item.interrupt_id))
        return records

    def save_policy_decision(
        self, record: PolicyDecisionRecord
    ) -> PolicyDecisionRecord:
        stored = deepcopy(record)
        self._policy_decisions[record.decision_id] = stored
        return deepcopy(stored)

    def list_policy_decisions(self, run_id: str) -> list[PolicyDecisionRecord]:
        records = [
            deepcopy(record)
            for record in self._policy_decisions.values()
            if record.run_id == run_id
        ]
        records.sort(key=lambda item: (item.created_at, item.decision_id))
        return records

    def save_side_effect(self, record: SideEffectRecord) -> SideEffectRecord:
        stored = deepcopy(record)
        self._side_effects[record.side_effect_id] = stored
        return deepcopy(stored)

    def list_side_effects(self, run_id: str) -> list[SideEffectRecord]:
        records = [
            deepcopy(record)
            for record in self._side_effects.values()
            if record.run_id == run_id
        ]
        records.sort(key=lambda item: (item.created_at, item.side_effect_id))
        return records

    def build_snapshot(self, run_id: str) -> StateStoreSnapshot:
        run_record = self._run_records.get(run_id)
        if run_record is None:
            raise KeyError(f"run_record '{run_id}' not found")

        thread_record = self._thread_records.get(run_record.thread_id)
        if thread_record is None:
            raise KeyError(f"thread_record '{run_record.thread_id}' not found")

        run_state = self._run_states.get(run_id)
        if run_state is None:
            raise KeyError(f"run_state '{run_id}' not found")

        thread_state = self._thread_states.get(run_record.thread_id)
        if thread_state is None:
            raise KeyError(f"thread_state '{run_record.thread_id}' not found")

        return StateStoreSnapshot(
            thread_record=deepcopy(thread_record),
            run_record=deepcopy(run_record),
            thread_state=deepcopy(thread_state),
            run_state=deepcopy(run_state),
            node_states={
                node_id: deepcopy(node_state)
                for (candidate_run_id, node_id), node_state in self._node_states.items()
                if candidate_run_id == run_id
            },
            artifacts={
                record.artifact_id: deepcopy(record)
                for record in self._artifacts.values()
                if record.run_id == run_id
            },
            interrupts={
                record.interrupt_id: deepcopy(record)
                for record in self._interrupts.values()
                if record.run_id == run_id
            },
            policy_decisions={
                record.decision_id: deepcopy(record)
                for record in self._policy_decisions.values()
                if record.run_id == run_id
            },
            side_effects={
                record.side_effect_id: deepcopy(record)
                for record in self._side_effects.values()
                if record.run_id == run_id
            },
            metadata={"backend": "memory"},
        )
