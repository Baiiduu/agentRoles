from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from core.contracts import ExecutionContext, NodeExecutionResult, NodeExecutor
from core.state.models import (
    InterruptRecord,
    InterruptStatus,
    InterruptType,
    NodeStatus,
    NodeType,
)
from core.workflow.workflow_models import MergeMode


def _extract_path(value: Any, path: str | None) -> Any:
    if path in (None, ""):
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


class BasicNodeExecutor:
    """
    Reference executor implementation for the minimal control-plane runtime.

    It handles the built-in node types that define generic workflow semantics:
    `noop`, `condition`, `merge`, and `human_gate`. Optional delegate executors
    can be provided for domain-specific node execution.
    """

    def __init__(self, delegates: list[NodeExecutor] | None = None) -> None:
        self._delegates = delegates or []

    def can_execute(self, node_type: NodeType, executor_ref: str) -> bool:
        if self._is_builtin(node_type, executor_ref):
            return True
        return any(delegate.can_execute(node_type, executor_ref) for delegate in self._delegates)

    def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        node_type = context.node_spec.node_type
        if self._is_builtin(node_type, context.node_spec.executor_ref):
            if node_type == NodeType.NOOP:
                return self._execute_noop(context)
            if node_type == NodeType.CONDITION:
                return self._execute_condition(context)
            if node_type == NodeType.MERGE:
                return self._execute_merge(context)
            if node_type == NodeType.HUMAN_GATE:
                return self._execute_human_gate(context)
            raise ValueError(f"unsupported built-in node_type={node_type}")

        for delegate in self._delegates:
            if delegate.can_execute(node_type, context.node_spec.executor_ref):
                return delegate.execute(context)

        raise ValueError(
            f"no executor available for node_type={node_type} "
            f"executor_ref={context.node_spec.executor_ref}"
        )

    def _execute_noop(self, context: ExecutionContext) -> NodeExecutionResult:
        config = context.node_spec.config
        if "output" in config:
            output = deepcopy(config["output"])
        elif config.get("emit_input", True):
            output = deepcopy(context.selected_input)
        else:
            output = {}
        return NodeExecutionResult(status=NodeStatus.SUCCEEDED, output=output)

    def _execute_condition(self, context: ExecutionContext) -> NodeExecutionResult:
        config = context.node_spec.config
        operand_path = config.get("operand_path")
        operator = str(config.get("operator", "truthy"))
        expected = config.get("value")
        actual = _extract_path(context.selected_input, operand_path)
        matched = self._evaluate_condition(actual, operator, expected)

        branches = config.get("branches", {})
        output = {
            "matched": matched,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "selected_branch": branches.get("true" if matched else "false"),
        }
        return NodeExecutionResult(status=NodeStatus.SUCCEEDED, output=output)

    def _execute_merge(self, context: ExecutionContext) -> NodeExecutionResult:
        strategy = context.node_spec.merge_strategy
        if strategy is None:
            raise ValueError("merge node requires merge_strategy")

        snapshot = self._require_snapshot(context)
        incoming_edges = context.workflow.incoming_edges.get(context.node_state.node_id, [])
        items: list[dict[str, Any]] = []
        for edge in incoming_edges:
            upstream_state = snapshot.node_states.get(edge.from_node_id)
            if upstream_state is None or upstream_state.output_artifact_id is None:
                continue
            artifact = snapshot.artifacts.get(upstream_state.output_artifact_id)
            if artifact is None:
                continue
            payload = deepcopy(artifact.payload_inline)
            if payload is None:
                payload = {
                    "payload_ref": artifact.payload_ref,
                    "summary": artifact.summary,
                    "artifact_type": artifact.artifact_type,
                }
            items.append({"node_id": edge.from_node_id, "payload": payload})

        if strategy.mode == MergeMode.COLLECT_LIST:
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={
                    "items": items,
                    "count": len(items),
                },
            )

        if strategy.mode == MergeMode.KEYED_MAP:
            key_field = strategy.key_field
            if not key_field:
                raise ValueError("KEYED_MAP merge requires key_field")
            merged: dict[str, Any] = {}
            for item in items:
                payload = item["payload"]
                key = _extract_path(payload, key_field)
                merged[str(key)] = payload
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={
                    "items_by_key": merged,
                    "count": len(merged),
                },
            )

        if strategy.mode == MergeMode.CUSTOM_REF:
            raise ValueError("CUSTOM_REF merge requires a domain-specific executor")

        raise ValueError(f"unsupported merge mode={strategy.mode}")

    def _execute_human_gate(self, context: ExecutionContext) -> NodeExecutionResult:
        policy = context.node_spec.approval_policy
        if policy is None:
            raise ValueError("human_gate node requires approval_policy")
        if not policy.required:
            return NodeExecutionResult(status=NodeStatus.SUCCEEDED, output={"approved": True})

        resolved = self._latest_resolved_interrupt_for_node(context)
        if resolved is not None:
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={
                    "approved": True,
                    "interrupt_id": resolved.interrupt_id,
                    "resolution": deepcopy(resolved.resolution_payload or {}),
                },
            )

        services = context.services
        interrupt_id = (
            services.id_generator.new("interrupt")
            if services is not None and services.id_generator is not None
            else f"interrupt_{uuid4().hex}"
        )

        interrupt = InterruptRecord(
            interrupt_id=interrupt_id,
            run_id=context.run_record.run_id,
            thread_id=context.thread_record.thread_id,
            node_id=context.node_state.node_id,
            interrupt_type=InterruptType.APPROVAL_REQUIRED,
            reason_code=policy.approval_reason_code,
            reason_message=context.node_spec.config.get(
                "approval_message", "human approval required"
            ),
            payload={
                "approver_type": str(policy.approver_type),
                "node_id": context.node_state.node_id,
                "executor_ref": context.node_spec.executor_ref,
            },
        )
        return NodeExecutionResult(
            status=NodeStatus.WAITING,
            interrupts=[interrupt],
            output={"approval_required": True, "interrupt_id": interrupt.interrupt_id},
        )

    def _latest_resolved_interrupt_for_node(
        self, context: ExecutionContext
    ) -> InterruptRecord | None:
        snapshot = self._require_snapshot(context)
        matches = [
            interrupt
            for interrupt in snapshot.interrupts.values()
            if interrupt.node_id == context.node_state.node_id
            and interrupt.resolution_payload is not None
            and interrupt.status != InterruptStatus.OPEN
        ]
        if not matches:
            return None
        matches.sort(key=lambda item: item.created_at, reverse=True)
        return matches[0]

    def _require_snapshot(self, context: ExecutionContext):
        if context.services is None:
            raise ValueError("basic executor requires RuntimeServices")
        return context.services.state_store.build_snapshot(context.run_record.run_id)

    def _is_builtin(self, node_type: NodeType, executor_ref: str) -> bool:
        if node_type in {NodeType.NOOP, NodeType.CONDITION, NodeType.MERGE, NodeType.HUMAN_GATE}:
            return True
        return executor_ref.startswith("builtin.")

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "truthy":
            return bool(actual)
        if operator == "falsy":
            return not bool(actual)
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "gt":
            return actual > expected
        if operator == "gte":
            return actual >= expected
        if operator == "lt":
            return actual < expected
        if operator == "lte":
            return actual <= expected
        if operator == "in":
            return actual in expected
        if operator == "not_in":
            return actual not in expected
        if operator == "exists":
            return actual is not None
        raise ValueError(f"unsupported condition operator={operator}")
