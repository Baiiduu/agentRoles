from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import (
    AgentWorkspaceRegistration,
    RegisteredMCPServer,
    RegisteredSkill,
    ResourceRegistry,
    WorkspaceRootConfig,
)


class FileResourceRegistryRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def get_registry(self) -> ResourceRegistry:
        payload = self._read_payload()
        return ResourceRegistry(
            workspace_root=WorkspaceRootConfig(
                root_path=str((payload.get("workspace_root") or {}).get("root_path", "")),
                enabled=bool((payload.get("workspace_root") or {}).get("enabled", False)),
                provisioned=bool((payload.get("workspace_root") or {}).get("provisioned", False)),
                notes=str((payload.get("workspace_root") or {}).get("notes", "")),
            ),
            mcp_servers=[
                RegisteredMCPServer(
                    server_ref=str(item.get("server_ref", "")),
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    connection_mode=str(item.get("connection_mode", "internal")),
                    transport_kind=str(item.get("transport_kind", "custom")),
                    command=str(item.get("command", "")),
                    args=[str(ref) for ref in (item.get("args") or [])],
                    endpoint=str(item.get("endpoint", "")),
                    env={str(key): str(value) for key, value in (item.get("env") or {}).items()},
                    cwd=str(item.get("cwd", "")),
                    tool_refs=[str(ref) for ref in (item.get("tool_refs") or [])],
                    discovered_tool_refs=[str(ref) for ref in (item.get("discovered_tool_refs") or [])],
                    enabled=bool(item.get("enabled", True)),
                    notes=str(item.get("notes", "")),
                )
                for item in payload.get("mcp_servers", [])
            ],
            skills=[
                RegisteredSkill(
                    skill_name=str(item.get("skill_name", "")),
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    trigger_kinds=[str(ref) for ref in (item.get("trigger_kinds") or [])],
                    enabled=bool(item.get("enabled", True)),
                    notes=str(item.get("notes", "")),
                )
                for item in payload.get("skills", [])
            ],
            agent_workspaces=[
                AgentWorkspaceRegistration(
                    agent_id=str(item.get("agent_id", "")),
                    relative_path=str(item.get("relative_path", "")),
                    enabled=bool(item.get("enabled", True)),
                    notes=str(item.get("notes", "")),
                )
                for item in payload.get("agent_workspaces", [])
            ],
        )

    def save_registry(self, registry: ResourceRegistry) -> ResourceRegistry:
        payload = {
            "workspace_root": asdict(registry.workspace_root),
            "mcp_servers": [asdict(item) for item in registry.mcp_servers],
            "skills": [asdict(item) for item in registry.skills],
            "agent_workspaces": [asdict(item) for item in registry.agent_workspaces],
        }
        self._write_payload(payload)
        return registry

    def _read_payload(self) -> dict[str, object]:
        if not self._file_path.exists():
            self._write_payload(
                {
                    "workspace_root": {
                        "root_path": "",
                        "enabled": False,
                        "provisioned": False,
                        "notes": "",
                    },
                    "mcp_servers": [],
                    "skills": [],
                    "agent_workspaces": [],
                }
            )
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


FileEducationResourceRegistryRepository = FileResourceRegistryRepository
