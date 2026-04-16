from __future__ import annotations

from copy import deepcopy

from core.agents.bindings import ResolvedAgentBinding, ResolvedWorkflowBindings
from core.contracts.agent_registry import AgentRegistry
from core.state.models import NodeType
from core.workflow.workflow_models import CompiledWorkflow, NodeSpec


class RegistryBackedAgentBindingResolver:
    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def resolve_workflow_bindings(
        self, workflow: CompiledWorkflow
    ) -> ResolvedWorkflowBindings:
        bindings: dict[str, ResolvedAgentBinding] = {}
        for node_spec in workflow.node_map.values():
            binding = self.resolve_node_binding(node_spec)
            if binding is not None:
                bindings[node_spec.node_id] = binding
        return ResolvedWorkflowBindings(
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            agent_bindings_by_node=bindings,
        )

    def resolve_node_binding(self, node_spec: NodeSpec) -> ResolvedAgentBinding | None:
        if node_spec.agent_ref is None:
            return None
        if node_spec.node_type != NodeType.AGENT:
            raise ValueError(
                f"node '{node_spec.node_id}' declares agent_ref but is not an agent node"
            )

        descriptor = self._registry.resolve(node_spec.agent_ref)
        if descriptor is None:
            raise KeyError(
                f"agent_ref '{node_spec.agent_ref}' for node '{node_spec.node_id}' "
                "could not be resolved"
            )

        return ResolvedAgentBinding(
            node_id=node_spec.node_id,
            agent_ref=node_spec.agent_ref,
            resolved_agent_id=descriptor.agent_id,
            resolved_version=descriptor.version,
            executor_ref=descriptor.executor_ref,
            implementation_ref=descriptor.implementation_ref,
            tool_refs=deepcopy(descriptor.tool_refs),
            memory_scopes=deepcopy(descriptor.memory_scopes),
            policy_profiles=deepcopy(descriptor.policy_profiles),
            capabilities=deepcopy(descriptor.capabilities),
            metadata=deepcopy(descriptor.metadata),
        )
