from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from uuid import uuid4

from core.contracts import ExecutionContext, ToolInvocationResult
from core.state.models import SideEffectKind, SideEffectRecord
from core.tools import InMemoryMCPGateway, MCPToolAdapter
from core.tools.models import MCPServerDescriptor, MCPTransportKind, ToolDescriptor, ToolTransportKind

from .external_mcp_client_service import ExternalMCPClientService

_FILESYSTEM_TOOL_DESCRIPTIONS = {
    "fs.list_dir": "List files and directories inside the agent workspace.",
    "fs.read_file": "Read a text file from the agent workspace.",
    "fs.write_file": "Write or overwrite a text file inside the agent workspace.",
    "fs.make_dir": "Create a directory inside the agent workspace.",
    "fs.search_files": "Search for files inside the agent workspace.",
    "fs.delete_file": "Delete a file inside the agent workspace.",
}


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    sanitized = re.sub(r"[^a-z0-9]+", "_", lowered)
    return sanitized.strip("_") or "tool"


def build_mcp_tool_ref(server_ref: str, operation_ref: str) -> str:
    return f"mcp.{_slug(server_ref)}.{_slug(operation_ref)}"


def mcp_tool_summary(server_payload: dict[str, object], operation_ref: str) -> dict[str, object]:
    server_ref = str(server_payload.get("server_ref", "")).strip()
    tool_ref = build_mcp_tool_ref(server_ref, operation_ref)
    return {
        "tool_ref": tool_ref,
        "operation_ref": operation_ref,
        "server_ref": server_ref,
        "server_name": str(server_payload.get("name", server_ref)).strip() or server_ref,
        "display_name": f"{server_ref}.{operation_ref}",
        "description": _FILESYSTEM_TOOL_DESCRIPTIONS.get(operation_ref, operation_ref),
        "connection_mode": str(server_payload.get("connection_mode", "internal")),
        "transport_kind": str(server_payload.get("transport_kind", "custom")),
        "tags": ["mcp", _slug(server_ref)],
    }


def build_mcp_server_catalog(registered_servers: list[dict[str, object]]) -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for server in registered_servers:
        if not bool(server.get("enabled", True)):
            continue
        server_ref = str(server.get("server_ref", "")).strip()
        if not server_ref:
            continue
        tool_names = [
            str(item)
            for item in (server.get("tool_refs") or [])
            if str(item).strip()
        ]
        tools = [mcp_tool_summary(server, tool_name) for tool_name in tool_names]
        catalog.append(
            {
                "server_ref": server_ref,
                "name": str(server.get("name", server_ref)).strip() or server_ref,
                "description": str(server.get("description", "")).strip(),
                "connection_mode": str(server.get("connection_mode", "internal")),
                "transport_kind": str(server.get("transport_kind", "custom")),
                "tool_count": len(tools),
                "tools": tools,
            }
        )
    return catalog


def _new_side_effect_id() -> str:
    return f"side_effect_{uuid4().hex}"


def _workspace_root_from_context(context: ExecutionContext | None) -> Path:
    runtime_context = {}
    if context is not None and context.agent_binding is not None:
        value = context.agent_binding.metadata.get("runtime_resource_context")
        if isinstance(value, dict):
            runtime_context = value
    workspace = runtime_context.get("workspace")
    if not isinstance(workspace, dict):
        raise ValueError("workspace is not available for this agent")
    if not workspace.get("enabled"):
        raise ValueError("workspace is disabled for this agent")
    absolute_path = workspace.get("absolute_path")
    if not isinstance(absolute_path, str) or not absolute_path.strip():
        raise ValueError("workspace absolute_path is missing")
    root = Path(absolute_path).resolve()
    if not root.exists():
        raise ValueError("workspace directory does not exist")
    return root


def _resolve_workspace_path(context: ExecutionContext | None, requested_path: str | None) -> Path:
    root = _workspace_root_from_context(context)
    relative = (requested_path or ".").strip() or "."
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("requested path must stay within the agent workspace")
    return candidate


