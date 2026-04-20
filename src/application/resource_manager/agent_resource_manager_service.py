from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog

from domain_packs import get_registered_agent_descriptors
from application.agent_admin.standard_agent_capability import (
    AgentMCPBinding,
    AgentSkillBinding,
    StandardAgentCapabilityService,
    StandardAgentCapabilityRepository,
)
from application.resource_manager.mcp_import_config import (
    MCPImportConfigRepository,
)
from core.resource_registry import (
    FileResourceRegistryRepository,
    ResourceRegistryService,
)
from infrastructure.persistence import (
    SQLiteAgentCapabilityRepository,
    SQLiteDocumentStore,
    SQLiteResourceRegistryRepository,
    get_persistence_settings,
)
from infrastructure.mcp.external_mcp_client_service import ExternalMCPClientService
from infrastructure.mcp.mcp_auth_service import MCPAuthService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESOURCE_MANAGER_STORAGE_DIR = Path("resource_manager")
AGENT_ADMIN_STORAGE_DIR = Path("agent_admin")
LEGACY_RESOURCE_REGISTRY_FILE = PROJECT_ROOT / "runtime_data" / "agent_resource_registry.json"
LEGACY_EDUCATION_RESOURCE_REGISTRY_FILE = (
    PROJECT_ROOT / "runtime_data" / "education" / "agent_resource_registry.json"
)
LEGACY_AGENT_CAPABILITY_FILE = PROJECT_ROOT / "runtime_data" / "agent_capabilities.json"
LEGACY_EDUCATION_AGENT_CAPABILITY_FILE = (
    PROJECT_ROOT / "runtime_data" / "education" / "agent_capabilities.json"
)
MCP_IMPORT_CONFIG_FILE = PROJECT_ROOT / "agentsroles.mcp.json"


def _resource_registry_file(settings) -> Path:
    return settings.files_root / RESOURCE_MANAGER_STORAGE_DIR / "agent_resource_registry.json"


def _agent_capability_file(settings) -> Path:
    return settings.files_root / AGENT_ADMIN_STORAGE_DIR / "agent_capabilities.json"


def _pick_legacy_file(primary: Path, secondary: Path) -> Path | None:
    if primary.exists():
        return primary
    if secondary.exists():
        return secondary
    return None

