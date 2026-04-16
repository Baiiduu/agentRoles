from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from core.agents import AgentDescriptor

from .agent_config_models import EducationAgentConfig
from .agent_config_repository import FileEducationAgentConfigRepository


class EducationAgentConfigService:
    def __init__(self, repository: FileEducationAgentConfigRepository) -> None:
        self._repository = repository

    def list_configs(self) -> list[EducationAgentConfig]:
        return self._repository.list_all()

    def get_config(self, agent_id: str) -> EducationAgentConfig:
        return self._repository.get(agent_id)

    def save_config(self, payload: dict[str, object]) -> EducationAgentConfig:
        config = EducationAgentConfig(
            agent_id=str(payload.get("agent_id", "")),
            enabled=bool(payload.get("enabled", True)),
            llm_profile_ref=str(payload.get("llm_profile_ref", "")),
            system_prompt=str(payload.get("system_prompt", "")),
            instruction_appendix=str(payload.get("instruction_appendix", "")),
            response_style=str(payload.get("response_style", "structured")),
            quality_bar=str(payload.get("quality_bar", "")),
            handoff_targets=[
                str(item) for item in (payload.get("handoff_targets") or []) if str(item).strip()
            ],
            metadata=dict(payload.get("metadata") or {}),
        )
        return self._repository.save(config)

    def apply_to_descriptor(self, descriptor: AgentDescriptor) -> AgentDescriptor:
        config = self.get_config(descriptor.agent_id)
        configured = deepcopy(descriptor)
        configured.metadata = {
            **configured.metadata,
            "llm_profile_ref": config.llm_profile_ref,
            "system_prompt": config.system_prompt,
            "instruction_appendix": config.instruction_appendix,
            "response_style": config.response_style,
            "quality_bar": config.quality_bar,
            "handoff_targets": list(config.handoff_targets),
            "config_metadata": asdict(config),
        }
        return configured
