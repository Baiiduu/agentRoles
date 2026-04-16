from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.state.models import JsonMap, SideEffectKind


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ToolTransportKind(StrEnum):
    LOCAL_FUNCTION = "local_function"
    HTTP_API = "http_api"
    COMMAND = "command"
    DATABASE = "database"
    MCP = "mcp"
    CUSTOM = "custom"


class ToolApprovalMode(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class MCPTransportKind(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
    CUSTOM = "custom"


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


@dataclass
class ToolDescriptor:
    tool_ref: str
    name: str
    description: str
    transport_kind: ToolTransportKind
    input_schema: JsonMap = field(default_factory=dict)
    output_schema: JsonMap = field(default_factory=dict)
    side_effect_kind: SideEffectKind = SideEffectKind.READ_ONLY
    approval_mode: ToolApprovalMode = ToolApprovalMode.NONE
    provider_ref: str | None = None
    operation_ref: str | None = None
    timeout_ms: int | None = None
    is_idempotent: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.tool_ref, "tool_ref")
        _require_non_empty(self.name, "name")
        _require_non_empty(self.description, "description")
        _require_unique(self.tags, "tags")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0 when provided")
        if self.transport_kind == ToolTransportKind.MCP and not self.provider_ref:
            raise ValueError("MCP tools must declare provider_ref")


@dataclass
class ToolInvocationRequest:
    tool_ref: str
    tool_input: JsonMap = field(default_factory=dict)
    caller_node_id: str | None = None
    trace_context: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.tool_ref, "tool_ref")


@dataclass
class ToolQuery:
    tags: list[str] = field(default_factory=list)
    transport_kind: ToolTransportKind | None = None
    side_effect_kind: SideEffectKind | None = None
    approval_mode: ToolApprovalMode | None = None
    provider_ref: str | None = None

    def __post_init__(self) -> None:
        _require_unique(self.tags, "tags")


@dataclass
class MCPServerDescriptor:
    server_ref: str
    transport_kind: MCPTransportKind
    endpoint: str | None = None
    command: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    env_keys: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.server_ref, "server_ref")
        _require_unique(self.env_keys, "env_keys")
