from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkspaceRootConfig:
    root_path: str = ""
    enabled: bool = False
    provisioned: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        self.root_path = self.root_path.strip()
        self.notes = self.notes.strip()


@dataclass
class RegisteredMCPServer:
    server_ref: str
    name: str
    description: str = ""
    connection_mode: str = "internal"
    transport_kind: str = "custom"
    command: str = ""
    args: list[str] = field(default_factory=list)
    endpoint: str = ""
    env: dict[str, str] = field(default_factory=dict)
    cwd: str = ""
    tool_refs: list[str] = field(default_factory=list)
    discovered_tool_refs: list[str] = field(default_factory=list)
    enabled: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        self.server_ref = self.server_ref.strip()
        self.name = self.name.strip() or self.server_ref
        self.description = self.description.strip()
        self.connection_mode = self.connection_mode.strip() or "internal"
        self.transport_kind = self.transport_kind.strip() or "custom"
        self.command = self.command.strip()
        self.args = [item.strip() for item in self.args if item.strip()]
        self.endpoint = self.endpoint.strip()
        self.env = {
            str(key).strip(): str(value).strip()
            for key, value in self.env.items()
            if str(key).strip()
        }
        self.cwd = self.cwd.strip()
        self.tool_refs = [item.strip() for item in self.tool_refs if item.strip()]
        self.discovered_tool_refs = [item.strip() for item in self.discovered_tool_refs if item.strip()]
        self.notes = self.notes.strip()
        if not self.server_ref:
            raise ValueError("server_ref must be non-empty")
        if self.connection_mode not in {"internal", "external"}:
            raise ValueError("connection_mode must be internal or external")
        if self.transport_kind not in {"stdio", "sse", "streamable_http", "custom"}:
            raise ValueError("transport_kind must be stdio, sse, streamable_http, or custom")


@dataclass
class RegisteredSkill:
    skill_name: str
    name: str
    description: str = ""
    trigger_kinds: list[str] = field(default_factory=list)
    enabled: bool = True
    notes: str = ""
    source_kind: str = "manual"
    source_path: str = ""
    prompt_file: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.skill_name = self.skill_name.strip()
        self.name = self.name.strip() or self.skill_name
        self.description = self.description.strip()
        self.trigger_kinds = [item.strip() for item in self.trigger_kinds if item.strip()]
        self.notes = self.notes.strip()
        self.source_kind = self.source_kind.strip() or "manual"
        self.source_path = self.source_path.strip()
        self.prompt_file = self.prompt_file.strip()
        self.metadata = {
            str(key).strip(): value
            for key, value in self.metadata.items()
            if str(key).strip()
        }
        if not self.skill_name:
            raise ValueError("skill_name must be non-empty")


@dataclass
class RegisteredSkillSource:
    source_ref: str
    source_kind: str = "custom"
    root_path: str = ""
    label: str = ""
    enabled: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        self.source_ref = self.source_ref.strip()
        self.source_kind = self.source_kind.strip() or "custom"
        self.root_path = self.root_path.strip()
        self.label = self.label.strip() or self.source_ref
        self.notes = self.notes.strip()
        if not self.source_ref:
            raise ValueError("source_ref must be non-empty")
        if not self.root_path:
            raise ValueError("root_path must be non-empty")


@dataclass
class AgentWorkspaceRegistration:
    agent_id: str
    relative_path: str
    enabled: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        self.agent_id = self.agent_id.strip()
        self.relative_path = self.relative_path.strip()
        self.notes = self.notes.strip()
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")
        if not self.relative_path:
            raise ValueError("relative_path must be non-empty")


@dataclass
class ResourceRegistry:
    workspace_root: WorkspaceRootConfig = field(default_factory=WorkspaceRootConfig)
    mcp_servers: list[RegisteredMCPServer] = field(default_factory=list)
    skills: list[RegisteredSkill] = field(default_factory=list)
    skill_sources: list[RegisteredSkillSource] = field(default_factory=list)
    agent_workspaces: list[AgentWorkspaceRegistration] = field(default_factory=list)


EducationResourceRegistry = ResourceRegistry
