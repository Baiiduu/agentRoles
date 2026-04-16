from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from typing import Any
import os
from contextlib import asynccontextmanager

import anyio
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from core.resource_registry import RegisteredMCPServer
from .mcp_auth_service import MCPAuthService


def _unwrap_exception(exc: BaseException) -> BaseException:
    current = exc
    while hasattr(current, "exceptions") and getattr(current, "exceptions"):
        exceptions = getattr(current, "exceptions")
        if not exceptions:
            break
        current = exceptions[0]
    return current


def _normalize_external_error(exc: BaseException) -> ValueError:
    root = _unwrap_exception(exc)
    if isinstance(root, httpx.HTTPStatusError):
        status = root.response.status_code
        if status == 401:
            return ValueError("remote MCP server responded 401 Unauthorized; this server likely requires authentication")
        return ValueError(f"remote MCP server responded {status}: {root}")
    return ValueError(str(root))


def _workspace_env(workspace: dict[str, object] | None) -> dict[str, str]:
    if not isinstance(workspace, dict):
        return {}
    absolute_path = workspace.get("absolute_path")
    if not isinstance(absolute_path, str) or not absolute_path.strip():
        return {}
    return {
        "AGENT_WORKSPACE": absolute_path,
        "AGENT_WORKSPACE_ROOT": absolute_path,
    }


def _serialize_content_item(item: Any) -> dict[str, object]:
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    if isinstance(item, dict):
        return dict(item)
    return {"value": str(item)}


