from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from core.agents import AgentDescriptor

from application.agent_admin.agent_capability_service import AgentCapabilityFacade
from application.agent_admin.agent_config_service import AgentConfigFacade
from application.resource_manager.agent_resource_manager_service import AgentResourceManagerFacade
from application.runtime.skill_prompt_service import build_runtime_skill_packages
from infrastructure.mcp.mcp_runtime_service import build_mcp_server_catalog


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _runtime_mcp_tool_refs(mcp_server_catalog: list[dict[str, object]]) -> list[str]:
    refs: list[str] = []
    for server in mcp_server_catalog:
        tools = server.get("tools", [])
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            tool_ref = str(tool.get("tool_ref", "")).strip()
            if tool_ref:
                refs.append(tool_ref)
    return refs


class AgentRuntimeContextFacade:
    def __init__(self) -> None:
        self._agent_config = AgentConfigFacade()
        self._agent_capability = AgentCapabilityFacade()
        self._agent_resource_manager = AgentResourceManagerFacade()

    def runtime_descriptors(self) -> list[AgentDescriptor]:
        configured_descriptors = self._agent_config.configured_descriptors()
        resource_snapshot = self._agent_resource_manager.get_snapshot()
        agent_distribution = {
            str(item.get("agent_id", "")): item for item in resource_snapshot.get("agents", [])
        }
        runtime_descriptors: list[AgentDescriptor] = []
        for descriptor in configured_descriptors:
            capability_payload = self._agent_capability.get_capability(descriptor.agent_id)
            resolved_preview = capability_payload.get("resolved_preview") or {}
            distribution = agent_distribution.get(descriptor.agent_id, {})
            assigned_skill_names = distribution.get("distribution", {}).get("assigned_skills", [])
            assigned_mcp_servers = [
                deepcopy(item)
                for item in resource_snapshot.get("registry", {}).get("mcp_servers", [])
                if item.get("server_ref")
                in distribution.get("distribution", {}).get("assigned_mcp_servers", [])
            ]
            mcp_server_catalog = build_mcp_server_catalog(assigned_mcp_servers)
            runtime_descriptor = deepcopy(descriptor)
            runtime_descriptor.tool_refs = _unique(
                list(runtime_descriptor.tool_refs)
                + [str(item) for item in (resolved_preview.get("resolved_tool_refs") or [])]
                + _runtime_mcp_tool_refs(mcp_server_catalog)
            )
            runtime_descriptor.memory_scopes = _unique(
                list(runtime_descriptor.memory_scopes)
                + [str(item) for item in (resolved_preview.get("resolved_memory_scopes") or [])]
            )
            runtime_descriptor.policy_profiles = _unique(
                list(runtime_descriptor.policy_profiles)
                + [str(item) for item in (resolved_preview.get("resolved_policy_profiles") or [])]
            )
            assigned_skills = [
                deepcopy(item)
                for item in resource_snapshot.get("registry", {}).get("skills", [])
                if item.get("skill_name") in assigned_skill_names
            ]
            assigned_skill_bindings = [
                deepcopy(item)
                for item in (capability_payload.get("skill_bindings") or [])
                if item.get("enabled", True) and item.get("skill_name") in assigned_skill_names
            ]
            runtime_descriptor.metadata = {
                **runtime_descriptor.metadata,
                "capability_metadata": capability_payload,
                "runtime_resource_context": {
                    "mcp_servers": assigned_mcp_servers,
                    "mcp_server_catalog": mcp_server_catalog,
                    "mcp_tools": [
                        deepcopy(tool)
                        for server in mcp_server_catalog
                        for tool in server.get("tools", [])
                    ],
                    "skills": assigned_skills,
                    "skill_bindings": assigned_skill_bindings,
                    "skill_packages": build_runtime_skill_packages(
                        registered_skills=assigned_skills,
                        skill_bindings=assigned_skill_bindings,
                    ),
                    "workspace": deepcopy(
                        distribution.get("distribution", {}).get("workspace")
                    ),
                    "distribution_effectiveness": deepcopy(
                        distribution.get("effectiveness", {})
                    ),
                },
            }
            runtime_descriptors.append(runtime_descriptor)
        return runtime_descriptors

    def get_runtime_descriptor(self, agent_id: str) -> AgentDescriptor:
        for descriptor in self.runtime_descriptors():
            if descriptor.agent_id == agent_id:
                return descriptor
        raise KeyError(f"unknown agent_id '{agent_id}'")
