from __future__ import annotations

from core.agents import AgentImplementation, ResolvedAgentBinding
from core.contracts import ExecutionContext, NodeExecutionResult, NodeExecutor
from core.state.models import NodeStatus, NodeType


class DomainAgentExecutor:
    """
    Generic executor shell for domain-pack agent implementations.

    It consumes `context.agent_binding`, selects one registered implementation,
    and delegates actual domain behavior without pulling registry logic into
    runtime or workflow compilation.
    """

    def __init__(self, implementations: list[AgentImplementation] | None = None) -> None:
        self._implementations = implementations or []

    def can_execute(self, node_type: NodeType, executor_ref: str) -> bool:
        return node_type == NodeType.AGENT and executor_ref.startswith("agent.")

    def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        binding = context.agent_binding
        if binding is None:
            return NodeExecutionResult(
                status=NodeStatus.FAILED,
                error_code="MISSING_AGENT_BINDING",
                error_message="domain agent executor requires context.agent_binding",
            )

        implementation = self._select_implementation(binding)
        return implementation.invoke(context)

    def _select_implementation(self, binding: ResolvedAgentBinding) -> AgentImplementation:
        if binding.implementation_ref:
            direct_matches = [
                implementation
                for implementation in self._implementations
                if getattr(implementation, "implementation_ref", None)
                == binding.implementation_ref
            ]
            if len(direct_matches) == 1:
                return direct_matches[0]
            if len(direct_matches) > 1:
                raise ValueError(
                    "multiple agent implementations matched "
                    f"implementation_ref='{binding.implementation_ref}'"
                )
            raise ValueError(
                "no agent implementation matched "
                f"implementation_ref='{binding.implementation_ref}'"
            )

        candidates = [
            implementation
            for implementation in self._implementations
            if implementation.can_handle(binding)
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(
                "multiple agent implementations can handle "
                f"agent_ref='{binding.agent_ref}'"
            )
        raise ValueError(f"no agent implementation available for agent_ref='{binding.agent_ref}'")