class ExternalMCPClientService:
    def __init__(self, auth_service: MCPAuthService | None = None) -> None:
        self._auth_service = auth_service

    def test_connection(
        self,
        server: RegisteredMCPServer,
        *,
        workspace: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if server.connection_mode != "external":
            raise ValueError("only external MCP servers can be connection-tested")
        try:
            return anyio.run(self._test_connection_async, server, workspace)
        except BaseException as exc:
            raise _normalize_external_error(exc) from exc

    def authenticate(self, server: RegisteredMCPServer) -> dict[str, object]:
        if server.connection_mode != "external":
            raise ValueError("only external MCP servers can be authenticated")
        if server.transport_kind not in {"sse", "streamable_http"}:
            raise ValueError("authentication UI is only supported for URL-based MCP servers")
        if not server.endpoint:
            raise ValueError("external MCP server requires endpoint")
        if self._auth_service is None:
            raise ValueError("auth service is not configured")
        return anyio.run(self._authenticate_async, server)

    def discover_tools(
        self,
        server: RegisteredMCPServer,
        *,
        workspace: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if server.connection_mode != "external":
            raise ValueError("only external MCP servers can be discovered")
        try:
            return anyio.run(self._discover_tools_async, server, workspace)
        except BaseException as exc:
            raise _normalize_external_error(exc) from exc

    def call_tool(
        self,
        server: RegisteredMCPServer,
        *,
        tool_name: str,
        arguments: dict[str, object],
        workspace: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if server.connection_mode != "external":
            raise ValueError("only external MCP servers can be invoked here")
        try:
            return anyio.run(self._call_tool_async, server, tool_name, arguments, workspace)
        except BaseException as exc:
            raise _normalize_external_error(exc) from exc

    async def _test_connection_async(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ) -> dict[str, object]:
        async with self._open_session(server, workspace) as session:
            await session.initialize()
            tools = await session.list_tools()
            return {
                "ok": True,
                "server_ref": server.server_ref,
                "transport_kind": server.transport_kind,
                "tool_count": len(tools.tools),
                "tools": [tool.name for tool in tools.tools],
            }

    async def _discover_tools_async(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ) -> dict[str, object]:
        async with self._open_session(server, workspace) as session:
            await session.initialize()
            result = await session.list_tools()
            return {
                "server_ref": server.server_ref,
                "tools": [
                    {
                        "name": tool.name,
                        "title": tool.title,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                        "output_schema": tool.outputSchema,
                    }
                    for tool in result.tools
                ],
            }

    async def _call_tool_async(
        self,
        server: RegisteredMCPServer,
        tool_name: str,
        arguments: dict[str, object],
        workspace: dict[str, object] | None,
    ) -> dict[str, object]:
        async with self._open_session(server, workspace) as session:
            await session.initialize()
            result = await session.call_tool(
                tool_name,
                dict(arguments),
                read_timeout_seconds=timedelta(seconds=30),
            )
            return {
                "is_error": bool(result.isError),
                "content": [_serialize_content_item(item) for item in result.content],
                "structured_content": result.structuredContent,
                "meta": result.meta or {},
            }

    async def _authenticate_async(self, server: RegisteredMCPServer) -> dict[str, object]:
        if self._auth_service is None:
            raise ValueError("auth service is not configured")
        client, waiter = await self._auth_service.build_authorized_client(server.server_ref, server.endpoint)
        try:
            async with client:
                if server.transport_kind == "streamable_http":
                    async with streamable_http_client(server.endpoint, http_client=client) as (
                        read_stream,
                        write_stream,
                        _get_session_id,
                    ):
                        async with ClientSession(read_stream, write_stream) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            return {
                                "ok": True,
                                "server_ref": server.server_ref,
                                "tool_count": len(tools.tools),
                                "tools": [tool.name for tool in tools.tools],
                                "auth_flow": "browser_oauth",
                            }
                if server.transport_kind == "sse":
                    async with sse_client(server.endpoint, auth=client.auth) as (read_stream, write_stream):
                        async with ClientSession(read_stream, write_stream) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            return {
                                "ok": True,
                                "server_ref": server.server_ref,
                                "tool_count": len(tools.tools),
                                "tools": [tool.name for tool in tools.tools],
                                "auth_flow": "browser_oauth",
                            }
                raise ValueError(f"unsupported transport_kind '{server.transport_kind}'")
        except BaseException as exc:
            raise _normalize_external_error(exc) from exc
        finally:
            waiter.stop()

    @asynccontextmanager
    async def _open_session(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ):
        if server.transport_kind == "stdio":
            async with self._open_stdio_session(server, workspace) as session:
                yield session
            return
        if server.transport_kind == "sse":
            async with self._open_sse_session(server, workspace) as session:
                yield session
            return
        if server.transport_kind == "streamable_http":
            async with self._open_streamable_http_session(server, workspace) as session:
                yield session
            return
        raise ValueError(f"unsupported external transport_kind '{server.transport_kind}'")

    def _build_stdio_parameters(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ) -> StdioServerParameters:
        if not server.command:
            raise ValueError("external stdio MCP server requires command")
        merged_env = dict(os.environ)
        merged_env.update(server.env)
        merged_env.update(_workspace_env(workspace))
        cwd = server.cwd or None
        if cwd:
            cwd = str(Path(cwd).resolve())
        return StdioServerParameters(
            command=server.command,
            args=list(server.args),
            env=merged_env,
            cwd=cwd,
        )

    @asynccontextmanager
    async def _open_stdio_session(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ):
        parameters = self._build_stdio_parameters(server, workspace)
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                yield session

    @asynccontextmanager
    async def _open_sse_session(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ):
        if not server.endpoint:
            raise ValueError("external sse MCP server requires endpoint")
        headers = _workspace_env(workspace)
        async with sse_client(server.endpoint, headers=headers or None) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                yield session

    @asynccontextmanager
    async def _open_streamable_http_session(
        self,
        server: RegisteredMCPServer,
        workspace: dict[str, object] | None,
    ):
        if not server.endpoint:
            raise ValueError("external streamable_http MCP server requires endpoint")
        headers = _workspace_env(workspace)
        async with httpx.AsyncClient(headers=headers or None, timeout=30) as client:
            async with streamable_http_client(server.endpoint, http_client=client) as (
                read_stream,
                write_stream,
                _get_session_id,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    yield session
