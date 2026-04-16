from __future__ import annotations

from typing import Protocol

from core.state.models import PolicyDecisionRecord, SideEffectRecord
from core.tools.models import ToolDescriptor, ToolInvocationRequest

from .types import ExecutionContext, NodeExecutionResult


class PolicyEngine(Protocol):
    def pre_node_execute(self, context: ExecutionContext) -> PolicyDecisionRecord: ...

    def pre_tool_invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> PolicyDecisionRecord: ...

    def pre_side_effect(
        self, context: ExecutionContext, side_effect: SideEffectRecord
    ) -> PolicyDecisionRecord: ...

    def post_node_execute(
        self, context: ExecutionContext, result: NodeExecutionResult
    ) -> PolicyDecisionRecord | None: ...
