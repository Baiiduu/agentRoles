from __future__ import annotations

from copy import deepcopy

from .models import AgentDescriptor, AgentQuery, split_agent_ref


def _version_sort_key(version: str) -> tuple[int, ...] | tuple[str]:
    parts = version.split(".")
    if all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return (version,)


class InMemoryAgentRegistry:
    """Reference registry for versioned agent descriptors."""

    def __init__(self) -> None:
        self._descriptors: dict[str, dict[str, AgentDescriptor]] = {}

    def register(self, descriptor: AgentDescriptor) -> AgentDescriptor:
        versions = self._descriptors.setdefault(descriptor.agent_id, {})
        if descriptor.version in versions:
            raise ValueError(
                f"agent '{descriptor.agent_id}' version '{descriptor.version}' is already registered"
            )
        versions[descriptor.version] = deepcopy(descriptor)
        return deepcopy(descriptor)

    def get(
        self, agent_id: str, *, version: str | None = None
    ) -> AgentDescriptor | None:
        versions = self._descriptors.get(agent_id)
        if not versions:
            return None
        if version is not None:
            descriptor = versions.get(version)
            return deepcopy(descriptor) if descriptor is not None else None
        return self.get_default(agent_id)

    def get_default(self, agent_id: str) -> AgentDescriptor | None:
        versions = self._descriptors.get(agent_id)
        if not versions:
            return None
        default_version = max(versions, key=_version_sort_key)
        return deepcopy(versions[default_version])

    def list(self, query: AgentQuery | None = None) -> list[AgentDescriptor]:
        query = query or AgentQuery()
        results: list[AgentDescriptor] = []
        for agent_id in sorted(self._descriptors):
            for version in sorted(self._descriptors[agent_id], key=_version_sort_key):
                descriptor = self._descriptors[agent_id][version]
                if query.domain is not None and descriptor.domain != query.domain:
                    continue
                if query.role is not None and descriptor.role != query.role:
                    continue
                if query.status is not None and descriptor.status != query.status:
                    continue
                if query.tool_ref is not None and query.tool_ref not in descriptor.tool_refs:
                    continue
                if (
                    query.memory_scope is not None
                    and query.memory_scope not in descriptor.memory_scopes
                ):
                    continue
                if query.tags and not set(query.tags).issubset(set(descriptor.tags)):
                    continue
                if query.capabilities and not set(query.capabilities).issubset(
                    set(descriptor.capabilities)
                ):
                    continue
                results.append(deepcopy(descriptor))
        return results

    def resolve(self, agent_ref: str) -> AgentDescriptor | None:
        agent_id, version = split_agent_ref(agent_ref)
        if version is None:
            return self.get_default(agent_id)
        return self.get(agent_id, version=version)
