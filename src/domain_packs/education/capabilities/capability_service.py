from __future__ import annotations

from core.agents import AgentDescriptor

from .capability_models import (
    AgentApprovalPolicy,
    AgentHandoffPolicy,
    AgentMCPBinding,
    AgentSkillBinding,
    EducationAgentCapability,
)
from .capability_repository import FileEducationAgentCapabilityRepository
from .capability_resolver import EducationAgentCapabilityResolver


class EducationAgentCapabilityService:
    def __init__(
        self,
        repository: FileEducationAgentCapabilityRepository,
        resolver: EducationAgentCapabilityResolver | None = None,
    ) -> None:
        self._repository = repository
        self._resolver = resolver or EducationAgentCapabilityResolver()

    def list_capabilities(self) -> list[EducationAgentCapability]:
        return self._repository.list_all()

    def get_capability(self, agent_id: str) -> EducationAgentCapability:
        return self._repository.get(agent_id)

    def save_capability(self, payload: dict[str, object]) -> EducationAgentCapability:
        capability = EducationAgentCapability(
            agent_id=str(payload.get("agent_id", "")),
            enabled=bool(payload.get("enabled", True)),
            tool_refs=[str(item) for item in (payload.get("tool_refs") or []) if str(item).strip()],
            memory_scopes=[
                str(item) for item in (payload.get("memory_scopes") or []) if str(item).strip()
            ],
            policy_profiles=[
                str(item) for item in (payload.get("policy_profiles") or []) if str(item).strip()
            ],
            mcp_bindings=[
                AgentMCPBinding(
                    server_ref=str(item.get("server_ref", "")),
                    tool_refs=[str(ref) for ref in (item.get("tool_refs") or []) if str(ref).strip()],
                    enabled=bool(item.get("enabled", True)),
                    usage_notes=str(item.get("usage_notes", "")),
                )
                for item in (payload.get("mcp_bindings") or [])
            ],
            skill_bindings=[
                AgentSkillBinding(
                    skill_name=str(item.get("skill_name", "")),
                    enabled=bool(item.get("enabled", True)),
                    trigger_kinds=[
                        str(ref) for ref in (item.get("trigger_kinds") or []) if str(ref).strip()
                    ],
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
                    if str(item).strip()
                ],
                notes=str((payload.get("approval_policy") or {}).get("notes", "")),
            ),
            handoff_policy=AgentHandoffPolicy(
                mode=str((payload.get("handoff_policy") or {}).get("mode", "manual")),
                allowed_targets=[
                    str(item)
                    for item in ((payload.get("handoff_policy") or {}).get("allowed_targets") or [])
                    if str(item).strip()
                ],
                notes=str((payload.get("handoff_policy") or {}).get("notes", "")),
            ),
            metadata=dict(payload.get("metadata") or {}),
        )
        return self._repository.save(capability)

    def build_preview(
        self,
        descriptor: AgentDescriptor,
        capability: EducationAgentCapability,
    ) -> dict[str, object]:
        return self._resolver.resolve_preview(descriptor, capability)
