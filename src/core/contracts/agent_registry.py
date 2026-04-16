from __future__ import annotations

from typing import Protocol

from core.agents.models import AgentDescriptor, AgentQuery


class AgentRegistry(Protocol):
    def register(self, descriptor: AgentDescriptor) -> AgentDescriptor: ...

    def get(
        self, agent_id: str, *, version: str | None = None
    ) -> AgentDescriptor | None: ...

    def get_default(self, agent_id: str) -> AgentDescriptor | None: ...

    def list(self, query: AgentQuery | None = None) -> list[AgentDescriptor]: ...

    def resolve(self, agent_ref: str) -> AgentDescriptor | None: ...
