from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.agents import AgentDescriptor


JsonMap = dict[str, Any]


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


@dataclass
class AgentMCPBinding:
    server_ref: str
    tool_refs: list[str] = field(default_factory=list)
    enabled: bool = True
    usage_notes: str = ""

    def __post_init__(self) -> None:
        self.server_ref = self.server_ref.strip()
        self.tool_refs = [item.strip() for item in self.tool_refs if item.strip()]
        self.usage_notes = self.usage_notes.strip()
        if not self.server_ref:
            raise ValueError("server_ref must be non-empty")


@dataclass
class AgentSkillBinding:
    skill_name: str
    enabled: bool = True
    trigger_kinds: list[str] = field(default_factory=list)
    scope: str = "session"
    execution_mode: str = "human_confirmed"
    usage_notes: str = ""

    def __post_init__(self) -> None:
        self.skill_name = self.skill_name.strip()
        self.trigger_kinds = [item.strip() for item in self.trigger_kinds if item.strip()]
        self.scope = self.scope.strip() or "session"
        self.execution_mode = self.execution_mode.strip() or "human_confirmed"
        self.usage_notes = self.usage_notes.strip()
        if not self.skill_name:
            raise ValueError("skill_name must be non-empty")
        if self.execution_mode not in {"advisory", "human_confirmed", "auto"}:
            raise ValueError("skill execution_mode must be advisory, human_confirmed, or auto")


@dataclass
class AgentApprovalPolicy:
    mode: str = "none"
    required_targets: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        self.mode = self.mode.strip() or "none"
        self.required_targets = [item.strip() for item in self.required_targets if item.strip()]
        self.notes = self.notes.strip()
        if self.mode not in {"none", "human_review", "required"}:
            raise ValueError("approval mode must be none, human_review, or required")


@dataclass
class AgentHandoffPolicy:
    mode: str = "manual"
    allowed_targets: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        self.mode = self.mode.strip() or "manual"
        self.allowed_targets = [item.strip() for item in self.allowed_targets if item.strip()]
        self.notes = self.notes.strip()
        if self.mode not in {"manual", "guided", "blocked"}:
            raise ValueError("handoff mode must be manual, guided, or blocked")


@dataclass
class AgentCapability:
    agent_id: str
    enabled: bool = True
    tool_refs: list[str] = field(default_factory=list)
    memory_scopes: list[str] = field(default_factory=list)
    policy_profiles: list[str] = field(default_factory=list)
    mcp_bindings: list[AgentMCPBinding] = field(default_factory=list)
    skill_bindings: list[AgentSkillBinding] = field(default_factory=list)
    approval_policy: AgentApprovalPolicy = field(default_factory=AgentApprovalPolicy)
    handoff_policy: AgentHandoffPolicy = field(default_factory=AgentHandoffPolicy)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agent_id = self.agent_id.strip()
        self.tool_refs = [item.strip() for item in self.tool_refs if item.strip()]
        self.memory_scopes = [item.strip() for item in self.memory_scopes if item.strip()]
        self.policy_profiles = [item.strip() for item in self.policy_profiles if item.strip()]
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")