class AgentResourceManagerFacade:
    def __init__(self) -> None:
        settings = get_persistence_settings()
        resource_registry_file = _resource_registry_file(settings)
        agent_capability_file = _agent_capability_file(settings)
        legacy_resource_registry_file = _pick_legacy_file(
            LEGACY_RESOURCE_REGISTRY_FILE,
            LEGACY_EDUCATION_RESOURCE_REGISTRY_FILE,
        )
        legacy_agent_capability_file = _pick_legacy_file(
            LEGACY_AGENT_CAPABILITY_FILE,
            LEGACY_EDUCATION_AGENT_CAPABILITY_FILE,
        )
        if (
            settings.backend != "sqlite"
            and not resource_registry_file.exists()
            and legacy_resource_registry_file is not None
        ):
            resource_registry_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(legacy_resource_registry_file, resource_registry_file)
        if (
            settings.backend != "sqlite"
            and not agent_capability_file.exists()
            and legacy_agent_capability_file is not None
        ):
            agent_capability_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(legacy_agent_capability_file, agent_capability_file)
        if settings.backend == "sqlite":
            resource_repository = SQLiteResourceRegistryRepository(
                SQLiteDocumentStore(settings.sqlite_path),
                legacy_file_path=(
                    resource_registry_file
                    if resource_registry_file.exists()
                    else legacy_resource_registry_file
                ),
                default_workspace_root=settings.default_workspace_root,
            )
        else:
            resource_repository = FileResourceRegistryRepository(resource_registry_file)
        self._resource_service = ResourceRegistryService(resource_repository, project_root=PROJECT_ROOT)
        if settings.backend == "sqlite":
            capability_repository = SQLiteAgentCapabilityRepository(
                SQLiteDocumentStore(settings.sqlite_path),
                legacy_file_path=(
                    agent_capability_file
                    if agent_capability_file.exists()
                    else legacy_agent_capability_file
                ),
            )
        else:
            capability_repository = StandardAgentCapabilityRepository(
                agent_capability_file,
                legacy_file_path=legacy_agent_capability_file,
            )
        self._capability_service = StandardAgentCapabilityService(capability_repository)
        self._external_mcp = ExternalMCPClientService(
            MCPAuthService(settings.auth_root / "mcp_auth.json")
        )
        self._mcp_import_config = MCPImportConfigRepository(MCP_IMPORT_CONFIG_FILE)
        self._sync_mcp_import_config()

    def get_snapshot(self) -> dict[str, object]:
        registry = self._resource_service.get_registry()
        descriptors = get_registered_agent_descriptors()
        mcp_index = {item.server_ref: item for item in registry.mcp_servers}
        skill_index = {item.skill_name: item for item in registry.skills}
        workspace_index = {item.agent_id: item for item in registry.agent_workspaces}
        agents: list[dict[str, object]] = []
        for descriptor in descriptors:
            capability = self._capability_service.get_capability(descriptor.agent_id, descriptors)
            preview = self._capability_service.build_preview(descriptor, capability)
            workspace_registration = workspace_index.get(descriptor.agent_id)
            assigned_mcp_refs = [
                binding.server_ref
                for binding in capability.mcp_bindings
                if binding.enabled
            ]
            agents.append(
                {
                    "agent_id": descriptor.agent_id,
                    "domain": descriptor.domain,
                    "name": descriptor.name,
                    "role": descriptor.role,
                    "distribution": {
                        "assigned_mcp_servers": assigned_mcp_refs,
                        "assigned_mcp_server_details": [
                            self._serialize_mcp_server(mcp_index[server_ref])
                            for server_ref in assigned_mcp_refs
                            if server_ref in mcp_index
                        ],
                        "assigned_skills": [
                            binding.skill_name
                            for binding in capability.skill_bindings
                            if binding.enabled
                        ],
                        "workspace": self._serialize_workspace(workspace_registration),
                    },
                    "effectiveness": {
                        "operational_summary": preview.get("operational_summary", ""),
                        "collaboration_summary": preview.get("collaboration_summary", ""),
                        "attention_points": list(preview.get("attention_points") or []),
                    },
                }
            )
        return {
            "registry": {
                "workspace_root": asdict(registry.workspace_root),
                "mcp_servers": [asdict(item) for item in registry.mcp_servers],
                "skills": [asdict(item) for item in registry.skills],
                "skill_sources": [asdict(item) for item in registry.skill_sources],
                "agent_workspaces": [
                    self._serialize_workspace(item) for item in registry.agent_workspaces
                ],
            },
            "agents": agents,
            "registered_counts": {
                "mcp_servers": len(registry.mcp_servers),
                "skills": len(registry.skills),
                "workspaces": len(registry.agent_workspaces),
            },
            "distribution_health": {
                "agents_with_mcp": sum(
                    1 for agent in agents if agent["distribution"]["assigned_mcp_servers"]
                ),
                "agents_with_skills": sum(
                    1 for agent in agents if agent["distribution"]["assigned_skills"]
                ),
                "agents_with_workspaces": sum(
                    1
                    for agent in agents
                    if agent["distribution"]["workspace"]
                    and agent["distribution"]["workspace"]["enabled"]
                ),
            },
            "catalog": {
                "mcp_server_refs": sorted(mcp_index.keys()),
                "skill_names": sorted(skill_index.keys()),
            },
            "skill_discovery": self._resource_service.list_discovered_skills(),
            "workspace_root_resolved": (
                str(self._resource_service.resolve_workspace_root_path(registry.workspace_root.root_path))
                if registry.workspace_root.root_path
                else ""
            ),
            "config_files": {
                "mcp_import": str(self._mcp_import_config.file_path),
            },
        }

    def save_workspace_root(self, payload: dict[str, object]) -> dict[str, object]:
        root = self._resource_service.save_workspace_root(payload)
        return {
            **asdict(root),
            "resolved_path": (
                str(self._resource_service.resolve_workspace_root_path(root.root_path))
                if root.root_path
                else ""
            ),
        }

    def pick_workspace_root(self) -> dict[str, object]:
        dialog_root = tk.Tk()
        dialog_root.withdraw()
        dialog_root.attributes("-topmost", True)
        try:
            selected_path = filedialog.askdirectory(
                title="Select global workspace root",
                mustexist=False,
            )
        finally:
            dialog_root.destroy()
        return {"root_path": selected_path or ""}

    def provision_workspace_root(self) -> dict[str, object]:
        descriptors = {
            descriptor.agent_id: descriptor.name
            for descriptor in get_registered_agent_descriptors()
        }
        workspaces = self._resource_service.provision_agent_workspaces(agent_names=descriptors)
        for workspace in workspaces:
            self._sync_workspace_metadata(workspace.agent_id, workspace)
        registry = self._resource_service.get_registry()
        return {
            "workspace_root": asdict(registry.workspace_root),
            "agent_workspaces": [self._serialize_workspace(item) for item in workspaces],
        }

    def save_mcp_server(self, server_ref: str, payload: dict[str, object]) -> dict[str, object]:
        saved = self._resource_service.save_mcp_server({**payload, "server_ref": server_ref})
        return asdict(saved)

    def test_mcp_server_connection(self, server_ref: str) -> dict[str, object]:
        server = self._resource_service.get_mcp_server(server_ref)
        return self._external_mcp.test_connection(server)

    def authenticate_mcp_server(self, server_ref: str) -> dict[str, object]:
        server = self._resource_service.get_mcp_server(server_ref)
        return self._external_mcp.authenticate(server)

    def discover_mcp_server_tools(self, server_ref: str) -> dict[str, object]:
        server = self._resource_service.get_mcp_server(server_ref)
        discovery = self._external_mcp.discover_tools(server)
        saved = self._resource_service.save_mcp_discovered_tools(
            server_ref,
            [str(item.get("name", "")) for item in discovery.get("tools", []) if str(item.get("name", "")).strip()],
        )
        return {
            "server": asdict(saved),
            "discovery": discovery,
        }

    def save_skill(self, skill_name: str, payload: dict[str, object]) -> dict[str, object]:
        saved = self._resource_service.save_skill({**payload, "skill_name": skill_name})
        return asdict(saved)

    def delete_skill(self, skill_name: str) -> dict[str, object]:
        self._resource_service.delete_skill(skill_name)
        return {"deleted": True, "skill_name": skill_name}

    def save_skill_source(self, source_ref: str, payload: dict[str, object]) -> dict[str, object]:
        saved = self._resource_service.save_skill_source({**payload, "source_ref": source_ref})
        return asdict(saved)

    def delete_skill_source(self, source_ref: str) -> dict[str, object]:
        self._resource_service.delete_skill_source(source_ref)
        return {"deleted": True, "source_ref": source_ref}

    def sync_skills(self) -> dict[str, object]:
        saved = self._resource_service.sync_skills_from_sources()
        discovery = self._resource_service.list_discovered_skills()
        return {
            "saved_skills": [asdict(item) for item in saved],
            "discovery": discovery,
        }

    def save_workspace(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        workspace = self._resource_service.save_workspace({**payload, "agent_id": agent_id})
        self._sync_workspace_metadata(agent_id, workspace)
        return self._serialize_workspace(workspace)

    def save_agent_distribution(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        registry = self._resource_service.get_registry()
        mcp_index = {item.server_ref: item for item in registry.mcp_servers if item.enabled}
        skill_index = {item.skill_name: item for item in registry.skills if item.enabled}
        descriptors = get_registered_agent_descriptors()
        capability = self._capability_service.get_capability(agent_id, descriptors)
        selected_mcp_servers = [str(item) for item in (payload.get("mcp_servers") or []) if str(item).strip()]
        selected_skills = [str(item) for item in (payload.get("skills") or []) if str(item).strip()]

        missing_mcp = [item for item in selected_mcp_servers if item not in mcp_index]
        missing_skills = [item for item in selected_skills if item not in skill_index]
        if missing_mcp:
            raise ValueError(f"unknown or disabled MCP server refs: {', '.join(missing_mcp)}")
        if missing_skills:
            raise ValueError(f"unknown or disabled skill names: {', '.join(missing_skills)}")

        existing_mcp = {item.server_ref: item for item in capability.mcp_bindings}
        existing_skills = {item.skill_name: item for item in capability.skill_bindings}

        updated_capability = self._capability_service.save_capability(
            {
                **asdict(capability),
                "mcp_bindings": [
                    asdict(
                        AgentMCPBinding(
                            server_ref=server_ref,
                            tool_refs=(
                                existing_mcp[server_ref].tool_refs
                                if server_ref in existing_mcp and existing_mcp[server_ref].tool_refs
                                else list(mcp_index[server_ref].tool_refs)
                            ),
                            enabled=True,
                            usage_notes=(
                                existing_mcp[server_ref].usage_notes
                                if server_ref in existing_mcp and existing_mcp[server_ref].usage_notes
                                else mcp_index[server_ref].notes
                            ),
                        )
                    )
                    for server_ref in selected_mcp_servers
                ],
                "skill_bindings": [
                    asdict(
                        AgentSkillBinding(
                            skill_name=skill_name,
                            enabled=True,
                            trigger_kinds=(
                                existing_skills[skill_name].trigger_kinds
                                if skill_name in existing_skills and existing_skills[skill_name].trigger_kinds
                                else list(skill_index[skill_name].trigger_kinds)
                            ),
                            scope=(
                                existing_skills[skill_name].scope
                                if skill_name in existing_skills
                                else "session"
                            ),
                            execution_mode=(
                                existing_skills[skill_name].execution_mode
                                if skill_name in existing_skills
                                else "human_confirmed"
                            ),
                            usage_notes=(
                                existing_skills[skill_name].usage_notes
                                if skill_name in existing_skills and existing_skills[skill_name].usage_notes
                                else skill_index[skill_name].notes
                            ),
                        )
                    )
                    for skill_name in selected_skills
                ],
            },
            descriptors,
        )
        descriptor = next(
            item for item in descriptors if item.agent_id == agent_id
        )
        return {
            "agent_id": agent_id,
            "capability": {
                **asdict(updated_capability),
                "resolved_preview": self._capability_service.build_preview(
                    descriptor,
                    updated_capability,
                ),
            },
        }

    def _sync_mcp_import_config(self) -> None:
        for payload in self._mcp_import_config.list_mcp_servers():
            self._resource_service.save_mcp_server(payload)

    def _serialize_workspace(self, workspace) -> dict[str, object] | None:
        if workspace is None:
            return None
        absolute_path = self._resource_service.resolve_workspace_path(workspace.relative_path)
        return {
            "agent_id": workspace.agent_id,
            "relative_path": workspace.relative_path,
            "absolute_path": str(absolute_path),
            "enabled": workspace.enabled,
            "notes": workspace.notes,
            "exists": absolute_path.exists(),
        }

    def _serialize_mcp_server(self, server) -> dict[str, object]:
        return {
            "server_ref": server.server_ref,
            "name": server.name,
            "description": server.description,
            "connection_mode": server.connection_mode,
            "transport_kind": server.transport_kind,
            "tool_refs": list(server.tool_refs),
            "discovered_tool_refs": list(server.discovered_tool_refs),
            "enabled": server.enabled,
            "notes": server.notes,
        }

    def _sync_workspace_metadata(self, agent_id: str, workspace) -> None:
        descriptors = get_registered_agent_descriptors()
        capability = self._capability_service.get_capability(agent_id, descriptors)
        metadata = dict(capability.metadata)
        metadata["workspace"] = {
            "relative_path": workspace.relative_path,
            "enabled": workspace.enabled,
            "notes": workspace.notes,
        }
        self._capability_service.save_capability(
            {
                **asdict(capability),
                "metadata": metadata,
            },
            descriptors,
        )
