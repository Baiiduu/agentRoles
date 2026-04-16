from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from core.agents.bindings import ResolvedAgentBinding

if TYPE_CHECKING:
    from core.contracts.types import ExecutionContext, NodeExecutionResult


class AgentImplementation(Protocol):
    implementation_ref: str | None

    def can_handle(self, binding: ResolvedAgentBinding) -> bool: ...

    def invoke(self, context: ExecutionContext) -> NodeExecutionResult: ...