def _side_effect(
    context: ExecutionContext | None,
    *,
    kind: SideEffectKind,
    action: str,
    target_type: str,
    target_ref: str,
    payload: dict[str, object],
) -> SideEffectRecord:
    run_id = context.run_record.run_id if context is not None else "standalone"
    node_id = context.node_state.node_id if context is not None else "mcp"
    return SideEffectRecord(
        side_effect_id=_new_side_effect_id(),
        run_id=run_id,
        node_id=node_id,
        kind=kind,
        target_type=target_type,
        target_ref=target_ref,
        action=action,
        args_summary=deepcopy(payload),
        is_idempotent=False,
        succeeded=True,
    )


def _handle_fs_list_dir(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    target = _resolve_workspace_path(context, str(arguments.get("path", ".")))
    if not target.exists():
        raise ValueError("target directory does not exist")
    if not target.is_dir():
        raise ValueError("target path is not a directory")
    items = []
    for item in sorted(target.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        items.append(
            {
                "name": item.name,
                "path": str(item.relative_to(_workspace_root_from_context(context))),
                "kind": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(target.relative_to(_workspace_root_from_context(context))),
            "items": items,
            "count": len(items),
        },
    )


def _handle_fs_read_file(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    target = _resolve_workspace_path(context, str(arguments.get("path", "")))
    if not target.exists():
        raise ValueError("file does not exist")
    if not target.is_file():
        raise ValueError("target path is not a file")
    content = target.read_text(encoding="utf-8")
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(target.relative_to(_workspace_root_from_context(context))),
            "content": content,
            "size": len(content),
        },
    )


def _handle_fs_write_file(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    target = _resolve_workspace_path(context, str(arguments.get("path", "")))
    content = str(arguments.get("content", ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(target.relative_to(_workspace_root_from_context(context))),
            "bytes_written": len(content.encode("utf-8")),
        },
        side_effects=[
            _side_effect(
                context,
                kind=SideEffectKind.LOCAL_WRITE,
                action="write_file",
                target_type="filesystem",
                target_ref=str(target),
                payload={"path": str(target)},
            )
        ],
    )


def _handle_fs_make_dir(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    target = _resolve_workspace_path(context, str(arguments.get("path", "")))
    target.mkdir(parents=True, exist_ok=True)
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(target.relative_to(_workspace_root_from_context(context))),
            "created": True,
        },
        side_effects=[
            _side_effect(
                context,
                kind=SideEffectKind.LOCAL_WRITE,
                action="make_dir",
                target_type="filesystem",
                target_ref=str(target),
                payload={"path": str(target)},
            )
        ],
    )


def _handle_fs_search_files(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    root = _resolve_workspace_path(context, str(arguments.get("path", ".")))
    pattern = str(arguments.get("pattern", "*")).strip() or "*"
    query = str(arguments.get("query", "")).strip()
    matches = []
    for item in root.rglob(pattern):
        if not item.is_file():
            continue
        if query:
            try:
                content = item.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if query not in content:
                continue
        matches.append(
            {
                "path": str(item.relative_to(_workspace_root_from_context(context))),
                "name": item.name,
            }
        )
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(root.relative_to(_workspace_root_from_context(context))),
            "pattern": pattern,
            "query": query,
            "matches": matches,
            "count": len(matches),
        },
    )


def _handle_fs_delete_file(arguments: dict[str, object], context: ExecutionContext | None) -> ToolInvocationResult:
    target = _resolve_workspace_path(context, str(arguments.get("path", "")))
    if not target.exists():
        raise ValueError("file does not exist")
    if not target.is_file():
        raise ValueError("target path is not a file")
    target.unlink()
    return ToolInvocationResult(
        success=True,
        output={
            "path": str(target.relative_to(_workspace_root_from_context(context))),
            "deleted": True,
        },
        side_effects=[
            _side_effect(
                context,
                kind=SideEffectKind.LOCAL_WRITE,
                action="delete_file",
                target_type="filesystem",
                target_ref=str(target),
                payload={"path": str(target)},
            )
        ],
    )


_FILESYSTEM_HANDLERS = {
    "fs.list_dir": _handle_fs_list_dir,
    "fs.read_file": _handle_fs_read_file,
    "fs.write_file": _handle_fs_write_file,
    "fs.make_dir": _handle_fs_make_dir,
    "fs.search_files": _handle_fs_search_files,
    "fs.delete_file": _handle_fs_delete_file,
}


