from __future__ import annotations

from typing import Protocol

from core.state.models import JsonMap
from core.tools.models import MCPServerDescriptor, ToolDescriptor

from .types import ExecutionContext, ToolInvocationResult


class MCPGateway(Protocol):
    def register_server(self, descriptor: MCPServerDescriptor) -> None: ...

    def list_servers(self) -> list[MCPServerDescriptor]: ...

    def list_tools(self, server_ref: str) -> list[ToolDescriptor]: ...

    def invoke_tool(
        self,
        server_ref: str,
        tool_name: str,
        arguments: JsonMap,
        context: ExecutionContext | None = None,
    ) -> ToolInvocationResult: ...
