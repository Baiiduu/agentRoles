from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from core.contracts.tool_invoker import ToolInvoker
from core.contracts.types import ExecutionContext, ToolInvocationResult
from core.events import EventDraft, RuntimeEventEmitter, child_trace_context, trace_context_from_map
from core.state.models import SideEffectKind, SideEffectRecord
from core.tools.models import ToolDescriptor, ToolQuery


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


class ObservedToolInvoker:
    """
    Tool invoker decorator that emits structured observability data.

    At this stage, observability is implemented as stable trace metadata plus a
    persisted `SideEffectRecord` for each tool invocation. This keeps the
    boundary clean: runtime still owns orchestration, while the tool layer owns
    tool-call tracing semantics.
    """

    def __init__(self, delegate: ToolInvoker) -> None:
        self._delegate = delegate

    def invoke(
        self,
        tool_ref: str,
        tool_input: dict[str, object],
        context: ExecutionContext,
    ) -> ToolInvocationResult:
        descriptor = self.get_descriptor(tool_ref)
        started_at = self._now(context)
        tool_trace_context = self._tool_trace_context(context, tool_ref)
        self._emit_tool_event(
            context=context,
            event_type="tool.invocation.started",
            tool_ref=tool_ref,
            descriptor=descriptor,
            trace_context=tool_trace_context,
            payload={"input": deepcopy(tool_input)},
        )
        result = self._delegate.invoke(tool_ref, tool_input, context)
        ended_at = self._now(context)

        trace_metadata = self._trace_metadata(descriptor, started_at, ended_at, tool_trace_context)
        result.metadata = {
            "observability": trace_metadata,
            **result.metadata,
        }
        result.side_effects = [
            self._trace_side_effect(
                descriptor=descriptor,
                tool_ref=tool_ref,
                tool_input=tool_input,
                context=context,
                result=result,
                trace_metadata=trace_metadata,
                created_at=ended_at,
            ),
            *result.side_effects,
        ]
        self._emit_tool_event(
            context=context,
            event_type="tool.invocation.succeeded" if result.success else "tool.invocation.failed",
            tool_ref=tool_ref,
            descriptor=descriptor,
            trace_context=tool_trace_context,
            payload={
                "success": result.success,
                "error_code": result.error_code,
                "error_message": result.error_message,
            },
            metadata={"observability": trace_metadata},
        )
        return result

    def get_descriptor(self, tool_ref: str) -> ToolDescriptor | None:
        return self._delegate.get_descriptor(tool_ref)

    def list_tools(self, query: ToolQuery | None = None) -> list[ToolDescriptor]:
        return self._delegate.list_tools(query)

    def _trace_metadata(
        self,
        descriptor: ToolDescriptor | None,
        started_at: datetime,
        ended_at: datetime,
        trace_context,
    ) -> dict[str, object]:
        duration_ms = max(
            0,
            int((ended_at - started_at).total_seconds() * 1000),
        )
        return {
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_ms": duration_ms,
            "transport_kind": str(descriptor.transport_kind) if descriptor is not None else None,
            "provider_ref": descriptor.provider_ref if descriptor is not None else None,
            "operation_ref": descriptor.operation_ref if descriptor is not None else None,
            "trace_id": trace_context.trace_id,
            "span_id": trace_context.span_id,
            "parent_span_id": trace_context.parent_span_id,
        }

    def _trace_side_effect(
        self,
        *,
        descriptor: ToolDescriptor | None,
        tool_ref: str,
        tool_input: dict[str, object],
        context: ExecutionContext,
        result: ToolInvocationResult,
        trace_metadata: dict[str, object],
        created_at: datetime,
    ) -> SideEffectRecord:
        services = context.services
        side_effect_id = (
            services.id_generator.new("side_effect")
            if services is not None and services.id_generator is not None
            else f"side_effect_{uuid4().hex}"
        )
        return SideEffectRecord(
            side_effect_id=side_effect_id,
            run_id=context.run_record.run_id,
            node_id=context.node_state.node_id,
            kind=descriptor.side_effect_kind if descriptor is not None else SideEffectKind.READ_ONLY,
            target_type="tool",
            target_ref=tool_ref,
            action="invoke",
            args_summary={
                "input": deepcopy(tool_input),
                "transport_kind": trace_metadata["transport_kind"],
                "provider_ref": trace_metadata["provider_ref"],
                "operation_ref": trace_metadata["operation_ref"],
            },
            is_idempotent=descriptor.is_idempotent if descriptor is not None else True,
            succeeded=result.success,
            created_at=created_at,
            metadata={
                "trace": deepcopy(trace_metadata),
                "error_code": result.error_code,
                "error_message": result.error_message,
            },
        )

    def _now(self, context: ExecutionContext) -> datetime:
        services = context.services
        if services is not None and services.clock is not None:
            return services.clock.now()
        return _utcnow()

    def _tool_trace_context(self, context: ExecutionContext, tool_ref: str):
        parent = trace_context_from_map(context.trace_context)
        return child_trace_context(
            parent,
            scope="tool",
            span_id=f"tool:{context.node_state.node_id}:{tool_ref}",
            attributes={
                "tool_ref": tool_ref,
                "node_id": context.node_state.node_id,
            },
        )

    def _emit_tool_event(
        self,
        *,
        context: ExecutionContext,
        event_type: str,
        tool_ref: str,
        descriptor: ToolDescriptor | None,
        trace_context,
        payload: dict[str, object],
        metadata: dict[str, object] | None = None,
    ) -> None:
        services = context.services
        if services is None:
            return
        emitter = RuntimeEventEmitter(
            event_store=services.event_store,
            clock=services.clock or _FallbackClock(),
            id_generator=services.id_generator or _FallbackIdGenerator(),
        )
        emitter.emit_run_events(
            context.run_record.run_id,
            [
                EventDraft(
                    event_type=event_type,
                    thread_id=context.thread_record.thread_id,
                    run_id=context.run_record.run_id,
                    node_id=context.node_state.node_id,
                    actor_type="tool_invoker",
                    actor_ref=tool_ref,
                    payload={
                        **payload,
                        "transport_kind": str(descriptor.transport_kind) if descriptor is not None else None,
                        "provider_ref": descriptor.provider_ref if descriptor is not None else None,
                        "operation_ref": descriptor.operation_ref if descriptor is not None else None,
                    },
                    metadata=dict(metadata or {}),
                    trace_context=trace_context,
                )
            ],
        )
