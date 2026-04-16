from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from core.state.models import JsonMap


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MemoryScopeKind(StrEnum):
    THREAD = "thread"
    TASK = "task"
    LONG_TERM = "long_term"
    DOMAIN = "domain"
    CUSTOM = "custom"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


@dataclass
class MemoryRecord:
    memory_id: str
    scope: str
    content: str | None = None
    payload: JsonMap = field(default_factory=dict)
    source_ref: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.memory_id, "memory_id")
        _require_non_empty(self.scope, "scope")
        _require_unique(self.tags, "tags")
        if not self.content and not self.payload:
            raise ValueError("memory record must define content or payload")


@dataclass
class MemorySummary:
    scope: str
    total_items: int
    latest_updated_at: datetime | None = None
    tag_counts: dict[str, int] = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.scope, "scope")
        if self.total_items < 0:
            raise ValueError("total_items must be >= 0")
