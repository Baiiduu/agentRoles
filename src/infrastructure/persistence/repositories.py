from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from application.agent_admin.standard_agent_capability import (
    AgentCapability,
    StandardAgentCapabilityRepository,
    default_capability_for_descriptor,
    hydrate_capability,
)
from application.agent_admin.standard_agent_config import (
    AgentConfig,
    StandardAgentConfigRepository,
    default_config_for_descriptor,
)
from core.agents import AgentDescriptor
from core.resource_registry.models import (
    AgentWorkspaceRegistration,
    RegisteredMCPServer,
    RegisteredSkill,
    ResourceRegistry,
    WorkspaceRootConfig,
)
from core.resource_registry.repository import FileResourceRegistryRepository

from .sqlite_document_store import SQLiteDocumentStore


class SQLiteAgentConfigRepository(StandardAgentConfigRepository):
    collection_name = "agent_configs"

    def __init__(
        self,
        store: SQLiteDocumentStore,
        *,
        legacy_file_path: Path | None = None,
    ) -> None:
        self._store = store
        self._legacy_file_path = legacy_file_path
        self._import_legacy_if_needed()

    def list_all(self, descriptors: list[AgentDescriptor]) -> list[AgentConfig]:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        stored = self._read_all()
        by_id = {item.agent_id: item for item in stored}
        merged: list[AgentConfig] = []
        for descriptor in descriptors:
            merged.append(by_id.get(descriptor.agent_id, default_config_for_descriptor(descriptor)))
        for item in stored:
            if item.agent_id not in descriptor_map:
                merged.append(item)
        return merged

    def get(self, agent_id: str, descriptors: list[AgentDescriptor]) -> AgentConfig:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        payload = self._store.get_document(self.collection_name, agent_id)
        if payload is not None:
            return AgentConfig(**payload)
        return default_config_for_descriptor(descriptor_map[agent_id])

    def save(self, config: AgentConfig, descriptors: list[AgentDescriptor]) -> AgentConfig:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if config.agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{config.agent_id}'")
        self._store.put_document(self.collection_name, config.agent_id, asdict(config))
        return config

    def _read_all(self) -> list[AgentConfig]:
        return [AgentConfig(**item) for item in self._store.list_documents(self.collection_name)]

    def _import_legacy_if_needed(self) -> None:
        if self._store.has_any(self.collection_name):
            return
        payload = _read_legacy_payload(self._legacy_file_path, default_key="agent_configs")
        for item in payload.get("agent_configs", []):
            agent_id = str(item.get("agent_id", "")).strip()
            if not agent_id:
                continue
            self._store.put_document(self.collection_name, agent_id, dict(item))


class SQLiteAgentCapabilityRepository(StandardAgentCapabilityRepository):
    collection_name = "agent_capabilities"

    def __init__(
        self,
        store: SQLiteDocumentStore,
        *,
        legacy_file_path: Path | None = None,
    ) -> None:
        self._store = store
        self._legacy_file_path = legacy_file_path
        self._import_legacy_if_needed()

    def list_all(self, descriptors: list[AgentDescriptor]) -> list[AgentCapability]:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        stored = self._read_all()
        by_id = {item.agent_id: item for item in stored}
        merged: list[AgentCapability] = []
        for descriptor in descriptors:
            merged.append(by_id.get(descriptor.agent_id, default_capability_for_descriptor(descriptor)))
        for item in stored:
            if item.agent_id not in descriptor_map:
                merged.append(item)
        return merged

    def get(self, agent_id: str, descriptors: list[AgentDescriptor]) -> AgentCapability:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        payload = self._store.get_document(self.collection_name, agent_id)
        if payload is not None:
            return hydrate_capability(payload)
        return default_capability_for_descriptor(descriptor_map[agent_id])

    def save(self, capability: AgentCapability, descriptors: list[AgentDescriptor]) -> AgentCapability:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if capability.agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{capability.agent_id}'")
        self._store.put_document(self.collection_name, capability.agent_id, asdict(capability))
        return capability

    def _read_all(self) -> list[AgentCapability]:
        return [hydrate_capability(item) for item in self._store.list_documents(self.collection_name)]

    def _import_legacy_if_needed(self) -> None:
        if self._store.has_any(self.collection_name):
            return
        payload = _read_legacy_payload(self._legacy_file_path, default_key="agent_capabilities")
        for item in payload.get("agent_capabilities", []):
            agent_id = str(item.get("agent_id", "")).strip()
            if not agent_id:
                continue
            self._store.put_document(self.collection_name, agent_id, dict(item))


class SQLiteResourceRegistryRepository(FileResourceRegistryRepository):
    collection_name = "resource_registry"
    document_id = "default"

    def __init__(
        self,
        store: SQLiteDocumentStore,
        *,
        legacy_file_path: Path | None = None,
        default_workspace_root: Path | None = None,
    ) -> None:
        self._store = store
        self._legacy_file_path = legacy_file_path
        self._default_workspace_root = default_workspace_root
        self._import_legacy_if_needed()

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
        payload = self._store.get_document(self.collection_name, self.document_id)
        if payload is None:
            payload = self._default_payload()
            self._write_payload(payload)
        return payload

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._store.put_document(self.collection_name, self.document_id, payload)

    def _import_legacy_if_needed(self) -> None:
        if self._store.get_document(self.collection_name, self.document_id) is not None:
            return
        payload = _read_legacy_payload(self._legacy_file_path, default_key=None)
        self._store.put_document(self.collection_name, self.document_id, payload or self._default_payload())

    def _default_payload(self) -> dict[str, object]:
        default_root = str(self._default_workspace_root) if self._default_workspace_root is not None else ""
        return {
            "workspace_root": {
                "root_path": default_root,
                "enabled": bool(default_root),
                "provisioned": False,
                "notes": "Default workspace root on E drive.",
            },
            "mcp_servers": [],
            "skills": [],
            "agent_workspaces": [],
        }


def _read_legacy_payload(file_path: Path | None, *, default_key: str | None) -> dict[str, object]:
    if file_path is None or not file_path.exists():
        if default_key is None:
            return {}
        return {default_key: []}
    return json.loads(file_path.read_text(encoding="utf-8"))
