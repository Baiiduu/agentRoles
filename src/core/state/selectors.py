from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.state.models import ArtifactRecord, NodeId, NodeState, NodeStatus, ReducedSnapshot
from core.workflow.workflow_models import (
    CompiledWorkflow,
    EdgeConditionType,
    InputSelector,
    InputSource,
    InputSourceType,
    JoinPolicyKind,
    MergeStrategyKind,
    TerminalConditionType,
)


TERMINAL_NODE_STATUSES = {
    NodeStatus.SUCCEEDED,
    NodeStatus.FAILED,
    NodeStatus.SKIPPED,
    NodeStatus.CANCELLED,
}

SUCCESS_NODE_STATUSES = {NodeStatus.SUCCEEDED}


def _extract_path(value: Any, path: str | None) -> Any:
    if path is None or path == "":
        return value

    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"path segment '{part}' not found")
            current = current[part]
        else:
            if not hasattr(current, part):
                raise KeyError(f"path segment '{part}' not found")
            current = getattr(current, part)
    return current


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in incoming.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _artifact_payload(artifact: ArtifactRecord) -> Any:
    if artifact.payload_inline is not None:
        return artifact.payload_inline
    return {
        "payload_ref": artifact.payload_ref,
        "summary": artifact.summary,
        "quality_status": artifact.quality_status,
        "artifact_type": artifact.artifact_type,
    }


