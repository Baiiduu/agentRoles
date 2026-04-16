from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
from typing import Any

from .models import (
    ArtifactId,
    ArtifactRecord,
    InterruptRecord,
    InterruptId,
    InterruptStatus,
    InterruptType,
    NodeId,
    NodeState,
    PolicyDecisionRecord,
    ReducedSnapshot,
    SideEffectRecord,
    StatePatch,
)


def _field_names(instance: object) -> set[str]:
    return {f.name for f in fields(instance)}


def _validate_update_keys(instance: object, updates: dict[str, Any], label: str) -> None:
    unknown = set(updates) - _field_names(instance)
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {sorted(unknown)}")


def _merge_value(current: Any, incoming: Any) -> Any:
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = dict(current)
        merged.update(incoming)
        return merged
    return incoming


def _apply_updates(instance: object, updates: dict[str, Any], label: str) -> object:
    if not updates:
        return instance
    _validate_update_keys(instance, updates, label)
    merged_updates = {}
    for key, value in updates.items():
        merged_updates[key] = _merge_value(getattr(instance, key), value)
    return replace(instance, **merged_updates)


def _bump_version(instance: object) -> object:
    if "version" not in _field_names(instance):
        return instance
    return replace(instance, version=getattr(instance, "version") + 1)


def _ensure_same_run(value: str, expected: str, label: str) -> None:
    if value != expected:
        raise ValueError(f"{label} must match current run_id={expected}, got {value}")


def _ensure_same_thread(value: str, expected: str, label: str) -> None:
    if value != expected:
        raise ValueError(f"{label} must match current thread_id={expected}, got {value}")


