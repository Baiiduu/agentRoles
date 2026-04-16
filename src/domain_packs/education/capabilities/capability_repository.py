from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .capability_models import (
    AgentApprovalPolicy,
    AgentHandoffPolicy,
    AgentMCPBinding,
    AgentSkillBinding,
    EducationAgentCapability,
)


def _hydrate_capability(payload: dict[str, object]) -> EducationAgentCapability:
    return EducationAgentCapability(
        agent_id=str(payload.get("agent_id", "")),
        enabled=bool(payload.get("enabled", True)),
        tool_refs=[str(item) for item in (payload.get("tool_refs") or [])],
        memory_scopes=[str(item) for item in (payload.get("memory_scopes") or [])],
        policy_profiles=[str(item) for item in (payload.get("policy_profiles") or [])],
        mcp_bindings=[
            AgentMCPBinding(
                server_ref=str(item.get("server_ref", "")),
                tool_refs=[str(ref) for ref in (item.get("tool_refs") or [])],
                enabled=bool(item.get("enabled", True)),
                usage_notes=str(item.get("usage_notes", "")),
            )
            for item in (payload.get("mcp_bindings") or [])
        ],
        skill_bindings=[
            AgentSkillBinding(
                skill_name=str(item.get("skill_name", "")),
                enabled=bool(item.get("enabled", True)),
                trigger_kinds=[str(ref) for ref in (item.get("trigger_kinds") or [])],
                scope=str(item.get("scope", "session")),
                execution_mode=str(item.get("execution_mode", "human_confirmed")),
                usage_notes=str(item.get("usage_notes", "")),
            )
            for item in (payload.get("skill_bindings") or [])
        ],
        approval_policy=AgentApprovalPolicy(
            mode=str((payload.get("approval_policy") or {}).get("mode", "none")),
            required_targets=[
                str(item)
                for item in ((payload.get("approval_policy") or {}).get("required_targets") or [])
            ],
            notes=str((payload.get("approval_policy") or {}).get("notes", "")),
        ),
        handoff_policy=AgentHandoffPolicy(
            mode=str((payload.get("handoff_policy") or {}).get("mode", "manual")),
            allowed_targets=[
                str(item)
                for item in ((payload.get("handoff_policy") or {}).get("allowed_targets") or [])
            ],
            notes=str((payload.get("handoff_policy") or {}).get("notes", "")),
        ),
        metadata=dict(payload.get("metadata") or {}),
    )


class FileEducationAgentCapabilityRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def list_all(self) -> list[EducationAgentCapability]:
        payload = self._read_payload()
        return [_hydrate_capability(item) for item in payload.get("agent_capabilities", [])]

    def get(self, agent_id: str) -> EducationAgentCapability:
        for item in self.list_all():
            if item.agent_id == agent_id:
                return item
        raise KeyError(f"unknown agent_id '{agent_id}'")

    def save(self, capability: EducationAgentCapability) -> EducationAgentCapability:
        payload = self._read_payload()
        items = payload.get("agent_capabilities", [])
        updated = False
        for index, item in enumerate(items):
            if item.get("agent_id") == capability.agent_id:
                items[index] = asdict(capability)
                updated = True
                break
        if not updated:
            items.append(asdict(capability))
        payload["agent_capabilities"] = items
        self._write_payload(payload)
        return capability

    def _read_payload(self) -> dict[str, object]:
        if not self._file_path.exists():
            raise FileNotFoundError(f"agent capability file not found: {self._file_path}")
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
