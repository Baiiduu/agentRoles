from __future__ import annotations

from pathlib import Path
import re

from .models import (
    AgentWorkspaceRegistration,
    RegisteredMCPServer,
    RegisteredSkill,
    ResourceRegistry,
    WorkspaceRootConfig,
)
from .repository import FileResourceRegistryRepository


class ResourceRegistryService:
    def __init__(
        self,
        repository: FileResourceRegistryRepository,
        *,
        project_root: Path,
    ) -> None:
        self._repository = repository
        self._project_root = project_root.resolve()

    def get_registry(self) -> ResourceRegistry:
        return self._repository.get_registry()

    def save_workspace_root(self, payload: dict[str, object]) -> WorkspaceRootConfig:
        registry = self.get_registry()
        existing = registry.workspace_root
        root_path = str(payload.get("root_path", existing.root_path)).strip()
        root = WorkspaceRootConfig(
            root_path=root_path,
            enabled=bool(root_path),
            provisioned=False if not root_path else existing.provisioned,
            notes=str(payload.get("notes", existing.notes)),
        )
        registry.workspace_root = root
        if not root.root_path:
            registry.agent_workspaces = []
        self._repository.save_registry(registry)
        return root

    def save_mcp_server(self, payload: dict[str, object]) -> RegisteredMCPServer:
        registry = self.get_registry()
        server = RegisteredMCPServer(
            server_ref=str(payload.get("server_ref", "")),
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            connection_mode=str(payload.get("connection_mode", "internal")),
            transport_kind=str(payload.get("transport_kind", "custom")),
            command=str(payload.get("command", "")),
            args=[str(item) for item in (payload.get("args") or [])],
            endpoint=str(payload.get("endpoint", "")),
            env={str(key): str(value) for key, value in (payload.get("env") or {}).items()},
            cwd=str(payload.get("cwd", "")),
            tool_refs=[str(item) for item in (payload.get("tool_refs") or [])],
            discovered_tool_refs=[str(item) for item in (payload.get("discovered_tool_refs") or [])],
            enabled=bool(payload.get("enabled", True)),
            notes=str(payload.get("notes", "")),
        )
        registry.mcp_servers = [
            item for item in registry.mcp_servers if item.server_ref != server.server_ref
        ] + [server]
        registry.mcp_servers.sort(key=lambda item: item.server_ref)
        self._repository.save_registry(registry)
        return server

    def get_mcp_server(self, server_ref: str) -> RegisteredMCPServer:
        registry = self.get_registry()
        for item in registry.mcp_servers:
            if item.server_ref == server_ref:
                return item
        raise KeyError(f"unknown MCP server '{server_ref}'")

    def save_mcp_discovered_tools(
        self,
        server_ref: str,
        tool_refs: list[str],
    ) -> RegisteredMCPServer:
        existing = self.get_mcp_server(server_ref)
        return self.save_mcp_server(
            {
                **existing.__dict__,
                "discovered_tool_refs": list(tool_refs),
                "tool_refs": list(tool_refs) if existing.connection_mode == "external" else list(existing.tool_refs),
            }
        )

    def save_skill(self, payload: dict[str, object]) -> RegisteredSkill:
        registry = self.get_registry()
        skill = RegisteredSkill(
            skill_name=str(payload.get("skill_name", "")),
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            trigger_kinds=[str(item) for item in (payload.get("trigger_kinds") or [])],
            enabled=bool(payload.get("enabled", True)),
            notes=str(payload.get("notes", "")),
        )
        registry.skills = [
            item for item in registry.skills if item.skill_name != skill.skill_name
        ] + [skill]
        registry.skills.sort(key=lambda item: item.skill_name)
        self._repository.save_registry(registry)
        return skill

    def save_workspace(self, payload: dict[str, object]) -> AgentWorkspaceRegistration:
        registry = self.get_registry()
        workspace = AgentWorkspaceRegistration(
            agent_id=str(payload.get("agent_id", "")),
            relative_path=str(payload.get("relative_path", "")),
            enabled=bool(payload.get("enabled", True)),
            notes=str(payload.get("notes", "")),
        )
        self.ensure_workspace_directory(workspace.relative_path)
        registry.agent_workspaces = [
            item for item in registry.agent_workspaces if item.agent_id != workspace.agent_id
        ] + [workspace]
        registry.agent_workspaces.sort(key=lambda item: item.agent_id)
        self._repository.save_registry(registry)
        return workspace

    def provision_agent_workspaces(
        self,
        *,
        agent_names: dict[str, str],
    ) -> list[AgentWorkspaceRegistration]:
        registry = self.get_registry()
        root = registry.workspace_root
        if not root.root_path:
            raise ValueError("workspace root must be selected before provisioning")
        resolved_root = self.ensure_workspace_root_directory(root.root_path)
        workspaces: list[AgentWorkspaceRegistration] = []
        for agent_id, agent_name in agent_names.items():
            workspace_name = self._safe_workspace_name(agent_name)
            absolute_path = resolved_root / workspace_name
            absolute_path.mkdir(parents=True, exist_ok=True)
            relative_or_absolute = str(absolute_path)
            workspaces.append(
                AgentWorkspaceRegistration(
                    agent_id=agent_id,
                    relative_path=relative_or_absolute,
                    enabled=True,
                    notes="Provisioned from selected workspace root.",
                )
            )
        registry.agent_workspaces = sorted(workspaces, key=lambda item: item.agent_id)
        registry.workspace_root = WorkspaceRootConfig(
            root_path=root.root_path,
            enabled=root.enabled,
            provisioned=True,
            notes=root.notes,
        )
        self._repository.save_registry(registry)
        return registry.agent_workspaces

    def resolve_workspace_path(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if not candidate.is_absolute():
            candidate = (self._project_root / relative_path).resolve()
            if self._project_root not in candidate.parents and candidate != self._project_root:
                raise ValueError("workspace path must stay within the project directory")
            return candidate
        return candidate.resolve()

    def resolve_workspace_root_path(self, root_path: str) -> Path:
        candidate = Path(root_path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (self._project_root / root_path).resolve()

    def ensure_workspace_root_directory(self, root_path: str) -> Path:
        resolved = self.resolve_workspace_root_path(root_path)
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def ensure_workspace_directory(self, relative_path: str) -> Path:
        resolved = self.resolve_workspace_path(relative_path)
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def _safe_workspace_name(self, value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*]', "_", value).strip()
        return cleaned or "agent"


EducationResourceRegistryService = ResourceRegistryService
