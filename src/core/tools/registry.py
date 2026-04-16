from __future__ import annotations

from copy import deepcopy

from core.tools.models import ToolDescriptor, ToolQuery


class InMemoryToolRegistry:
    """Reference registry that keeps tool descriptors immutable to callers."""

    def __init__(self) -> None:
        self._descriptors: dict[str, ToolDescriptor] = {}

    def register(self, descriptor: ToolDescriptor) -> None:
        if descriptor.tool_ref in self._descriptors:
            raise ValueError(f"tool '{descriptor.tool_ref}' is already registered")
        self._descriptors[descriptor.tool_ref] = deepcopy(descriptor)

    def get(self, tool_ref: str) -> ToolDescriptor | None:
        descriptor = self._descriptors.get(tool_ref)
        if descriptor is None:
            return None
        return deepcopy(descriptor)

    def list(self, query: ToolQuery | None = None) -> list[ToolDescriptor]:
        query = query or ToolQuery()
        results: list[ToolDescriptor] = []
        for tool_ref in sorted(self._descriptors):
            descriptor = self._descriptors[tool_ref]
            if query.transport_kind is not None and descriptor.transport_kind != query.transport_kind:
                continue
            if query.side_effect_kind is not None and descriptor.side_effect_kind != query.side_effect_kind:
                continue
            if query.approval_mode is not None and descriptor.approval_mode != query.approval_mode:
                continue
            if query.provider_ref is not None and descriptor.provider_ref != query.provider_ref:
                continue
            if query.tags and not set(query.tags).issubset(set(descriptor.tags)):
                continue
            results.append(deepcopy(descriptor))
        return results
