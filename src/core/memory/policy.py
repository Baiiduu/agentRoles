from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from core.contracts import ExecutionContext, MemoryProvider
from core.state.models import PolicyAction, SideEffectKind, SideEffectRecord

from .errors import MemoryPolicyError


class PolicyAwareMemoryProvider:
    """
    Memory provider decorator that applies policy checks through the generic
    `pre_side_effect` hook.

    Memory operations are treated as structured side effects so the governance
    layer can reason about them without hard-coding memory-specific rules into
    runtime.
    """

    def __init__(self, delegate: MemoryProvider) -> None:
        self._delegate = delegate

    def retrieve(
        self,
        query: str,
        scope: str,
        *,
        top_k: int = 5,
        context: ExecutionContext | None = None,
    ):
        decision = self._precheck(
            operation="retrieve",
            scope=scope,
            kind=SideEffectKind.READ_ONLY,
            args_summary={"query": query, "top_k": top_k},
            context=context,
        )
        if decision.action == PolicyAction.REDACT and decision.redactions:
            query = self._redact_query(query, decision.redactions)
        return self._delegate.retrieve(query, scope, top_k=top_k, context=context)

    def write(
        self,
        memory_item: dict[str, object],
        *,
        context: ExecutionContext | None = None,
    ) -> str:
        scope = str(memory_item.get("scope") or "")
        decision = self._precheck(
            operation="write",
            scope=scope,
            kind=SideEffectKind.LOCAL_WRITE,
            args_summary={"memory_item": deepcopy(memory_item)},
            context=context,
        )
        effective_item = deepcopy(memory_item)
        if decision.action == PolicyAction.REDACT and decision.redactions:
            for path in decision.redactions:
                self._redact_path(effective_item, path)
        return self._delegate.write(effective_item, context=context)

    def summarize(
        self,
        scope: str,
        *,
        context: ExecutionContext | None = None,
    ) -> dict[str, object]:
        self._precheck(
            operation="summarize",
            scope=scope,
            kind=SideEffectKind.READ_ONLY,
            args_summary={},
            context=context,
        )
        return self._delegate.summarize(scope, context=context)

    def _precheck(
        self,
        *,
        operation: str,
        scope: str,
        kind: SideEffectKind,
        args_summary: dict[str, object],
        context: ExecutionContext | None,
    ):
        if context is None or context.services is None or context.services.policy_engine is None:
            return _allow_decision()

        services = context.services
        side_effect_id = (
            services.id_generator.new("side_effect")
            if services.id_generator is not None
            else f"side_effect_{uuid4().hex}"
        )
        decision = services.policy_engine.pre_side_effect(
            context,
            SideEffectRecord(
                side_effect_id=side_effect_id,
                run_id=context.run_record.run_id,
                node_id=context.node_state.node_id,
                kind=kind,
                target_type="memory",
                target_ref=scope,
                action=operation,
                args_summary=args_summary,
                is_idempotent=(operation != "write"),
                succeeded=False,
            ),
        )
        if decision.action in {PolicyAction.ALLOW, PolicyAction.REDACT}:
            return decision
        raise MemoryPolicyError(operation=operation, scope=scope, decision=decision)

    def _redact_query(self, query: str, paths: list[str]) -> str:
        if "query" in paths or "*" in paths:
            return ""
        return query

    def _redact_path(self, payload: dict[str, object], path: str) -> None:
        if not path:
            return
        parts = path.split(".")
        current: object = payload
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return
            current = current[part]
        if isinstance(current, dict):
            current.pop(parts[-1], None)


class _AllowDecision:
    action = PolicyAction.ALLOW
    redactions: list[str] = []


def _allow_decision():
    return _AllowDecision()
