from __future__ import annotations

from copy import deepcopy

from core.contracts import ExecutionContext, NodeExecutionResult, NodeExecutor
from core.state.models import InterruptRecord, InterruptType, NodeStatus, NodeType, PolicyAction


class ToolNodeExecutor:
    """
    Executes `NodeType.TOOL` nodes through the ToolInvoker contract.

    This keeps runtime and workflow nodes isolated from concrete tool protocols
    such as local functions, MCP, HTTP, or command execution.
    """

    def can_execute(self, node_type: NodeType, executor_ref: str) -> bool:
        return node_type == NodeType.TOOL or executor_ref.startswith("tool.")

    def execute(self, context: ExecutionContext) -> NodeExecutionResult:
        services = context.services
        if services is None or services.tool_invoker is None:
            raise ValueError("tool executor requires RuntimeServices.tool_invoker")

        tool_ref = self._resolve_tool_ref(context)
        result = services.tool_invoker.invoke(
            tool_ref,
            deepcopy(context.selected_input),
            context,
        )
        if any(
            decision.action == PolicyAction.REQUIRE_APPROVAL
            for decision in result.policy_decisions
        ):
            return NodeExecutionResult(
                status=NodeStatus.WAITING,
                output={},
                interrupts=[self._approval_interrupt(context, tool_ref, result)],
                policy_decisions=deepcopy(result.policy_decisions),
                metadata={
                    "tool_ref": tool_ref,
                    "tool_metadata": deepcopy(result.metadata),
                },
            )
        if result.success:
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output=deepcopy(result.output or {}),
                policy_decisions=deepcopy(result.policy_decisions),
                side_effects=deepcopy(result.side_effects),
                metadata={
                    "tool_ref": tool_ref,
                    "tool_metadata": deepcopy(result.metadata),
                },
            )
        return NodeExecutionResult(
            status=NodeStatus.FAILED,
            error_code=result.error_code or "TOOL_INVOCATION_FAILED",
            error_message=result.error_message or f"tool '{tool_ref}' invocation failed",
            policy_decisions=deepcopy(result.policy_decisions),
            side_effects=deepcopy(result.side_effects),
            metadata={
                "tool_ref": tool_ref,
                "tool_metadata": deepcopy(result.metadata),
            },
        )

    def _resolve_tool_ref(self, context: ExecutionContext) -> str:
        tool_ref = context.node_spec.config.get("tool_ref")
        if tool_ref is None:
            tool_ref = context.node_spec.metadata.get("tool_ref")
        if tool_ref is None and context.node_spec.executor_ref.startswith("tool."):
            tool_ref = context.node_spec.executor_ref.removeprefix("tool.")
        if not isinstance(tool_ref, str) or not tool_ref:
            raise ValueError(
                f"tool node '{context.node_state.node_id}' must declare a non-empty tool_ref"
            )
        return tool_ref

    def _approval_interrupt(
        self,
        context: ExecutionContext,
        tool_ref: str,
        result,
    ) -> InterruptRecord:
        services = context.services
        if services is None:
            raise ValueError("tool executor requires RuntimeServices for approval interrupts")
        decision = next(
            item for item in result.policy_decisions if item.action == PolicyAction.REQUIRE_APPROVAL
        )
        interrupt_id = services.id_generator.new("interrupt")
        return InterruptRecord(
            interrupt_id=interrupt_id,
            run_id=context.run_record.run_id,
            thread_id=context.thread_record.thread_id,
            node_id=context.node_state.node_id,
            interrupt_type=InterruptType.APPROVAL_REQUIRED,
            reason_code=decision.reason_code,
            reason_message=decision.reason_message,
            payload={
                "tool_ref": tool_ref,
                "decision_id": decision.decision_id,
                "policy_name": decision.policy_name,
            },
        )
