from __future__ import annotations

from copy import deepcopy
from typing import Callable

from core.contracts.tool_adapter import ToolAdapter
from core.contracts.tool_registry import ToolRegistry
from core.contracts.types import ExecutionContext, ToolInvocationResult
from core.state.models import JsonMap
from core.tools.models import ToolDescriptor, ToolInvocationRequest, ToolQuery, ToolTransportKind


ToolHandler = Callable[[JsonMap, ExecutionContext], ToolInvocationResult | JsonMap | None]


class FunctionToolAdapter:
    """Adapter for local Python-callable tools."""

    adapter_ref = "adapter.function"

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register_handler(self, tool_ref: str, handler: ToolHandler) -> None:
        if tool_ref in self._handlers:
            raise ValueError(f"handler for tool '{tool_ref}' is already registered")
        self._handlers[tool_ref] = handler

    def supports(self, descriptor: ToolDescriptor) -> bool:
        return (
            descriptor.transport_kind == ToolTransportKind.LOCAL_FUNCTION
            and descriptor.tool_ref in self._handlers
        )

    def invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> ToolInvocationResult:
        handler = self._handlers.get(descriptor.tool_ref)
        if handler is None:
            return ToolInvocationResult(
                success=False,
                error_code="TOOL_HANDLER_NOT_FOUND",
                error_message=f"no local handler registered for tool '{descriptor.tool_ref}'",
                metadata={"adapter_ref": self.adapter_ref},
            )

        try:
            raw_result = handler(deepcopy(request.tool_input), context)
        except Exception as exc:  # noqa: BLE001 - normalized into tool result.
            return ToolInvocationResult(
                success=False,
                error_code="TOOL_EXECUTION_ERROR",
                error_message=str(exc),
                metadata={"adapter_ref": self.adapter_ref},
            )

        if isinstance(raw_result, ToolInvocationResult):
            result = deepcopy(raw_result)
        elif raw_result is None:
            result = ToolInvocationResult(success=True, output={})
        elif isinstance(raw_result, dict):
            result = ToolInvocationResult(success=True, output=deepcopy(raw_result))
        else:
            result = ToolInvocationResult(success=True, output={"value": raw_result})

        result.metadata = {
            **result.metadata,
            "adapter_ref": self.adapter_ref,
        }
        return result


class RoutingToolInvoker:
    """Routes tool calls through registered tool descriptors and adapters."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        adapters: list[ToolAdapter],
    ) -> None:
        self._registry = registry
        self._adapters = list(adapters)

    def invoke(
        self,
        tool_ref: str,
        tool_input: dict[str, object],
        context: ExecutionContext,
    ) -> ToolInvocationResult:
        descriptor = self.get_descriptor(tool_ref)
        if descriptor is None:
            return ToolInvocationResult(
                success=False,
                error_code="TOOL_NOT_FOUND",
                error_message=f"tool '{tool_ref}' is not registered",
                metadata={"tool_ref": tool_ref},
            )

        request = ToolInvocationRequest(
            tool_ref=tool_ref,
            tool_input=deepcopy(tool_input),
            caller_node_id=context.node_state.node_id,
            trace_context=deepcopy(context.trace_context),
        )
        adapter = self._select_adapter(descriptor)
        if adapter is None:
            return ToolInvocationResult(
                success=False,
                error_code="TOOL_ADAPTER_NOT_FOUND",
                error_message=f"no adapter can handle tool '{tool_ref}'",
                metadata={
                    "tool_ref": tool_ref,
                    "transport_kind": str(descriptor.transport_kind),
                },
            )

        result = adapter.invoke(descriptor, request, context)
        result.metadata = {
            "tool_ref": descriptor.tool_ref,
            "transport_kind": str(descriptor.transport_kind),
            "provider_ref": descriptor.provider_ref,
            "operation_ref": descriptor.operation_ref,
            "adapter_ref": getattr(adapter, "adapter_ref", None),
            **result.metadata,
        }
        return result

    def get_descriptor(self, tool_ref: str) -> ToolDescriptor | None:
        return self._registry.get(tool_ref)

    def list_tools(self, query: ToolQuery | None = None) -> list[ToolDescriptor]:
        return self._registry.list(query)

    def _select_adapter(self, descriptor: ToolDescriptor) -> ToolAdapter | None:
        preferred = descriptor.metadata.get("adapter_ref")
        if preferred:
            for adapter in self._adapters:
                if getattr(adapter, "adapter_ref", None) == preferred and adapter.supports(descriptor):
                    return adapter
        for adapter in self._adapters:
            if adapter.supports(descriptor):
                return adapter
        return None
