from __future__ import annotations

from dataclasses import dataclass, field

from core.state.models import JsonMap, NodeId, WorkflowId


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


@dataclass
class ResolvedAgentBinding:
    node_id: NodeId
    agent_ref: str
    resolved_agent_id: str
    resolved_version: str
    executor_ref: str
    implementation_ref: str | None = None
    tool_refs: list[str] = field(default_factory=list)
    memory_scopes: list[str] = field(default_factory=list)
    policy_profiles: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("node_id", self.node_id),
            ("agent_ref", self.agent_ref),
            ("resolved_agent_id", self.resolved_agent_id),
            ("resolved_version", self.resolved_version),
            ("executor_ref", self.executor_ref),
        ):
            _require_non_empty(value, field_name)

        for field_name in (
            "tool_refs",
            "memory_scopes",
            "policy_profiles",
            "capabilities",
        ):
            _require_unique(getattr(self, field_name), field_name)

    def to_map(self) -> JsonMap:
        return {
            "node_id": self.node_id,
            "agent_ref": self.agent_ref,
            "resolved_agent_id": self.resolved_agent_id,
            "resolved_version": self.resolved_version,
            "executor_ref": self.executor_ref,
            "implementation_ref": self.implementation_ref,
            "tool_refs": list(self.tool_refs),
            "memory_scopes": list(self.memory_scopes),
            "policy_profiles": list(self.policy_profiles),
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_map(cls, payload: JsonMap) -> "ResolvedAgentBinding":
        return cls(
            node_id=str(payload["node_id"]),
            agent_ref=str(payload["agent_ref"]),
            resolved_agent_id=str(payload["resolved_agent_id"]),
            resolved_version=str(payload["resolved_version"]),
            executor_ref=str(payload["executor_ref"]),
            implementation_ref=payload.get("implementation_ref"),
            tool_refs=list(payload.get("tool_refs", [])),
            memory_scopes=list(payload.get("memory_scopes", [])),
            policy_profiles=list(payload.get("policy_profiles", [])),
            capabilities=list(payload.get("capabilities", [])),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass
class ResolvedWorkflowBindings:
    workflow_id: WorkflowId
    workflow_version: str
    agent_bindings_by_node: dict[NodeId, ResolvedAgentBinding] = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.workflow_id, "workflow_id")
        _require_non_empty(self.workflow_version, "workflow_version")

    def get(self, node_id: NodeId) -> ResolvedAgentBinding | None:
        return self.agent_bindings_by_node.get(node_id)

    def to_extension_map(self) -> JsonMap:
        return {
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "agent_bindings_by_node": {
                node_id: binding.to_map()
                for node_id, binding in self.agent_bindings_by_node.items()
            },
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_extension_map(cls, payload: JsonMap) -> "ResolvedWorkflowBindings":
        return cls(
            workflow_id=str(payload["workflow_id"]),
            workflow_version=str(payload["workflow_version"]),
            agent_bindings_by_node={
                node_id: ResolvedAgentBinding.from_map(binding_payload)
                for node_id, binding_payload in dict(
                    payload.get("agent_bindings_by_node", {})
                ).items()
            },
            metadata=dict(payload.get("metadata", {})),
        )
