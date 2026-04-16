from __future__ import annotations

from typing import Protocol

from core.tools.models import ToolDescriptor, ToolInvocationRequest

from .types import ExecutionContext, ToolInvocationResult


class ToolAdapter(Protocol):
    adapter_ref: str

    def supports(self, descriptor: ToolDescriptor) -> bool: ...

    def invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> ToolInvocationResult: ...
