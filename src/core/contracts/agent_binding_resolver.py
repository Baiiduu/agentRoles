from __future__ import annotations

from typing import Protocol

from core.agents.bindings import ResolvedAgentBinding, ResolvedWorkflowBindings
from core.workflow.workflow_models import CompiledWorkflow, NodeSpec


class AgentBindingResolver(Protocol):
    def resolve_workflow_bindings(
        self, workflow: CompiledWorkflow
    ) -> ResolvedWorkflowBindings: ...

    def resolve_node_binding(self, node_spec: NodeSpec) -> ResolvedAgentBinding | None: ...
