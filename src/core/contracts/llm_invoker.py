from __future__ import annotations

from typing import Protocol

from core.llm.models import LLMRequest, LLMResult


class LLMInvoker(Protocol):
    def invoke(self, request: LLMRequest, context=None) -> LLMResult: ...
