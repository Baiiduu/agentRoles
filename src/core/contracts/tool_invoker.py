from __future__ import annotations

from typing import Protocol

from core.tools.models import ToolDescriptor, ToolQuery

from .types import ExecutionContext, ToolInvocationResult


class ToolInvoker(Protocol):
    def invoke(
        self, tool_ref: str, tool_input: dict[str, object], context: ExecutionContext
    ) -> ToolInvocationResult: ...

    def get_descriptor(self, tool_ref: str) -> ToolDescriptor | None: ...

    def list_tools(self, query: ToolQuery | None = None) -> list[ToolDescriptor]: ...
