from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .models import LLMModelProfile, LLMProviderConfig, LLMProviderKind
from .registry import InMemoryLLMProviderRegistry


@dataclass
class EnvironmentConfigBundle:
    providers: list[LLMProviderConfig] = field(default_factory=list)
    profiles: list[LLMModelProfile] = field(default_factory=list)
    default_profile_ref: str | None = None


class EnvironmentProviderConfigLoader:
    def __init__(self, env_file: Path | None = None) -> None:
        self._env_file = env_file or Path(__file__).resolve().parents[3] / ".env"

    def load(self) -> EnvironmentConfigBundle:
        self._load_env_file()
        providers: list[LLMProviderConfig] = []
        profiles: list[LLMModelProfile] = []

        openai_api_key_env = "AGENTSROLES_OPENAI_API_KEY"
        if os.getenv(openai_api_key_env):
            providers.append(
                LLMProviderConfig(
                    provider_ref="openai",
                    provider_kind=LLMProviderKind.OPENAI,
                    display_name="OpenAI",
                    base_url=os.getenv("AGENTSROLES_OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    api_key_env=openai_api_key_env,
                    default_model=os.getenv("AGENTSROLES_OPENAI_MODEL", "gpt-5"),
                    organization=os.getenv("AGENTSROLES_OPENAI_ORG"),
                    project=os.getenv("AGENTSROLES_OPENAI_PROJECT"),
                )
            )
            profiles.append(
                LLMModelProfile(
                    profile_ref="openai.default",
                    provider_ref="openai",
                    model_name=os.getenv("AGENTSROLES_OPENAI_MODEL", "gpt-5"),
                    temperature=0.2,
                    supports_json_mode=True,
                    supports_system_prompt=True,
                    is_default=os.getenv("AGENTSROLES_DEFAULT_LLM_PROFILE") in {None, "openai.default"},
                )
            )

        deepseek_api_key_env = "AGENTSROLES_DEEPSEEK_API_KEY"
        if os.getenv(deepseek_api_key_env):
            providers.append(
                LLMProviderConfig(
                    provider_ref="deepseek",
                    provider_kind=LLMProviderKind.DEEPSEEK,
                    display_name="DeepSeek",
                    base_url=os.getenv("AGENTSROLES_DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                    api_key_env=deepseek_api_key_env,
                    default_model=os.getenv("AGENTSROLES_DEEPSEEK_MODEL", "deepseek-chat"),
                )
            )
            profiles.append(
                LLMModelProfile(
                    profile_ref="deepseek.default",
                    provider_ref="deepseek",
                    model_name=os.getenv("AGENTSROLES_DEEPSEEK_MODEL", "deepseek-chat"),
                    temperature=0.2,
                    supports_json_mode=True,
                    supports_system_prompt=True,
                    is_default=os.getenv("AGENTSROLES_DEFAULT_LLM_PROFILE") == "deepseek.default",
                )
            )

        profiles.extend(self._build_education_profiles(providers))

        default_profile_ref = self._resolve_default_profile_ref(providers)
        return EnvironmentConfigBundle(
            providers=providers,
            profiles=profiles,
            default_profile_ref=default_profile_ref,
        )

    def build_registry(self) -> tuple[InMemoryLLMProviderRegistry, str | None]:
        bundle = self.load()
        registry = InMemoryLLMProviderRegistry()
        for provider in bundle.providers:
            registry.register_provider(provider)
        for profile in bundle.profiles:
            registry.register_profile(profile)
        return registry, bundle.default_profile_ref

    def _build_education_profiles(
        self,
        providers: list[LLMProviderConfig],
    ) -> list[LLMModelProfile]:
        by_ref = {provider.provider_ref: provider for provider in providers}
        if not by_ref:
            return []

        def pick(preferred: str) -> LLMProviderConfig:
            if preferred in by_ref:
                return by_ref[preferred]
            return next(iter(by_ref.values()))

        mappings = {
            "education.learner_profiler.default": pick("deepseek"),
            "education.curriculum_planner.default": pick("deepseek"),
            "education.exercise_designer.default": pick("deepseek"),
            "education.reviewer_grader.default": pick("deepseek"),
            "education.tutor_coach.default": pick("deepseek"),
        }

        profiles: list[LLMModelProfile] = []
        for profile_ref, provider in mappings.items():
            profiles.append(
                LLMModelProfile(
                    profile_ref=profile_ref,
                    provider_ref=provider.provider_ref,
                    model_name=provider.default_model,
                    temperature=0.2,
                    supports_json_mode=True,
                    supports_system_prompt=True,
                )
            )
        return profiles

    def _resolve_default_profile_ref(
        self,
        providers: list[LLMProviderConfig],
    ) -> str | None:
        provider_refs = {provider.provider_ref for provider in providers}
        if "deepseek" in provider_refs:
            return "deepseek.default"
        if "openai" in provider_refs:
            return "openai.default"
        return os.getenv("AGENTSROLES_DEFAULT_LLM_PROFILE")

    def _load_env_file(self) -> None:
        env_file = self._env_file
        if not env_file.exists():
            return

        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            os.environ.setdefault(key, value)
