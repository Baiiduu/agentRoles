from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from domain_packs import get_registered_agent_descriptors
from infrastructure.persistence import (
    SQLiteAgentConfigRepository,
    SQLiteDocumentStore,
    get_persistence_settings,
)

from .standard_agent_config import StandardAgentConfigRepository, StandardAgentConfigService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_CONFIG_FILE = PROJECT_ROOT / "runtime_data" / "agent_configs.json"
LEGACY_EDUCATION_AGENT_CONFIG_FILE = PROJECT_ROOT / "runtime_data" / "education" / "agent_configs.json"

class AgentConfigFacade:
    def __init__(self) -> None:
        settings = get_persistence_settings()
        if settings.backend == "sqlite":
            repository = SQLiteAgentConfigRepository(
                SQLiteDocumentStore(settings.sqlite_path),
                legacy_file_path=(AGENT_CONFIG_FILE if AGENT_CONFIG_FILE.exists() else LEGACY_EDUCATION_AGENT_CONFIG_FILE),
            )
        else:
            repository = StandardAgentConfigRepository(
                AGENT_CONFIG_FILE,
                legacy_file_path=LEGACY_EDUCATION_AGENT_CONFIG_FILE,
            )
        self._service = StandardAgentConfigService(
            repository
        )

    def list_configs(self) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        return {
            "agent_configs": [
                {
                    **asdict(config),
                    "name": descriptor_map[config.agent_id].name if config.agent_id in descriptor_map else config.agent_id,
                    "role": descriptor_map[config.agent_id].role if config.agent_id in descriptor_map else "unknown",
                    "domain": descriptor_map[config.agent_id].domain if config.agent_id in descriptor_map else None,
                }
                for config in self._service.list_configs(descriptors)
            ]
        }

    def get_config(self, agent_id: str) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        config = self._service.get_config(agent_id, descriptors)
        payload = asdict(config)
        if agent_id in descriptor_map:
            payload["name"] = descriptor_map[agent_id].name
            payload["role"] = descriptor_map[agent_id].role
            payload["domain"] = descriptor_map[agent_id].domain
        return payload

    def save_config(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        config = self._service.save_config({**payload, "agent_id": agent_id}, descriptors)
        result = asdict(config)
        if agent_id in descriptor_map:
            result["name"] = descriptor_map[agent_id].name
            result["role"] = descriptor_map[agent_id].role
            result["domain"] = descriptor_map[agent_id].domain
        return result

    def configured_descriptors(self):
        descriptors = get_registered_agent_descriptors()
        return [
            self._service.apply_to_descriptor(
                descriptor,
                self._service.get_config(descriptor.agent_id, descriptors),
            )
            for descriptor in descriptors
        ]
