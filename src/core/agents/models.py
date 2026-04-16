from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.state.models import JsonMap


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AgentStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


@dataclass
class AgentDescriptor:
    agent_id: str
    name: str
    version: str
    role: str
    description: str
    executor_ref: str
    status: AgentStatus = AgentStatus.ACTIVE
    domain: str | None = None
    implementation_ref: str | None = None
    tags: list[str] = field(default_factory=list)
    tool_refs: list[str] = field(default_factory=list)
    memory_scopes: list[str] = field(default_factory=list)
    policy_profiles: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    input_contract: JsonMap = field(default_factory=dict)
    output_contract: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("agent_id", self.agent_id),
            ("name", self.name),
            ("version", self.version),
            ("role", self.role),
            ("description", self.description),
            ("executor_ref", self.executor_ref),
        ):
            _require_non_empty(value, field_name)

        for field_name in (
            "tags",
            "tool_refs",
            "memory_scopes",
            "policy_profiles",
            "capabilities",
        ):
            _require_unique(getattr(self, field_name), field_name)


@dataclass
class AgentQuery:
    domain: str | None = None
    role: str | None = None
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    tool_ref: str | None = None
    memory_scope: str | None = None
    status: AgentStatus | None = None

    def __post_init__(self) -> None:
        _require_unique(self.tags, "tags")
        _require_unique(self.capabilities, "capabilities")


def split_agent_ref(agent_ref: str) -> tuple[str, str | None]:
    _require_non_empty(agent_ref, "agent_ref")
    if ":" not in agent_ref:
        return agent_ref, None
    agent_id, version = agent_ref.split(":", 1)
    _require_non_empty(agent_id, "agent_ref.agent_id")
    _require_non_empty(version, "agent_ref.version")
    return agent_id, version
