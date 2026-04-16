from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.agents import AgentDescriptor


JsonMap = dict[str, Any]


@dataclass
class AgentConfig:
    agent_id: str
    enabled: bool
    llm_profile_ref: str
    system_prompt: str
    instruction_appendix: str = ""
    response_style: str = "structured"
    quality_bar: str = ""
    handoff_targets: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agent_id = self.agent_id.strip()
        self.llm_profile_ref = self.llm_profile_ref.strip()
        self.system_prompt = self.system_prompt.strip()
        self.instruction_appendix = self.instruction_appendix.strip()
        self.response_style = self.response_style.strip() or "structured"
        self.quality_bar = self.quality_bar.strip()
        self.handoff_targets = [item.strip() for item in self.handoff_targets if item.strip()]
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")
        if not self.llm_profile_ref:
            raise ValueError("llm_profile_ref must be non-empty")
        if not self.system_prompt:
            raise ValueError("system_prompt must be non-empty")


def default_config_for_descriptor(descriptor: AgentDescriptor) -> AgentConfig:
    metadata = descriptor.metadata if isinstance(descriptor.metadata, dict) else {}
    return AgentConfig(
        agent_id=descriptor.agent_id,
        enabled=True,
        llm_profile_ref=str(metadata.get("llm_profile_ref", "openai.default")).strip() or "openai.default",
        system_prompt=str(metadata.get("system_prompt", descriptor.description)).strip()
        or descriptor.description,
        instruction_appendix=str(metadata.get("instruction_appendix", "")),
        response_style=str(metadata.get("response_style", "structured")),
        quality_bar=str(metadata.get("quality_bar", "")),
        handoff_targets=[str(item) for item in (metadata.get("handoff_targets") or []) if str(item).strip()],
        metadata={"domain": descriptor.domain, "standard_config": True},
    )


class StandardAgentConfigRepository:
    def __init__(self, file_path: Path, *, legacy_file_path: Path | None = None) -> None:
        self._file_path = file_path
        self._legacy_file_path = legacy_file_path

    def list_all(self, descriptors: list[AgentDescriptor]) -> list[AgentConfig]:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        stored = self._read_all()
        by_id = {item.agent_id: item for item in stored}
        merged: list[AgentConfig] = []
        for descriptor in descriptors:
            merged.append(by_id.get(descriptor.agent_id, default_config_for_descriptor(descriptor)))
        for item in stored:
            if item.agent_id not in descriptor_map:
                merged.append(item)
        return merged

    def get(self, agent_id: str, descriptors: list[AgentDescriptor]) -> AgentConfig:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{agent_id}'")
        for item in self._read_all():
            if item.agent_id == agent_id:
                return item
        return default_config_for_descriptor(descriptor_map[agent_id])

    def save(self, config: AgentConfig, descriptors: list[AgentDescriptor]) -> AgentConfig:
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}
        if config.agent_id not in descriptor_map:
            raise KeyError(f"unknown agent_id '{config.agent_id}'")
        payload = self._read_payload()
        items = payload.get("agent_configs", [])
        updated = False
        serialized = asdict(config)
        for index, item in enumerate(items):
            if item.get("agent_id") == config.agent_id:
                items[index] = serialized
                updated = True
                break
        if not updated:
            items.append(serialized)
        payload["agent_configs"] = items
        self._write_payload(payload)
        return config

    def _read_all(self) -> list[AgentConfig]:
        payload = self._read_payload()
        return [AgentConfig(**item) for item in payload.get("agent_configs", [])]

    def _read_payload(self) -> dict[str, object]:
        source = self._file_path
        if not source.exists() and self._legacy_file_path is not None and self._legacy_file_path.exists():
            source = self._legacy_file_path
        if not source.exists():
            return {"agent_configs": []}
        return json.loads(source.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class StandardAgentConfigService:
    def __init__(self, repository: StandardAgentConfigRepository) -> None:
        self._repository = repository

    def list_configs(self, descriptors: list[AgentDescriptor]) -> list[AgentConfig]:
        return self._repository.list_all(descriptors)

    def get_config(self, agent_id: str, descriptors: list[AgentDescriptor]) -> AgentConfig:
        return self._repository.get(agent_id, descriptors)

    def save_config(self, payload: dict[str, object], descriptors: list[AgentDescriptor]) -> AgentConfig:
        config = AgentConfig(
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
        return self._repository.save(config, descriptors)

    def apply_to_descriptor(self, descriptor: AgentDescriptor, config: AgentConfig) -> AgentDescriptor:
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
