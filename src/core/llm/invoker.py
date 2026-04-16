from __future__ import annotations

from copy import deepcopy

from core.contracts.llm_adapter import LLMAdapter
from core.contracts.llm_provider_registry import LLMProviderRegistry

from .models import (
    LLMModelProfile,
    LLMProviderConfig,
    LLMRequest,
    LLMResult,
)


class RoutingLLMInvoker:
    def __init__(
        self,
        *,
        registry: LLMProviderRegistry,
        adapters: list[LLMAdapter] | None = None,
        default_profile_ref: str | None = None,
    ) -> None:
        self._registry = registry
        self._adapters = adapters or []
        self._default_profile_ref = default_profile_ref

    def invoke(self, request: LLMRequest, context=None) -> LLMResult:
        provider_config, profile = self._resolve_provider_and_profile(request)
        adapter = self._select_adapter(provider_config.provider_kind)
        materialized_request = self._materialize_request(
            request,
            provider_config=provider_config,
            profile=profile,
        )
        return adapter.invoke(materialized_request, provider_config, profile)

    def _resolve_provider_and_profile(
        self,
        request: LLMRequest,
    ) -> tuple[LLMProviderConfig, LLMModelProfile | None]:
        profile: LLMModelProfile | None = None
        if request.profile_ref:
            profile = self._registry.get_profile(request.profile_ref)
            if profile is None:
                raise ValueError(f"LLM_PROFILE_NOT_FOUND: '{request.profile_ref}'")

        if profile is None and self._default_profile_ref:
            profile = self._registry.get_profile(self._default_profile_ref)
            if profile is None:
                raise ValueError(
                    f"LLM_PROFILE_NOT_FOUND: '{self._default_profile_ref}'"
                )

        if profile is None and request.provider_ref is not None:
            profile = getattr(self._registry, "get_default_profile", lambda **_: None)(
                provider_ref=request.provider_ref
            )

        if profile is None:
            profile = getattr(self._registry, "get_default_profile", lambda **_: None)()

        provider_ref = request.provider_ref or (profile.provider_ref if profile else None)
        if provider_ref is None:
            raise ValueError(
                "LLM_PROVIDER_NOT_FOUND: request must declare provider_ref or resolve a profile"
            )

        provider_config = self._registry.get_provider(provider_ref)
        if provider_config is None:
            raise ValueError(f"LLM_PROVIDER_NOT_FOUND: '{provider_ref}'")

        return provider_config, profile

    def _select_adapter(self, provider_kind):
        for adapter in self._adapters:
            if adapter.can_handle(provider_kind):
                return adapter
        raise ValueError(f"LLM_ADAPTER_NOT_FOUND: '{provider_kind}'")

    def _materialize_request(
        self,
        request: LLMRequest,
        *,
        provider_config: LLMProviderConfig,
        profile: LLMModelProfile | None,
    ) -> LLMRequest:
        materialized = deepcopy(request)
        materialized.provider_ref = provider_config.provider_ref
        if materialized.model_name is None:
            if profile is not None:
                materialized.model_name = profile.model_name
            else:
                materialized.model_name = provider_config.default_model
        if materialized.temperature is None and profile is not None:
            materialized.temperature = profile.temperature
        if materialized.max_output_tokens is None and profile is not None:
            materialized.max_output_tokens = profile.max_output_tokens
        if materialized.top_p is None and profile is not None:
            materialized.top_p = profile.top_p
        return materialized