class DefaultStateSelector:
    """
    Default selector implementation guided by the design spec.

    Responsibilities:
    1. Resolve structured node input from snapshot data.
    2. Compute which nodes are ready to run.
    3. Evaluate terminal conditions for a compiled workflow.
    """

    def select_node_input(
        self, snapshot: ReducedSnapshot, selector: InputSelector
    ) -> dict[str, object]:
        resolved_values = [
            self._resolve_input_source(snapshot, source) for source in selector.sources
        ]

        if selector.merge_strategy == MergeStrategyKind.REPLACE:
            last = resolved_values[-1]
            if isinstance(last, dict):
                return deepcopy(last)
            return {"value": deepcopy(last)}

        if selector.merge_strategy == MergeStrategyKind.SHALLOW_MERGE:
            merged: dict[str, Any] = {}
            for value in resolved_values:
                if not isinstance(value, dict):
                    raise ValueError("SHALLOW_MERGE requires all resolved input values to be dicts")
                merged.update(deepcopy(value))
            return merged

        if selector.merge_strategy == MergeStrategyKind.DEEP_MERGE:
            merged = {}
            for value in resolved_values:
                if not isinstance(value, dict):
                    raise ValueError("DEEP_MERGE requires all resolved input values to be dicts")
                merged = _deep_merge(merged, value)
            return merged

        raise ValueError(f"unsupported merge_strategy={selector.merge_strategy}")

    def select_ready_nodes(
        self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow
    ) -> list[str]:
        ready_nodes: list[str] = []
        for node_id, node_spec in workflow.node_map.items():
            node_state = snapshot.node_states.get(node_id)
            if node_state is None:
                continue

            if node_state.status == NodeStatus.READY:
                ready_nodes.append(node_id)
                continue

            if node_state.status not in {NodeStatus.PENDING, NodeStatus.BLOCKED}:
                continue

            if self._has_open_interrupt_for_node(snapshot, node_id):
                continue

            if self._dependencies_satisfied(snapshot, workflow, node_id, node_spec.join_policy):
                ready_nodes.append(node_id)

        return ready_nodes

    def terminal_condition_met(
        self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow
    ) -> bool:
        if workflow.terminal_conditions:
            return any(
                self._evaluate_terminal_condition(snapshot, workflow, condition)
                for condition in workflow.terminal_conditions
            )

        workflow_node_ids = set(workflow.node_map)
        known_node_ids = set(snapshot.node_states)
        if not workflow_node_ids.issubset(known_node_ids):
            return False
        return all(
            snapshot.node_states[node_id].status in TERMINAL_NODE_STATUSES
            for node_id in workflow_node_ids
        )

    def _resolve_input_source(self, snapshot: ReducedSnapshot, source: InputSource) -> Any:
        try:
            if source.source_type == InputSourceType.THREAD_STATE:
                base = snapshot.thread_state
                return _extract_path(base, source.path)

            if source.source_type == InputSourceType.RUN_STATE:
                base = snapshot.run_state
                return _extract_path(base, source.path)

            if source.source_type == InputSourceType.ARTIFACT:
                artifact = self._find_artifact(snapshot, source.source_ref)
                return _extract_path(_artifact_payload(artifact), source.path)

            if source.source_type == InputSourceType.LITERAL:
                return source.source_ref

            if source.source_type == InputSourceType.INTERRUPT_RESOLUTION:
                resolution = self._find_interrupt_resolution(snapshot, source.source_ref)
                return _extract_path(resolution, source.path)

            if source.source_type == InputSourceType.MEMORY_RESULT:
                cached = snapshot.run_state.extensions.get("memory_results", {})
                if source.source_ref not in cached:
                    raise KeyError(f"memory result '{source.source_ref}' not found")
                return _extract_path(cached[source.source_ref], source.path)

            raise ValueError(f"unsupported input source_type={source.source_type}")
        except Exception:
            if source.required:
                raise
            return None

    def _find_artifact(self, snapshot: ReducedSnapshot, source_ref: str) -> ArtifactRecord:
        direct = snapshot.artifacts.get(source_ref)
        if direct is not None:
            return direct

        matches = [
            artifact
            for artifact in snapshot.artifacts.values()
            if artifact.producer_node_id == source_ref
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(f"artifact '{source_ref}' not found")
        raise ValueError(
            f"artifact source_ref '{source_ref}' matched multiple producer artifacts"
        )

    def _find_interrupt_resolution(
        self, snapshot: ReducedSnapshot, source_ref: str
    ) -> dict[str, Any]:
        if source_ref in snapshot.interrupts:
            interrupt = snapshot.interrupts[source_ref]
            if interrupt.resolution_payload is None:
                raise KeyError(f"interrupt '{source_ref}' has no resolution_payload")
            return interrupt.resolution_payload

        matches = [
            interrupt
            for interrupt in snapshot.interrupts.values()
            if interrupt.node_id == source_ref and interrupt.resolution_payload is not None
        ]
        if len(matches) == 1:
            return matches[0].resolution_payload or {}
        if not matches:
            raise KeyError(f"interrupt resolution '{source_ref}' not found")
        matches.sort(key=lambda item: item.created_at, reverse=True)
        return matches[0].resolution_payload or {}

    def _has_open_interrupt_for_node(self, snapshot: ReducedSnapshot, node_id: str) -> bool:
        for interrupt_id in snapshot.run_state.pending_interrupt_ids:
            interrupt = snapshot.interrupts.get(interrupt_id)
            if interrupt is not None and interrupt.node_id == node_id:
                return True
        return False

    def _dependencies_satisfied(
        self,
        snapshot: ReducedSnapshot,
        workflow: CompiledWorkflow,
        node_id: str,
        join_policy,
    ) -> bool:
        incoming_edges = workflow.incoming_edges.get(node_id, [])
        if not incoming_edges:
            return node_id == workflow.entry_node_id

        upstream_states: list[NodeState] = []
        for edge in incoming_edges:
            source_state = snapshot.node_states.get(edge.from_node_id)
            if source_state is None:
                return False
            if not self._edge_condition_satisfied(snapshot, source_state, edge.condition):
                continue
            upstream_states.append(source_state)

        if not upstream_states:
            return False

        if join_policy is None or join_policy.kind == JoinPolicyKind.ALL_SUCCESS:
            return all(state.status in SUCCESS_NODE_STATUSES for state in upstream_states)

        if join_policy.kind == JoinPolicyKind.ANY_SUCCESS:
            return any(state.status in SUCCESS_NODE_STATUSES for state in upstream_states)

        if join_policy.kind == JoinPolicyKind.ALL_DONE:
            return all(state.status in TERMINAL_NODE_STATUSES for state in upstream_states)

        if join_policy.kind == JoinPolicyKind.QUORUM:
            success_count = sum(
                1 for state in upstream_states if state.status in SUCCESS_NODE_STATUSES
            )
            return success_count >= (join_policy.quorum or 0)

        raise ValueError(f"unsupported join policy kind={join_policy.kind}")

    def _edge_condition_satisfied(self, snapshot: ReducedSnapshot, state: NodeState, condition) -> bool:
        if condition is None or condition.condition_type == EdgeConditionType.ALWAYS:
            return True

        if condition.condition_type == EdgeConditionType.POLICY_ACTION:
            for decision_id in state.policy_decision_ids:
                decision = snapshot.policy_decisions.get(decision_id)
                if decision is not None and str(decision.action) == str(condition.expected_value):
                    return True
            return False

        artifact = None
        if state.output_artifact_id is not None:
            artifact = snapshot.artifacts.get(state.output_artifact_id)

        if artifact is None:
            return False

        payload = _artifact_payload(artifact)

        if condition.condition_type == EdgeConditionType.RESULT_FIELD_EXISTS:
            try:
                _extract_path(payload, condition.operand_path)
                return True
            except KeyError:
                return False

        if condition.condition_type == EdgeConditionType.RESULT_FIELD_EQUALS:
            try:
                actual = _extract_path(payload, condition.operand_path)
            except KeyError:
                return False
            return actual == condition.expected_value

        if condition.condition_type == EdgeConditionType.CUSTOM_REF:
            return False

        return False

    def _evaluate_terminal_condition(self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow, condition) -> bool:
        if condition.condition_type == TerminalConditionType.ALL_TERMINAL:
            return all(
                snapshot.node_states.get(node_id) is not None
                and snapshot.node_states[node_id].status in TERMINAL_NODE_STATUSES
                for node_id in workflow.node_map
            )

        if condition.condition_type == TerminalConditionType.EXPLICIT_NODE_COMPLETED:
            if condition.node_id is None:
                return False
            node_state = snapshot.node_states.get(condition.node_id)
            return node_state is not None and node_state.status == NodeStatus.SUCCEEDED

        if condition.condition_type == TerminalConditionType.ANY_FATAL_FAILURE:
            return any(
                node_state.status == NodeStatus.FAILED
                for node_state in snapshot.node_states.values()
            )

        if condition.condition_type == TerminalConditionType.CUSTOM_REF:
            return False

        return False
