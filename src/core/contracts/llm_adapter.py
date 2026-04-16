from __future__ import annotations

from typing import Protocol

from core.llm.models import (
    LLMModelProfile,
    LLMProviderConfig,
    LLMProviderKind,
    LLMRequest,
    LLMResult,
)


class LLMAdapter(Protocol):
    def can_handle(self, provider_kind: LLMProviderKind) -> bool: ...

    def invoke(
        self,
        request: LLMRequest,
        provider_config: LLMProviderConfig,
        profile: LLMModelProfile | None = None,
    ) -> LLMResult: ...
