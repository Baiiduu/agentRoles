from __future__ import annotations

from typing import Protocol

from core.tools.models import ToolDescriptor, ToolQuery


class ToolRegistry(Protocol):
    def register(self, descriptor: ToolDescriptor) -> None: ...

    def get(self, tool_ref: str) -> ToolDescriptor | None: ...

    def list(self, query: ToolQuery | None = None) -> list[ToolDescriptor]: ...
