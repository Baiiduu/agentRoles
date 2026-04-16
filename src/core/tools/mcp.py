from __future__ import annotations

from copy import deepcopy
from typing import Callable

from core.contracts.mcp_gateway import MCPGateway
from core.contracts.types import ExecutionContext, ToolInvocationResult
from core.state.models import JsonMap
from core.tools.models import (
    MCPServerDescriptor,
    ToolDescriptor,
    ToolInvocationRequest,
    ToolTransportKind,
)


MCPHandler = Callable[[JsonMap, ExecutionContext | None], ToolInvocationResult | JsonMap | None]


class InMemoryMCPGateway:
    """
    Reference MCP gateway used to keep the interface stable before real MCP
    transports are added.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerDescriptor] = {}
        self._server_tools: dict[str, dict[str, ToolDescriptor]] = {}
        self._handlers: dict[tuple[str, str], MCPHandler] = {}

    def register_server(self, descriptor: MCPServerDescriptor) -> None:
        if descriptor.server_ref in self._servers:
            raise ValueError(f"MCP server '{descriptor.server_ref}' is already registered")
        self._servers[descriptor.server_ref] = deepcopy(descriptor)
        self._server_tools[descriptor.server_ref] = {}

    def list_servers(self) -> list[MCPServerDescriptor]:
        return [deepcopy(self._servers[key]) for key in sorted(self._servers)]

    def register_tool(self, descriptor: ToolDescriptor) -> None:
        if descriptor.transport_kind != ToolTransportKind.MCP:
            raise ValueError("only MCP tools can be registered in an MCP gateway")
        if descriptor.provider_ref is None:
            raise ValueError("MCP tools must declare provider_ref")
        if descriptor.provider_ref not in self._servers:
            raise ValueError(f"unknown MCP server '{descriptor.provider_ref}'")
        tool_name = descriptor.operation_ref or descriptor.tool_ref
        server_tools = self._server_tools[descriptor.provider_ref]
        if tool_name in server_tools:
            raise ValueError(
                f"MCP tool '{tool_name}' is already registered for server "
                f"'{descriptor.provider_ref}'"
            )
        server_tools[tool_name] = deepcopy(descriptor)

    def register_handler(self, server_ref: str, tool_name: str, handler: MCPHandler) -> None:
        if server_ref not in self._servers:
            raise ValueError(f"unknown MCP server '{server_ref}'")
        key = (server_ref, tool_name)
        if key in self._handlers:
            raise ValueError(f"MCP handler '{server_ref}:{tool_name}' is already registered")
        self._handlers[key] = handler

    def list_tools(self, server_ref: str) -> list[ToolDescriptor]:
        if server_ref not in self._server_tools:
            raise ValueError(f"unknown MCP server '{server_ref}'")
        tools = self._server_tools[server_ref]
        return [deepcopy(tools[key]) for key in sorted(tools)]

    def invoke_tool(
        self,
        server_ref: str,
        tool_name: str,
        arguments: JsonMap,
        context: ExecutionContext | None = None,
    ) -> ToolInvocationResult:
        key = (server_ref, tool_name)
        handler = self._handlers.get(key)
        if handler is None:
            return ToolInvocationResult(
                success=False,
                error_code="MCP_TOOL_HANDLER_NOT_FOUND",
                error_message=f"no MCP handler registered for '{server_ref}:{tool_name}'",
                metadata={"server_ref": server_ref, "tool_name": tool_name},
            )
        try:
            raw_result = handler(deepcopy(arguments), context)
        except Exception as exc:  # noqa: BLE001 - normalized into tool result.
            return ToolInvocationResult(
                success=False,
                error_code="MCP_TOOL_EXECUTION_ERROR",
                error_message=str(exc),
                metadata={"server_ref": server_ref, "tool_name": tool_name},
            )

        if isinstance(raw_result, ToolInvocationResult):
            result = deepcopy(raw_result)
        elif raw_result is None:
            result = ToolInvocationResult(success=True, output={})
        elif isinstance(raw_result, dict):
            result = ToolInvocationResult(success=True, output=deepcopy(raw_result))
        else:
            result = ToolInvocationResult(success=True, output={"value": raw_result})

        result.metadata = {
            "server_ref": server_ref,
            "tool_name": tool_name,
            **result.metadata,
        }
        return result


class MCPToolAdapter:
    adapter_ref = "adapter.mcp"

    def __init__(self, gateway: MCPGateway) -> None:
        self._gateway = gateway

    def supports(self, descriptor: ToolDescriptor) -> bool:
        return descriptor.transport_kind == ToolTransportKind.MCP and descriptor.provider_ref is not None

    def invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> ToolInvocationResult:
        if descriptor.provider_ref is None:
            return ToolInvocationResult(
                success=False,
                error_code="MCP_SERVER_REF_MISSING",
                error_message=f"MCP tool '{descriptor.tool_ref}' is missing provider_ref",
                metadata={"adapter_ref": self.adapter_ref},
            )
        tool_name = descriptor.operation_ref or descriptor.tool_ref
        result = self._gateway.invoke_tool(
            descriptor.provider_ref,
            tool_name,
            deepcopy(request.tool_input),
            context,
        )
        result.metadata = {
            "adapter_ref": self.adapter_ref,
            "server_ref": descriptor.provider_ref,
            "tool_name": tool_name,
            **result.metadata,
        }
        return result
