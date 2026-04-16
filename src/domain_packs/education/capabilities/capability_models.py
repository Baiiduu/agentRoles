from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonMap = dict[str, Any]


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
class EducationAgentCapability:
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