def hydrate_capability(payload: dict[str, object]) -> AgentCapability:
    return AgentCapability(
        agent_id=str(payload.get("agent_id", "")),
        enabled=bool(payload.get("enabled", True)),
        tool_refs=[str(item) for item in (payload.get("tool_refs") or [])],
        memory_scopes=[str(item) for item in (payload.get("memory_scopes") or [])],
        policy_profiles=[str(item) for item in (payload.get("policy_profiles") or [])],
        mcp_bindings=[
            AgentMCPBinding(
                server_ref=str(item.get("server_ref", "")),
                tool_refs=[str(ref) for ref in (item.get("tool_refs") or [])],
                enabled=bool(item.get("enabled", True)),
                usage_notes=str(item.get("usage_notes", "")),
            )
            for item in (payload.get("mcp_bindings") or [])
        ],
        skill_bindings=[
            AgentSkillBinding(
                skill_name=str(item.get("skill_name", "")),
                enabled=bool(item.get("enabled", True)),
                trigger_kinds=[str(ref) for ref in (item.get("trigger_kinds") or [])],
                scope=str(item.get("scope", "session")),
                execution_mode=str(item.get("execution_mode", "human_confirmed")),
                usage_notes=str(item.get("usage_notes", "")),
            )
            for item in (payload.get("skill_bindings") or [])
        ],
        approval_policy=AgentApprovalPolicy(
            mode=str((payload.get("approval_policy") or {}).get("mode", "none")),
            required_targets=[
                str(item)
                for item in ((payload.get("approval_policy") or {}).get("required_targets") or [])
            ],
            notes=str((payload.get("approval_policy") or {}).get("notes", "")),
        ),
        handoff_policy=AgentHandoffPolicy(
            mode=str((payload.get("handoff_policy") or {}).get("mode", "manual")),
            allowed_targets=[
                str(item)
                for item in ((payload.get("handoff_policy") or {}).get("allowed_targets") or [])
            ],
            notes=str((payload.get("handoff_policy") or {}).get("notes", "")),
        ),
        metadata=dict(payload.get("metadata") or {}),
    )


def default_capability_for_descriptor(descriptor: AgentDescriptor) -> AgentCapability:
    return AgentCapability(
        agent_id=descriptor.agent_id,
        enabled=True,
        metadata={
            "domain": descriptor.domain,
            "standard_capability": True,
        },
    )


