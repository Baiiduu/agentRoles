from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from core.state.models import JsonMap


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    scope: str | None = None
    attributes: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise ValueError("trace_id must be non-empty")
        if not self.span_id:
            raise ValueError("span_id must be non-empty")

    def to_map(self) -> JsonMap:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "scope": self.scope,
            "attributes": dict(self.attributes),
        }


def root_trace_context(trace_id: str, *, scope: str | None = None) -> TraceContext:
    return TraceContext(trace_id=trace_id, span_id=f"root:{trace_id}", scope=scope)


def child_trace_context(
    parent: TraceContext | None,
    *,
    scope: str | None = None,
    span_id: str | None = None,
    attributes: JsonMap | None = None,
) -> TraceContext:
    if parent is None:
        trace_id = uuid4().hex
        return TraceContext(
            trace_id=trace_id,
            span_id=span_id or f"span:{uuid4().hex}",
            scope=scope,
            attributes=dict(attributes or {}),
        )
    return TraceContext(
        trace_id=parent.trace_id,
        span_id=span_id or f"span:{uuid4().hex}",
        parent_span_id=parent.span_id,
        scope=scope,
        attributes=dict(attributes or {}),
    )


def trace_context_from_map(value: JsonMap | None) -> TraceContext | None:
    if not value:
        return None
    trace_id = value.get("trace_id")
    span_id = value.get("span_id")
    if not isinstance(trace_id, str) or not isinstance(span_id, str):
        return None
    parent_span_id = value.get("parent_span_id")
    scope = value.get("scope")
    attributes = value.get("attributes")
    return TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id if isinstance(parent_span_id, str) else None,
        scope=scope if isinstance(scope, str) else None,
        attributes=dict(attributes or {}) if isinstance(attributes, dict) else {},
    )