class StateReducer:
    """
    Apply a `StatePatch` to the current snapshot and return a new snapshot.

    Design constraints inherited from the spec:
    1. Reducer is the only component allowed to generate new state versions.
    2. Reducer does not persist anything.
    3. Reducer does not execute business logic; it only merges structured patch data.
    """

    def apply(self, current_snapshot: ReducedSnapshot, patch: StatePatch) -> ReducedSnapshot:
        thread_record = deepcopy(current_snapshot.thread_record)
        run_record = deepcopy(current_snapshot.run_record)
        thread_state = deepcopy(current_snapshot.thread_state)
        run_state = deepcopy(current_snapshot.run_state)
        node_states = deepcopy(current_snapshot.node_states)
        artifacts = deepcopy(current_snapshot.artifacts)
        interrupts = deepcopy(current_snapshot.interrupts)
        policy_decisions = deepcopy(current_snapshot.policy_decisions)
        side_effects = deepcopy(current_snapshot.side_effects)

        thread_record_updated = False
        run_record_updated = False
        thread_state_updated = False
        run_state_updated = False

        if patch.thread_record_updates:
            thread_record = _apply_updates(
                thread_record, patch.thread_record_updates, "thread_record_updates"
            )
            thread_record = _bump_version(thread_record)
            thread_record_updated = True

        if patch.run_record_updates:
            run_record = _apply_updates(run_record, patch.run_record_updates, "run_record_updates")
            run_record = _bump_version(run_record)
            run_record_updated = True

        if patch.thread_state_updates:
            thread_state = _apply_updates(
                thread_state, patch.thread_state_updates, "thread_state_updates"
            )
            thread_state = _bump_version(thread_state)
            thread_state_updated = True

        if patch.run_state_updates:
            run_state = _apply_updates(run_state, patch.run_state_updates, "run_state_updates")
            run_state = _bump_version(run_state)
            run_state_updated = True

        for node_state in patch.node_states_to_upsert:
            _ensure_same_run(node_state.run_id, run_state.run_id, "NodeState.run_id")
            existing = node_states.get(node_state.node_id)
            upserted = deepcopy(node_state)
            if existing is not None:
                upserted = replace(upserted, version=existing.version + 1)
            node_states[node_state.node_id] = upserted

        if patch.node_state_updates:
            for node_id, updates in patch.node_state_updates.items():
                if node_id not in node_states:
                    raise ValueError(f"node_state_updates references unknown node_id={node_id}")
                if not isinstance(updates, dict):
                    raise ValueError(
                        f"node_state_updates[{node_id}] must be a dict of field updates"
                    )
                updated_node = _apply_updates(
                    node_states[node_id], updates, f"node_state_updates[{node_id}]"
                )
                node_states[node_id] = _bump_version(updated_node)

        artifact_ids_to_append: list[ArtifactId] = []
        for artifact in patch.artifacts_to_create:
            _ensure_same_run(artifact.run_id, run_state.run_id, "ArtifactRecord.run_id")
            _ensure_same_thread(
                artifact.thread_id, thread_state.thread_id, "ArtifactRecord.thread_id"
            )
            if artifact.artifact_id in artifacts:
                raise ValueError(f"duplicate artifact_id={artifact.artifact_id}")
            artifacts[artifact.artifact_id] = deepcopy(artifact)
            artifact_ids_to_append.append(artifact.artifact_id)
            producer_node = node_states.get(artifact.producer_node_id)
            if producer_node is not None and producer_node.output_artifact_id is None:
                node_states[artifact.producer_node_id] = _bump_version(
                    replace(producer_node, output_artifact_id=artifact.artifact_id)
                )

        if artifact_ids_to_append:
            merged_ids = list(thread_state.artifact_ids)
            for artifact_id in artifact_ids_to_append:
                if artifact_id not in merged_ids:
                    merged_ids.append(artifact_id)
            thread_state = replace(thread_state, artifact_ids=merged_ids)
            thread_state = _bump_version(thread_state)
            thread_state_updated = True

        interrupt_ids_to_append: list[str] = []
        approval_ids_to_append: list[str] = []
        for interrupt in patch.interrupts_to_create:
            _ensure_same_run(interrupt.run_id, run_state.run_id, "InterruptRecord.run_id")
            _ensure_same_thread(
                interrupt.thread_id, thread_state.thread_id, "InterruptRecord.thread_id"
            )
            if interrupt.interrupt_id in interrupts:
                raise ValueError(f"duplicate interrupt_id={interrupt.interrupt_id}")
            interrupts[interrupt.interrupt_id] = deepcopy(interrupt)
            if interrupt.status == InterruptStatus.OPEN:
                interrupt_ids_to_append.append(interrupt.interrupt_id)
                if interrupt.interrupt_type == InterruptType.APPROVAL_REQUIRED:
                    approval_ids_to_append.append(interrupt.interrupt_id)

        if interrupt_ids_to_append or approval_ids_to_append:
            pending_interrupt_ids = list(run_state.pending_interrupt_ids)
            pending_approval_ids = list(run_state.pending_approval_ids)
            for interrupt_id in interrupt_ids_to_append:
                if interrupt_id not in pending_interrupt_ids:
                    pending_interrupt_ids.append(interrupt_id)
            for interrupt_id in approval_ids_to_append:
                if interrupt_id not in pending_approval_ids:
                    pending_approval_ids.append(interrupt_id)
            run_state = replace(
                run_state,
                pending_interrupt_ids=pending_interrupt_ids,
                pending_approval_ids=pending_approval_ids,
            )
            run_state = _bump_version(run_state)
            run_state_updated = True

        if patch.interrupt_updates:
            pending_interrupt_ids = list(run_state.pending_interrupt_ids)
            pending_approval_ids = list(run_state.pending_approval_ids)
            for interrupt_id, updates in patch.interrupt_updates.items():
                if interrupt_id not in interrupts:
                    raise ValueError(
                        f"interrupt_updates references unknown interrupt_id={interrupt_id}"
                    )
                if not isinstance(updates, dict):
                    raise ValueError(
                        f"interrupt_updates[{interrupt_id}] must be a dict of field updates"
                    )
                updated_interrupt = _apply_updates(
                    interrupts[interrupt_id], updates, f"interrupt_updates[{interrupt_id}]"
                )
                updated_interrupt = _bump_version(updated_interrupt)
                interrupts[interrupt_id] = updated_interrupt
                if updated_interrupt.status == InterruptStatus.OPEN:
                    if interrupt_id not in pending_interrupt_ids:
                        pending_interrupt_ids.append(interrupt_id)
                    if (
                        updated_interrupt.interrupt_type == InterruptType.APPROVAL_REQUIRED
                        and interrupt_id not in pending_approval_ids
                    ):
                        pending_approval_ids.append(interrupt_id)
                else:
                    pending_interrupt_ids = [
                        item for item in pending_interrupt_ids if item != interrupt_id
                    ]
                    pending_approval_ids = [
                        item for item in pending_approval_ids if item != interrupt_id
                    ]
            run_state = replace(
                run_state,
                pending_interrupt_ids=pending_interrupt_ids,
                pending_approval_ids=pending_approval_ids,
            )
            run_state = _bump_version(run_state)
            run_state_updated = True

        for decision in patch.policy_decisions_to_create:
            _ensure_same_run(decision.run_id, run_state.run_id, "PolicyDecisionRecord.run_id")
            if decision.decision_id in policy_decisions:
                raise ValueError(f"duplicate decision_id={decision.decision_id}")
            policy_decisions[decision.decision_id] = deepcopy(decision)
            if decision.node_id is not None and decision.node_id in node_states:
                node = node_states[decision.node_id]
                decision_ids = list(node.policy_decision_ids)
                if decision.decision_id not in decision_ids:
                    decision_ids.append(decision.decision_id)
                    node_states[decision.node_id] = _bump_version(
                        replace(node, policy_decision_ids=decision_ids)
                    )

        for side_effect in patch.side_effects_to_create:
            _ensure_same_run(side_effect.run_id, run_state.run_id, "SideEffectRecord.run_id")
            if side_effect.side_effect_id in side_effects:
                raise ValueError(f"duplicate side_effect_id={side_effect.side_effect_id}")
            side_effects[side_effect.side_effect_id] = deepcopy(side_effect)
            if side_effect.node_id in node_states:
                node = node_states[side_effect.node_id]
                side_effect_ids = list(node.side_effect_ids)
                if side_effect.side_effect_id not in side_effect_ids:
                    side_effect_ids.append(side_effect.side_effect_id)
                    node_states[side_effect.node_id] = _bump_version(
                        replace(node, side_effect_ids=side_effect_ids)
                    )

        return ReducedSnapshot(
            thread_record=thread_record,
            run_record=run_record,
            thread_state=thread_state,
            run_state=run_state,
            node_states=node_states,
            artifacts=artifacts,
            interrupts=interrupts,
            policy_decisions=policy_decisions,
            side_effects=side_effects,
        )