def _looks_like_workspace_filesystem_server(server_payload: dict[str, object]) -> bool:
    server_ref = str(server_payload.get("server_ref", ""))
    tool_refs = [str(item) for item in (server_payload.get("tool_refs") or [])]
    return server_ref == "filesystem.workspace" or any(ref.startswith("fs.") for ref in tool_refs)


def _tool_descriptor(server_payload: dict[str, object], operation_ref: str) -> ToolDescriptor:
    server_ref = str(server_payload.get("server_ref", "")).strip()
    tool_ref = build_mcp_tool_ref(server_ref, operation_ref)
    side_effect_kind = (
        SideEffectKind.LOCAL_WRITE
        if operation_ref in {"fs.write_file", "fs.make_dir", "fs.delete_file"}
        else SideEffectKind.READ_ONLY
    )
    return ToolDescriptor(
        tool_ref=tool_ref,
        name=f"{server_ref}.{operation_ref}",
        description=_FILESYSTEM_TOOL_DESCRIPTIONS.get(operation_ref, operation_ref),
        transport_kind=ToolTransportKind.MCP,
        provider_ref=server_ref,
        operation_ref=operation_ref,
        side_effect_kind=side_effect_kind,
        tags=["mcp", _slug(server_ref)],
        metadata={
            "tool_origin": "mcp",
            "mcp_server_ref": server_ref,
            "mcp_tool_name": operation_ref,
            "display_name": f"{server_ref}.{operation_ref}",
        },
    )


class MCPRuntimeFactory:
    def __init__(self) -> None:
        self._external_client = ExternalMCPClientService()

    def build(
        self,
        *,
        registered_servers: list[dict[str, object]],
    ) -> tuple[list[ToolDescriptor], MCPToolAdapter]:
        gateway = InMemoryMCPGateway()
        descriptors: list[ToolDescriptor] = []
        for server in registered_servers:
            if not bool(server.get("enabled", True)):
                continue
            server_ref = str(server.get("server_ref", "")).strip()
            if not server_ref:
                continue
            gateway.register_server(
                MCPServerDescriptor(
                    server_ref=server_ref,
                    transport_kind=MCPTransportKind.CUSTOM,
                    metadata={"display_name": server.get("name", server_ref)},
                )
            )
            tool_refs = [str(item) for item in (server.get("tool_refs") or []) if str(item).strip()]
            for tool_ref in tool_refs:
                descriptor = _tool_descriptor(server, tool_ref)
                gateway.register_tool(descriptor)
                descriptors.append(descriptor)
                if str(server.get("connection_mode", "internal")) == "external":
                    gateway.register_handler(
                        server_ref,
                        tool_ref,
                        self._external_handler(server_ref, tool_ref, server),
                    )
                elif _looks_like_workspace_filesystem_server(server) and tool_ref in _FILESYSTEM_HANDLERS:
                    gateway.register_handler(server_ref, tool_ref, _FILESYSTEM_HANDLERS[tool_ref])
        return descriptors, MCPToolAdapter(gateway)

    def _external_handler(
        self,
        server_ref: str,
        tool_ref: str,
        server_payload: dict[str, object],
    ):
        def handler(arguments: dict[str, object], context: ExecutionContext | None):
            workspace = {}
            if context is not None and context.agent_binding is not None:
                runtime_context = context.agent_binding.metadata.get("runtime_resource_context")
                if isinstance(runtime_context, dict):
                    workspace = deepcopy(runtime_context.get("workspace") or {})
            result = self._external_client.call_tool(
                RegisteredMCPServerLike.from_payload(server_payload),
                tool_name=tool_ref,
                arguments=arguments,
                workspace=workspace,
            )
            return result

        return handler


class RegisteredMCPServerLike:
    def __init__(self, payload: dict[str, object]) -> None:
        self.server_ref = str(payload.get("server_ref", ""))
        self.connection_mode = str(payload.get("connection_mode", "internal"))
        self.transport_kind = str(payload.get("transport_kind", "custom"))
        self.command = str(payload.get("command", ""))
        self.args = [str(item) for item in (payload.get("args") or [])]
        self.endpoint = str(payload.get("endpoint", ""))
        self.env = {str(key): str(value) for key, value in (payload.get("env") or {}).items()}
        self.cwd = str(payload.get("cwd", ""))

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "RegisteredMCPServerLike":
        return cls(payload)
