"""Tool registry, adapter routing, and MCP bridge reference implementations."""

from .models import (
    MCPServerDescriptor,
    MCPTransportKind,
    ToolApprovalMode,
    ToolDescriptor,
    ToolInvocationRequest,
    ToolQuery,
    ToolTransportKind,
)
from .observability import ObservedToolInvoker
from .policy import PolicyAwareToolInvoker
from .registry import InMemoryToolRegistry

__all__ = [
    "FunctionToolAdapter",
    "InMemoryMCPGateway",
    "InMemoryToolRegistry",
    "MCPServerDescriptor",
    "MCPToolAdapter",
    "MCPTransportKind",
    "ObservedToolInvoker",
    "PolicyAwareToolInvoker",
    "RoutingToolInvoker",
    "ToolApprovalMode",
    "ToolDescriptor",
    "ToolInvocationRequest",
    "ToolQuery",
    "ToolTransportKind",
]


def __getattr__(name: str):
    if name in {"FunctionToolAdapter", "RoutingToolInvoker"}:
        from .adapters import FunctionToolAdapter, RoutingToolInvoker

        return {
            "FunctionToolAdapter": FunctionToolAdapter,
            "RoutingToolInvoker": RoutingToolInvoker,
        }[name]
    if name == "PolicyAwareToolInvoker":
        from .policy import PolicyAwareToolInvoker

        return PolicyAwareToolInvoker
    if name == "ObservedToolInvoker":
        from .observability import ObservedToolInvoker

        return ObservedToolInvoker
    if name in {"InMemoryMCPGateway", "MCPToolAdapter"}:
        from .mcp import InMemoryMCPGateway, MCPToolAdapter

        return {
            "InMemoryMCPGateway": InMemoryMCPGateway,
            "MCPToolAdapter": MCPToolAdapter,
        }[name]
    raise AttributeError(name)
