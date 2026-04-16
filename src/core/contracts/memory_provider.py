from __future__ import annotations

from typing import Protocol

from .types import ExecutionContext, MemoryResult


class MemoryProvider(Protocol):
    def retrieve(
        self,
        query: str,
        scope: str,
        *,
        top_k: int = 5,
        context: ExecutionContext | None = None,
    ) -> list[MemoryResult]: ...

    def write(
        self,
        memory_item: dict[str, object],
        *,
        context: ExecutionContext | None = None,
    ) -> str: ...

    def summarize(
        self,
        scope: str,
        *,
        context: ExecutionContext | None = None,
    ) -> dict[str, object]: ...
