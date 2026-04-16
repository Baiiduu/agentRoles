from __future__ import annotations

from typing import Protocol

from core.state.models import NodeType

from .types import ExecutionContext, NodeExecutionResult


class NodeExecutor(Protocol):
    def can_execute(self, node_type: NodeType, executor_ref: str) -> bool: ...

    def execute(self, context: ExecutionContext) -> NodeExecutionResult: ...
