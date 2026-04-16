from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from core.agents import AgentDescriptor
from domain_packs import get_registered_agent_descriptors
from infrastructure.persistence import (
    SQLiteAgentCapabilityRepository,
    SQLiteDocumentStore,
    get_persistence_settings,
)

from .standard_agent_capability import (
    StandardAgentCapabilityService,
    StandardAgentCapabilityRepository,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_CAPABILITY_FILE = PROJECT_ROOT / "runtime_data" / "agent_capabilities.json"
LEGACY_EDUCATION_AGENT_CAPABILITY_FILE = (
    PROJECT_ROOT / "runtime_data" / "education" / "agent_capabilities.json"
)
class AgentCapabilityFacade:
    def __init__(self) -> None:
        settings = get_persistence_settings()
        if settings.backend == "sqlite":
            repository = SQLiteAgentCapabilityRepository(
                SQLiteDocumentStore(settings.sqlite_path),
                legacy_file_path=(
                    AGENT_CAPABILITY_FILE
                    if AGENT_CAPABILITY_FILE.exists()
                    else LEGACY_EDUCATION_AGENT_CAPABILITY_FILE
                ),
            )
        else:
            repository = StandardAgentCapabilityRepository(
                AGENT_CAPABILITY_FILE,
                legacy_file_path=LEGACY_EDUCATION_AGENT_CAPABILITY_FILE,
            )
        self._service = StandardAgentCapabilityService(
            repository
        )

    def list_capabilities(self) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        return {
            "agent_capabilities": [
                {
                    **asdict(capability),
                    "name": descriptor_map[capability.agent_id].name
                    if capability.agent_id in descriptor_map
                    else capability.agent_id,
                    "role": descriptor_map[capability.agent_id].role
                    if capability.agent_id in descriptor_map
                    else "unknown",
                    "domain": descriptor_map[capability.agent_id].domain
                    if capability.agent_id in descriptor_map
                    else None,
                    "resolved_preview": self._service.build_preview(
                        descriptor_map[capability.agent_id],
                        capability,
                    )
                    if capability.agent_id in descriptor_map
                    else {},
                }
                for capability in self._service.list_capabilities(descriptors)
            ]
        }

    def get_capability(self, agent_id: str) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        capability = self._service.get_capability(agent_id, descriptors)
        payload = asdict(capability)
        if agent_id in descriptor_map:
            payload["name"] = descriptor_map[agent_id].name
            payload["role"] = descriptor_map[agent_id].role
            payload["domain"] = descriptor_map[agent_id].domain
            payload["resolved_preview"] = self._service.build_preview(
                descriptor_map[agent_id],
                capability,
            )
        return payload

    def save_capability(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        capability = self._service.save_capability({**payload, "agent_id": agent_id}, descriptors)
        result = asdict(capability)
        if agent_id in descriptor_map:
            result["name"] = descriptor_map[agent_id].name
            result["role"] = descriptor_map[agent_id].role
            result["domain"] = descriptor_map[agent_id].domain
            result["resolved_preview"] = self._service.build_preview(
                descriptor_map[agent_id],
                capability,
            )
        return result
