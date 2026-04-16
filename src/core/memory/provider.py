from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from core.contracts import ExecutionContext, MemoryResult

from .models import MemoryRecord, MemorySummary


def _utcnow() -> datetime:
    return datetime.now(UTC)


class InMemoryMemoryProvider:
    """
    Reference in-memory memory service.

    It keeps scope semantics explicit while staying domain-neutral. The provider
    is intentionally simple: exact scope isolation, lexical retrieval, and
    summary generation suitable for local development and tests.
    """

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def retrieve(
        self,
        query: str,
        scope: str,
        *,
        top_k: int = 5,
        context: ExecutionContext | None = None,
    ) -> list[MemoryResult]:
        if not scope:
            raise ValueError("scope must be non-empty")
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        scored: list[tuple[float, MemoryRecord]] = []
        for record in self._iter_scope(scope):
            score = self._score_record(record, query)
            if score <= 0 and query.strip():
                continue
            scored.append((score, record))

        scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        return [
            MemoryResult(
                memory_id=record.memory_id,
                scope=record.scope,
                score=score,
                payload={
                    **deepcopy(record.payload),
                    "content": record.content,
                    "tags": list(record.tags),
                },
                source_ref=record.source_ref,
                metadata={
                    **deepcopy(record.metadata),
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                },
            )
            for score, record in scored[:top_k]
        ]

    def write(
        self,
        memory_item: dict[str, object],
        *,
        context: ExecutionContext | None = None,
    ) -> str:
        return self._write(memory_item)

    def summarize(
        self,
        scope: str,
        *,
        context: ExecutionContext | None = None,
    ) -> dict[str, object]:
        summary = self.build_summary(scope)
        return {
            "scope": summary.scope,
            "total_items": summary.total_items,
            "latest_updated_at": (
                summary.latest_updated_at.isoformat()
                if summary.latest_updated_at is not None
                else None
            ),
            "tag_counts": dict(summary.tag_counts),
            "metadata": deepcopy(summary.metadata),
        }

    def _write(self, memory_item: dict[str, object]) -> str:
        scope = str(memory_item.get("scope") or "").strip()
        if not scope:
            raise ValueError("memory_item.scope must be non-empty")

        content_value = memory_item.get("content")
        content = str(content_value).strip() if content_value is not None else None
        payload_value = memory_item.get("payload", {})
        payload = deepcopy(payload_value)
        if not isinstance(payload, dict):
            raise ValueError("memory_item.payload must be a dict when provided")
        raw_tags = memory_item.get("tags") or []
        if isinstance(raw_tags, str):
            raise ValueError("memory_item.tags must be a list of strings, not a string")
        tags = list(raw_tags)
        if any(not isinstance(tag, str) or not tag for tag in tags):
            raise ValueError("memory_item.tags must contain only non-empty strings")

        memory_id = str(memory_item.get("memory_id") or f"memory_{uuid4().hex}")
        record = self._records.get(memory_id)
        now = _utcnow()
        if record is None:
            record = MemoryRecord(
                memory_id=memory_id,
                scope=scope,
                content=content,
                payload=payload,
                source_ref=_optional_str(memory_item.get("source_ref")),
                tags=tags,
                created_at=now,
                updated_at=now,
                metadata=deepcopy(memory_item.get("metadata") or {}),
            )
        else:
            record.scope = scope
            record.content = content
            record.payload = payload
            record.source_ref = _optional_str(memory_item.get("source_ref"))
            record.tags = tags
            record.updated_at = now
            record.metadata = deepcopy(memory_item.get("metadata") or {})
            record.__post_init__()

        self._records[memory_id] = deepcopy(record)
        return memory_id

    def get_record(self, memory_id: str) -> MemoryRecord | None:
        record = self._records.get(memory_id)
        return deepcopy(record) if record is not None else None

    def list_records(self, scope: str | None = None) -> list[MemoryRecord]:
        records = list(self._records.values())
        if scope is not None:
            records = [record for record in records if record.scope == scope]
        return sorted(
            (deepcopy(record) for record in records),
            key=lambda record: (record.scope, record.updated_at, record.memory_id),
        )

    def build_summary(self, scope: str) -> MemorySummary:
        records = self._iter_scope(scope)
        latest = max((record.updated_at for record in records), default=None)
        tag_counts: dict[str, int] = {}
        for record in records:
            for tag in record.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return MemorySummary(
            scope=scope,
            total_items=len(records),
            latest_updated_at=latest,
            tag_counts=tag_counts,
            metadata={"record_ids": [record.memory_id for record in records]},
        )

    def _iter_scope(self, scope: str) -> list[MemoryRecord]:
        return [deepcopy(record) for record in self._records.values() if record.scope == scope]

    def _score_record(self, record: MemoryRecord, query: str) -> float:
        if not query.strip():
            return 1.0
        now = _utcnow()
        haystack = " ".join(
            [
                record.content or "",
                " ".join(record.tags),
                _flatten_payload(record.payload),
                record.source_ref or "",
            ]
        ).lower()
        query_terms = [term for term in query.lower().split() if term]
        if not query_terms:
            return 1.0
        matches = sum(1 for term in query_terms if term in haystack)
        if matches == 0:
            return 0.0
        density = matches / len(query_terms)
        age_hours = max(0.0, (now - record.updated_at).total_seconds() / 3600.0)
        freshness = min(1.0, age_hours)
        return round(density + (1.0 / (1.0 + freshness)), 6)


def _flatten_payload(payload: dict[str, object]) -> str:
    values: list[str] = []
    for value in payload.values():
        if isinstance(value, dict):
            values.append(_flatten_payload(value))
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
