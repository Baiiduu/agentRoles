from __future__ import annotations

from copy import deepcopy

from core.state.models import NodeId, NodeType
from core.workflow.workflow_models import (
    CompiledWorkflow,
    EdgeSpec,
    JoinPolicyKind,
    NodeSpec,
    TerminalConditionType,
    WorkflowDefinition,
)


class WorkflowCompileError(ValueError):
    """Raised when a workflow definition cannot be compiled safely."""


class WorkflowCompiler:
    """
    Compile declarative workflow definitions into runtime-friendly structures.

    The compiler is intentionally strict: it rejects invalid or underspecified
    graphs before any run is created, so runtime code can assume structural
    invariants already hold.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], CompiledWorkflow] = {}

    def compile(
        self, definition: WorkflowDefinition, *, use_cache: bool = True
    ) -> CompiledWorkflow:
        cache_key = (definition.workflow_id, definition.version)
        if use_cache and cache_key in self._cache:
            return deepcopy(self._cache[cache_key])

        node_map = self._materialize_node_map(definition)
        outgoing_edges = {node_id: [] for node_id in node_map}
        incoming_edges = {node_id: [] for node_id in node_map}

        for edge in definition.edge_specs:
            self._validate_edge_reference(edge, node_map)
            compiled_edge = deepcopy(edge)
            outgoing_edges[compiled_edge.from_node_id].append(compiled_edge)
            incoming_edges[compiled_edge.to_node_id].append(compiled_edge)

        self._validate_terminal_conditions(definition, node_map)
        self._validate_node_constraints(node_map, incoming_edges)

        contains_cycles = self._contains_cycle(node_map, outgoing_edges)
        if contains_cycles and not definition.allow_cycles:
            raise WorkflowCompileError(
                "workflow contains directed cycles but allow_cycles is False"
            )
        if contains_cycles and not definition.terminal_conditions:
            raise WorkflowCompileError(
                "workflow contains directed cycles but does not define terminal_conditions"
            )

        compiled = CompiledWorkflow(
            workflow_id=definition.workflow_id,
            version=definition.version,
            entry_node_id=definition.entry_node_id,
            node_map=node_map,
            outgoing_edges=outgoing_edges,
            incoming_edges=incoming_edges,
            allow_cycles=definition.allow_cycles,
            contains_cycles=contains_cycles,
            terminal_conditions=list(definition.terminal_conditions),
        )

        if use_cache:
            self._cache[cache_key] = deepcopy(compiled)
        return compiled

    def invalidate(self, workflow_id: str, version: str | None = None) -> None:
        if version is None:
            keys_to_delete = [
                key for key in self._cache if key[0] == workflow_id
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return

        self._cache.pop((workflow_id, version), None)

    def clear_cache(self) -> None:
        self._cache.clear()

    def _materialize_node_map(
        self, definition: WorkflowDefinition
    ) -> dict[NodeId, NodeSpec]:
        node_map: dict[NodeId, NodeSpec] = {}
        for original in definition.node_specs:
            node = deepcopy(original)
            if node.retry_policy is None and definition.default_retry_policy is not None:
                node.retry_policy = deepcopy(definition.default_retry_policy)
            if node.timeout_policy is None and definition.default_timeout_policy is not None:
                node.timeout_policy = deepcopy(definition.default_timeout_policy)
            node_map[node.node_id] = node
        return node_map

    def _validate_edge_reference(
        self, edge: EdgeSpec, node_map: dict[NodeId, NodeSpec]
    ) -> None:
        if edge.from_node_id not in node_map:
            raise WorkflowCompileError(
                f"edge '{edge.edge_id}' references missing from_node_id '{edge.from_node_id}'"
            )
        if edge.to_node_id not in node_map:
            raise WorkflowCompileError(
                f"edge '{edge.edge_id}' references missing to_node_id '{edge.to_node_id}'"
            )

    def _validate_terminal_conditions(
        self, definition: WorkflowDefinition, node_map: dict[NodeId, NodeSpec]
    ) -> None:
        for condition in definition.terminal_conditions:
            if (
                condition.condition_type == TerminalConditionType.EXPLICIT_NODE_COMPLETED
                and condition.node_id not in node_map
            ):
                raise WorkflowCompileError(
                    f"terminal condition references missing node_id '{condition.node_id}'"
                )

    def _validate_node_constraints(
        self,
        node_map: dict[NodeId, NodeSpec],
        incoming_edges: dict[NodeId, list[EdgeSpec]],
    ) -> None:
        for node_id, node in node_map.items():
            incoming = incoming_edges[node_id]

            if node.node_type == NodeType.MERGE and not incoming:
                raise WorkflowCompileError(
                    f"merge node '{node_id}' must declare at least one incoming edge"
                )

            if node.node_type == NodeType.HUMAN_GATE and node.approval_policy is None:
                raise WorkflowCompileError(
                    f"human_gate node '{node_id}' must declare approval_policy"
                )

            if (
                node.join_policy is not None
                and node.join_policy.kind == JoinPolicyKind.QUORUM
                and node.join_policy.quorum is not None
                and incoming
                and node.join_policy.quorum > len(incoming)
            ):
                raise WorkflowCompileError(
                    f"node '{node_id}' declares quorum={node.join_policy.quorum} "
                    f"but only has {len(incoming)} incoming edges"
                )

    def _contains_cycle(
        self,
        node_map: dict[NodeId, NodeSpec],
        outgoing_edges: dict[NodeId, list[EdgeSpec]],
    ) -> bool:
        visiting: set[NodeId] = set()
        visited: set[NodeId] = set()

        def visit(node_id: NodeId) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False

            visiting.add(node_id)
            for edge in outgoing_edges[node_id]:
                if visit(edge.to_node_id):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in node_map)
