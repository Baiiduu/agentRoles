from __future__ import annotations

from copy import deepcopy

from .models import LLMModelProfile, LLMProviderConfig


class InMemoryLLMProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProviderConfig] = {}
        self._profiles: dict[str, LLMModelProfile] = {}

    def register_provider(self, config: LLMProviderConfig) -> None:
        if config.provider_ref in self._providers:
            raise ValueError(f"provider '{config.provider_ref}' already registered")
        self._providers[config.provider_ref] = deepcopy(config)

    def register_profile(self, profile: LLMModelProfile) -> None:
        if profile.profile_ref in self._profiles:
            raise ValueError(f"profile '{profile.profile_ref}' already registered")
        if profile.provider_ref not in self._providers:
            raise ValueError(
                f"profile '{profile.profile_ref}' references unknown provider "
                f"'{profile.provider_ref}'"
            )
        self._profiles[profile.profile_ref] = deepcopy(profile)

    def get_provider(self, provider_ref: str) -> LLMProviderConfig | None:
        config = self._providers.get(provider_ref)
        return deepcopy(config) if config is not None else None

    def get_profile(self, profile_ref: str) -> LLMModelProfile | None:
        profile = self._profiles.get(profile_ref)
        return deepcopy(profile) if profile is not None else None

    def list_providers(self) -> list[LLMProviderConfig]:
        return [deepcopy(config) for config in self._providers.values()]

    def list_profiles(self) -> list[LLMModelProfile]:
        return [deepcopy(profile) for profile in self._profiles.values()]

    def get_default_profile(
        self,
        *,
        provider_ref: str | None = None,
    ) -> LLMModelProfile | None:
        candidates = [
            profile
            for profile in self._profiles.values()
            if provider_ref is None or profile.provider_ref == provider_ref
        ]
        defaults = [profile for profile in candidates if profile.is_default]
        if defaults:
            defaults.sort(key=lambda item: item.profile_ref)
            return deepcopy(defaults[0])
        if candidates:
            candidates.sort(key=lambda item: item.profile_ref)
            return deepcopy(candidates[0])
        return None
