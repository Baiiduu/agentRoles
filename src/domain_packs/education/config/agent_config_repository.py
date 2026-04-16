from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .agent_config_models import EducationAgentConfig


class FileEducationAgentConfigRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def list_all(self) -> list[EducationAgentConfig]:
        payload = self._read_payload()
        return [EducationAgentConfig(**item) for item in payload.get("agent_configs", [])]

    def get(self, agent_id: str) -> EducationAgentConfig:
        for item in self.list_all():
            if item.agent_id == agent_id:
                return item
        raise KeyError(f"unknown agent_id '{agent_id}'")

    def save(self, config: EducationAgentConfig) -> EducationAgentConfig:
        payload = self._read_payload()
        items = payload.get("agent_configs", [])
        updated = False
        for index, item in enumerate(items):
            if item.get("agent_id") == config.agent_id:
                items[index] = asdict(config)
                updated = True
                break
        if not updated:
            items.append(asdict(config))
        payload["agent_configs"] = items
        self._write_payload(payload)
        return config

    def _read_payload(self) -> dict[str, object]:
        if not self._file_path.exists():
            raise FileNotFoundError(f"agent config file not found: {self._file_path}")
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
