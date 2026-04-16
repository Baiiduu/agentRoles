from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonMap = dict[str, Any]


@dataclass
class AgentSessionRequest:
    agent_id: str
    message: str
    case_id: str | None = None
    session_id: str | None = None
    ephemeral_context: JsonMap = field(default_factory=dict)
    persist_artifact: bool = False

    def __post_init__(self) -> None:
        self.agent_id = self.agent_id.strip()
        self.message = self.message.strip()
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")
        if not self.message:
            raise ValueError("message must be non-empty")


@dataclass
class AgentSessionMessage:
    role: str
    content: str


@dataclass
class AgentArtifactPreview:
    artifact_type: str
    summary: str
    payload: JsonMap = field(default_factory=dict)


@dataclass
class AgentWritebackStatus:
    persisted: bool
    case_id: str | None = None
    message: str | None = None


@dataclass
class AgentSessionResult:
    session_id: str
    status: str
    agent_id: str
    agent_name: str
    messages: list[AgentSessionMessage] = field(default_factory=list)
    artifact_preview: AgentArtifactPreview | None = None
    tool_events: list[JsonMap] = field(default_factory=list)
    resource_events: list[JsonMap] = field(default_factory=list)
    memory_events: list[JsonMap] = field(default_factory=list)
    writeback_status: AgentWritebackStatus = field(
        default_factory=lambda: AgentWritebackStatus(persisted=False)
    )
