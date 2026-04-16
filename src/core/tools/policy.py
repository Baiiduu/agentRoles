from __future__ import annotations

from copy import deepcopy

from core.contracts.tool_invoker import ToolInvoker
from core.contracts.types import ExecutionContext, ToolInvocationResult
from core.state.models import PolicyAction
from core.tools.models import ToolDescriptor, ToolInvocationRequest, ToolQuery


class PolicyAwareToolInvoker:
    """
    Tool invoker decorator that applies policy checks before a tool call.

    The runtime still only sees `ToolInvocationResult`; policy details remain
    attached as structured decisions so reducers can persist them.
    """

    def __init__(self, delegate: ToolInvoker) -> None:
        self._delegate = delegate

    def invoke(
        self,
        tool_ref: str,
        tool_input: dict[str, object],
        context: ExecutionContext,
    ) -> ToolInvocationResult:
        descriptor = self.get_descriptor(tool_ref)
        if descriptor is None:
            return self._delegate.invoke(tool_ref, tool_input, context)

        services = context.services
        if services is None or services.policy_engine is None:
            return self._delegate.invoke(tool_ref, tool_input, context)

        request = ToolInvocationRequest(
            tool_ref=tool_ref,
            tool_input=deepcopy(tool_input),
            caller_node_id=context.node_state.node_id,
            trace_context=deepcopy(context.trace_context),
        )
        decision = services.policy_engine.pre_tool_invoke(descriptor, request, context)
        if decision.action == PolicyAction.ALLOW:
            result = self._delegate.invoke(tool_ref, request.tool_input, context)
            result.policy_decisions = [decision, *result.policy_decisions]
            result.metadata = {
                "policy_action": str(decision.action),
                **result.metadata,
            }
            return result

        if decision.action == PolicyAction.REDACT and decision.redactions:
            redacted_input = deepcopy(request.tool_input)
            for path in decision.redactions:
                self._redact_path(redacted_input, path)
            result = self._delegate.invoke(tool_ref, redacted_input, context)
            result.policy_decisions = [decision, *result.policy_decisions]
            result.metadata = {
                "policy_action": str(decision.action),
                "redactions": list(decision.redactions),
                **result.metadata,
            }
            return result

        if decision.action == PolicyAction.REQUIRE_APPROVAL:
            return ToolInvocationResult(
                success=False,
                error_code="POLICY_APPROVAL_REQUIRED",
                error_message=decision.reason_message,
                policy_decisions=[decision],
                metadata={
                    "policy_action": str(decision.action),
                    "tool_ref": tool_ref,
                },
            )

        if decision.action == PolicyAction.DENY:
            return ToolInvocationResult(
                success=False,
                error_code="POLICY_DENIED",
                error_message=decision.reason_message,
                policy_decisions=[decision],
                metadata={
                    "policy_action": str(decision.action),
                    "tool_ref": tool_ref,
                },
            )

        return ToolInvocationResult(
            success=False,
            error_code=f"POLICY_{str(decision.action).upper()}",
            error_message=decision.reason_message,
            policy_decisions=[decision],
            metadata={
                "policy_action": str(decision.action),
                "tool_ref": tool_ref,
            },
        )

    def get_descriptor(self, tool_ref: str) -> ToolDescriptor | None:
        return self._delegate.get_descriptor(tool_ref)

    def list_tools(self, query: ToolQuery | None = None) -> list[ToolDescriptor]:
        return self._delegate.list_tools(query)

    def _redact_path(self, payload: dict[str, object], path: str) -> None:
        if not path:
            return
        parts = path.split(".")
        current: object = payload
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return
            current = current[part]
        if isinstance(current, dict):
            current.pop(parts[-1], None)
