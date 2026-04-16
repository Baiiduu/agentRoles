from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from core.contracts import ExecutionContext, MemoryProvider
from core.events import EventDraft, RuntimeEventEmitter, child_trace_context, trace_context_from_map


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _FallbackClock:
    def now(self) -> datetime:
        return _utcnow()


class _FallbackIdGenerator:
    def new(self, prefix: str | None = None) -> str:
        base = uuid4().hex
        if prefix:
            return f"{prefix}_{base}"
        return base


class ObservedMemoryProvider:
    """
    Emits structured runtime events for memory operations.

    Unlike the tool layer, memory operations currently return plain contract
    values, so observability is represented as runtime events rather than
    reducer-managed side-effect records.
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
        started_at = self._now(context)
        trace_context = self._memory_trace_context(context, scope, "retrieve")
        self._emit(
            context=context,
            operation="retrieve",
            phase="started",
            scope=scope,
            trace_context=trace_context,
            payload={"query": query, "top_k": top_k},
        )
        try:
            results = self._delegate.retrieve(query, scope, top_k=top_k, context=context)
        except Exception as exc:
            self._emit(
                context=context,
                operation="retrieve",
                phase="failed",
                scope=scope,
                trace_context=trace_context,
                payload={"query": query, "top_k": top_k},
                metadata=self._metadata(started_at, self._now(context), error_message=str(exc)),
            )
            raise
        self._emit(
            context=context,
            operation="retrieve",
            phase="succeeded",
            scope=scope,
            trace_context=trace_context,
            payload={"query": query, "top_k": top_k, "result_count": len(results)},
            metadata=self._metadata(started_at, self._now(context), result_count=len(results)),
        )
        return results

    def write(
        self,
        memory_item: dict[str, object],
        *,
        context: ExecutionContext | None = None,
    ) -> str:
        scope = str(memory_item.get("scope") or "")
        started_at = self._now(context)
        trace_context = self._memory_trace_context(context, scope, "write")
        self._emit(
            context=context,
            operation="write",
            phase="started",
            scope=scope,
            trace_context=trace_context,
            payload={"memory_item": deepcopy(memory_item)},
        )
        try:
            memory_id = self._delegate.write(memory_item, context=context)
        except Exception as exc:
            self._emit(
                context=context,
                operation="write",
                phase="failed",
                scope=scope,
                trace_context=trace_context,
                payload={"memory_item": deepcopy(memory_item)},
                metadata=self._metadata(started_at, self._now(context), error_message=str(exc)),
            )
            raise
        self._emit(
            context=context,
            operation="write",
            phase="succeeded",
            scope=scope,
            trace_context=trace_context,
            payload={"memory_id": memory_id},
            metadata=self._metadata(started_at, self._now(context), memory_id=memory_id),
        )
        return memory_id

    def summarize(
        self,
        scope: str,
        *,
        context: ExecutionContext | None = None,
    ) -> dict[str, object]:
        started_at = self._now(context)
        trace_context = self._memory_trace_context(context, scope, "summarize")
        self._emit(
            context=context,
            operation="summarize",
            phase="started",
            scope=scope,
            trace_context=trace_context,
            payload={},
        )
        try:
            summary = self._delegate.summarize(scope, context=context)
        except Exception as exc:
            self._emit(
                context=context,
                operation="summarize",
                phase="failed",
                scope=scope,
                trace_context=trace_context,
                payload={},
                metadata=self._metadata(started_at, self._now(context), error_message=str(exc)),
            )
            raise
        self._emit(
            context=context,
            operation="summarize",
            phase="succeeded",
            scope=scope,
            trace_context=trace_context,
            payload={"total_items": summary.get("total_items")},
            metadata=self._metadata(
                started_at,
                self._now(context),
                total_items=summary.get("total_items"),
            ),
        )
        return summary

    def _emit(
        self,
        *,
        context: ExecutionContext | None,
        operation: str,
        phase: str,
        scope: str,
        trace_context,
        payload: dict[str, object],
        metadata: dict[str, object] | None = None,
    ) -> None:
        if context is None or context.services is None:
            return
        services = context.services
        emitter = RuntimeEventEmitter(
            event_store=services.event_store,
            clock=services.clock or _FallbackClock(),
            id_generator=services.id_generator or _FallbackIdGenerator(),
        )
        emitter.emit_run_events(
            context.run_record.run_id,
            [
                EventDraft(
                    event_type=f"memory.{operation}.{phase}",
                    thread_id=context.thread_record.thread_id,
                    run_id=context.run_record.run_id,
                    node_id=context.node_state.node_id,
                    actor_type="memory_provider",
                    actor_ref=scope,
                    payload={"scope": scope, **payload},
                    metadata=dict(metadata or {}),
                    trace_context=trace_context,
                )
            ],
        )

    def _memory_trace_context(
        self,
        context: ExecutionContext | None,
        scope: str,
        operation: str,
    ):
        if context is None:
            return None
        parent = trace_context_from_map(context.trace_context)
        return child_trace_context(
            parent,
            scope="memory",
            span_id=f"memory:{context.node_state.node_id}:{operation}:{scope}",
            attributes={
                "scope": scope,
                "operation": operation,
                "node_id": context.node_state.node_id,
            },
        )

    def _metadata(
        self,
        started_at: datetime,
        ended_at: datetime,
        **extra: object,
    ) -> dict[str, object]:
        return {
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_ms": max(0, int((ended_at - started_at).total_seconds() * 1000)),
            **extra,
        }

    def _now(self, context: ExecutionContext | None) -> datetime:
        if context is not None and context.services is not None and context.services.clock is not None:
            return context.services.clock.now()
        return _utcnow()