class StandardAgentCapabilityRepository:
    def __init__(self, file_path: Path, *, legacy_file_path: Path | None = None) -> None:
        self._file_path = file_path
        self._legacy_file_path = legacy_file_path

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
        for item in self._read_all():
            if item.agent_id == agent_id:
                return item
        return default_capability_for_descriptor(descriptor_map[agent_id])

    def save(self, capability: AgentCapability, descriptors: list[AgentDescriptor]) -> AgentCapability:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if capability.agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{capability.agent_id}'")
        payload = self._read_payload()
        items = payload.get("agent_capabilities", [])
        updated = False
        serialized = asdict(capability)
        for index, item in enumerate(items):
            if item.get("agent_id") == capability.agent_id:
                items[index] = serialized
                updated = True
                break
        if not updated:
            items.append(serialized)
        payload["agent_capabilities"] = items
        self._write_payload(payload)
        return capability

    def _read_all(self) -> list[AgentCapability]:
        payload = self._read_payload()
        return [hydrate_capability(item) for item in payload.get("agent_capabilities", [])]

    def _read_payload(self) -> dict[str, object]:
        source = self._file_path
        if not source.exists() and self._legacy_file_path is not None and self._legacy_file_path.exists():
            source = self._legacy_file_path
        if not source.exists():
            return {"agent_capabilities": []}
        return json.loads(source.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class StandardAgentCapabilityResolver:
    def resolve_preview(
        self,
        descriptor: AgentDescriptor,
        capability: AgentCapability,
    ) -> dict[str, object]:
        mcp_tool_refs = _unique(
            [
                tool_ref
                for binding in capability.mcp_bindings
                if binding.enabled
                for tool_ref in binding.tool_refs
            ]
        )
        enabled_skills = [binding.skill_name for binding in capability.skill_bindings if binding.enabled]
        resolved_tool_refs = _unique(list(descriptor.tool_refs) + list(capability.tool_refs) + mcp_tool_refs)
        resolved_memory_scopes = _unique(list(descriptor.memory_scopes) + list(capability.memory_scopes))
        resolved_policy_profiles = _unique(
            list(descriptor.policy_profiles) + list(capability.policy_profiles)
        )
        workspace = capability.metadata.get("workspace", {})
        workspace_relative_path = ""
        workspace_enabled = False
        if isinstance(workspace, dict):
            workspace_relative_path = str(workspace.get("relative_path", "")).strip()
            workspace_enabled = bool(workspace.get("enabled", False))
        approval_mode = capability.approval_policy.mode
        handoff_mode = capability.handoff_policy.mode

        usage_guidance: list[str] = []
        if not capability.enabled:
            usage_guidance.append("This agent capability is currently disabled for active work.")
        if resolved_tool_refs:
            usage_guidance.append(
                f"Operational surface includes {len(resolved_tool_refs)} tool reference(s)."
            )
        if capability.mcp_bindings:
            usage_guidance.append(
                f"MCP access is configured through {len([binding for binding in capability.mcp_bindings if binding.enabled])} enabled server binding(s)."
            )
        if enabled_skills:
            usage_guidance.append(
                f"Skill support is available through {len(enabled_skills)} enabled skill binding(s)."
            )
        if workspace_enabled and workspace_relative_path:
            usage_guidance.append(
                f"Agent workspace is provisioned at '{workspace_relative_path}' for project-local file operations."
            )
        if approval_mode in {"human_review", "required"}:
            usage_guidance.append(
                "Human confirmation should be expected before sensitive or externally visible actions."
            )
        if handoff_mode == "guided":
            usage_guidance.append("Agent handoff should follow the configured target allowlist.")
        if handoff_mode == "blocked":
            usage_guidance.append("This agent should not be selected as the next manual handoff target.")

        attention_points: list[str] = []
        if not capability.enabled:
            attention_points.append("Capability disabled")
        if approval_mode == "required":
            attention_points.append("Requires explicit approval")
        elif approval_mode == "human_review":
            attention_points.append("Needs human review for selected actions")
        if handoff_mode == "guided" and capability.handoff_policy.allowed_targets:
            attention_points.append(
                f"Handoff limited to {len(capability.handoff_policy.allowed_targets)} target(s)"
            )
        elif handoff_mode == "blocked":
            attention_points.append("Manual handoff blocked")

        operational_summary = (
            "Ready for live work."
            if capability.enabled
            else "Not ready for live work until re-enabled."
        )
        collaboration_summary = f"Approval mode: {approval_mode}; handoff mode: {handoff_mode}."
        return {
            "agent_id": descriptor.agent_id,
            "resolved_tool_refs": resolved_tool_refs,
            "resolved_memory_scopes": resolved_memory_scopes,
            "resolved_policy_profiles": resolved_policy_profiles,
            "enabled_mcp_servers": [
                binding.server_ref for binding in capability.mcp_bindings if binding.enabled
            ],
            "enabled_skills": enabled_skills,
            "approval_policy": asdict(capability.approval_policy),
            "handoff_policy": asdict(capability.handoff_policy),
            "workspace": {
                "relative_path": workspace_relative_path,
                "enabled": workspace_enabled,
            },
            "operational_summary": operational_summary,
            "collaboration_summary": collaboration_summary,
            "usage_guidance": usage_guidance,
            "attention_points": attention_points,
        }


class StandardAgentCapabilityService:
    def __init__(
        self,
        repository: StandardAgentCapabilityRepository,
        resolver: StandardAgentCapabilityResolver | None = None,
    ) -> None:
        self._repository = repository
        self._resolver = resolver or StandardAgentCapabilityResolver()

    def list_capabilities(self, descriptors: list[AgentDescriptor]) -> list[AgentCapability]:
        return self._repository.list_all(descriptors)

    def get_capability(self, agent_id: str, descriptors: list[AgentDescriptor]) -> AgentCapability:
        return self._repository.get(agent_id, descriptors)

    def save_capability(
        self,
        payload: dict[str, object],
        descriptors: list[AgentDescriptor],
    ) -> AgentCapability:
        capability = hydrate_capability(payload)
        return self._repository.save(capability, descriptors)

    def build_preview(
        self,
        descriptor: AgentDescriptor,
        capability: AgentCapability,
    ) -> dict[str, object]:
        return self._resolver.resolve_preview(descriptor, capability)
