from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from domain_packs.education import EducationDomainPack
from domain_packs.education.orchestration import (
    CaseCoordinationInput,
    CaseCoordinatorService,
    CaseHandoffRequest,
    CaseHandoffService,
    CaseSessionFeedItem,
)
from application.agent_admin.agent_capability_service import AgentCapabilityFacade

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CASE_DATA_FILE = PROJECT_ROOT / "runtime_data" / "education" / "cases.json"


class InMemoryCaseWorkspaceStore:
    def __init__(self) -> None:
        payload = self._load_payload()
        cases = payload.get("cases", [])
        self._cases = {item["case_id"]: deepcopy(item) for item in cases}
        self._handoffs: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in self._cases}
        self._session_feed: dict[str, list[dict[str, Any]]] = {
            case_id: [] for case_id in self._cases
        }

    def _load_payload(self) -> dict[str, Any]:
        if not CASE_DATA_FILE.exists():
            return {"cases": []}
        try:
            payload = json.loads(CASE_DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"cases": []}
        return payload if isinstance(payload, dict) else {"cases": []}

    def list_cases(self) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in self._cases.values()]

    def get_case(self, case_id: str) -> dict[str, Any]:
        case_payload = self._cases.get(case_id)
        if case_payload is None:
            raise KeyError(f"unknown case_id '{case_id}'")
        return deepcopy(case_payload)

    def list_handoffs(self, case_id: str) -> list[dict[str, Any]]:
        self.get_case(case_id)
        return deepcopy(self._handoffs.get(case_id, []))

    def add_handoff(self, case_id: str, record: dict[str, Any]) -> dict[str, Any]:
        self.get_case(case_id)
        self._handoffs.setdefault(case_id, []).append(deepcopy(record))
        return deepcopy(record)

    def list_session_feed(self, case_id: str) -> list[dict[str, Any]]:
        self.get_case(case_id)
        return deepcopy(self._session_feed.get(case_id, []))

    def add_session_feed_item(self, case_id: str, item: dict[str, Any]) -> dict[str, Any]:
        self.get_case(case_id)
        self._session_feed.setdefault(case_id, []).append(deepcopy(item))
        return deepcopy(item)


_STORE = InMemoryCaseWorkspaceStore()


class CaseWorkspaceFacade:
    def __init__(self) -> None:
        descriptors = EducationDomainPack.get_agent_descriptors()
        self._store = _STORE
        self._handoff_service = CaseHandoffService(agent_descriptors=descriptors)
        self._coordinator_service = CaseCoordinatorService()
        self._capability_facade = AgentCapabilityFacade()

    def list_cases(self) -> dict[str, object]:
        return {
            "cases": [
                {
                    "case_id": item["case_id"],
                    "title": item["title"],
                    "learner_name": item["learner_name"],
                    "goal": item["goal"],
                    "current_stage": item["current_stage"],
                }
                for item in self._store.list_cases()
            ]
        }

    def get_case(self, case_id: str) -> dict[str, object]:
        case_payload = self._store.get_case(case_id)
        session_feed = self._store.list_session_feed(case_id)
        handoffs = self._store.list_handoffs(case_id)
        return {
            "case": case_payload,
            "available_agents": self._available_agents(),
            "available_workflows": self._available_workflows(),
            "handoffs": handoffs,
            "session_feed": session_feed,
            "coordination": self._build_coordination(case_payload, session_feed, handoffs),
        }

    def create_handoff(self, case_id: str, payload: dict[str, object]) -> dict[str, object]:
        request = CaseHandoffRequest(
            case_id=case_id,
            target_agent_id=str(payload.get("target_agent_id", "")),
            requested_by=str(payload.get("requested_by", "teacher")),
            reason=str(payload.get("reason", "")),
            context_overrides=payload.get("context_overrides", {}) or {},
        )
        record = self._handoff_service.create_handoff(request)
        saved = self._store.add_handoff(case_id, asdict(record))
        return {
            "handoff": saved,
            "navigation_target": {
                "case_id": case_id,
                "agent_id": saved["target_agent_id"],
            },
        }

    def append_session_feed_item(
        self,
        case_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        session = payload.get("session") or {}
        agent = payload.get("agent") or {}
        artifact_preview = payload.get("artifact_preview") or {}
        item = CaseSessionFeedItem(
            case_id=case_id,
            session_id=str(session.get("session_id", "")),
            agent_id=str(agent.get("agent_id", "")),
            agent_name=str(agent.get("name", "")),
            status=str(session.get("status", "")),
            summary=str(artifact_preview.get("summary", "")) or "Agent session completed.",
            artifact_type=(
                str(artifact_preview.get("artifact_type", ""))
                if artifact_preview.get("artifact_type")
                else None
            ),
        )
        saved = self._store.add_session_feed_item(case_id, asdict(item))
        return {"item": saved}

    def get_coordination(self, case_id: str) -> dict[str, object]:
        case_payload = self._store.get_case(case_id)
        session_feed = self._store.list_session_feed(case_id)
        handoffs = self._store.list_handoffs(case_id)
        return self._build_coordination(case_payload, session_feed, handoffs)

    def build_case_session_context(self, case_id: str) -> dict[str, object]:
        case_payload = self._store.get_case(case_id)
        session_feed = self._store.list_session_feed(case_id)
        recent_artifacts = list(case_payload.get("artifacts", []))[-3:]
        recent_session_summaries = [
            {
                "agent_id": str(item.get("agent_id", "")),
                "agent_name": str(item.get("agent_name", "")),
                "status": str(item.get("status", "")),
                "summary": str(item.get("summary", "")),
                "artifact_type": item.get("artifact_type"),
            }
            for item in session_feed[-3:]
        ]
        focus_areas = [
            str(item)
            for item in case_payload.get("active_plan", {}).get("focus_areas", [])
            if str(item).strip()
        ]
        learner_state = {
            "learner_name": str(case_payload.get("learner_name", "")),
            "goal": str(case_payload.get("goal", "")),
            "current_stage": str(case_payload.get("current_stage", "")),
            "mastery_summary": str(case_payload.get("mastery_summary", "")),
        }
        return {
            "case_context": {
                "case_id": str(case_payload.get("case_id", "")),
                "title": str(case_payload.get("title", "")),
                "learner_state": learner_state,
                "active_plan": {
                    "title": str(case_payload.get("active_plan", {}).get("title", "")),
                    "focus_areas": focus_areas,
                },
                "recent_artifacts": recent_artifacts,
                "recent_session_summaries": recent_session_summaries,
            },
            "goal": str(case_payload.get("goal", "")),
            "focus_areas": focus_areas,
            "weak_topics": focus_areas,
            "recent_signals": [str(case_payload.get("mastery_summary", ""))] if case_payload.get("mastery_summary") else [],
            "current_stage": str(case_payload.get("current_stage", "")),
            "learner_name": str(case_payload.get("learner_name", "")),
            "active_plan_title": str(case_payload.get("active_plan", {}).get("title", "")),
        }

    def _build_coordination(
        self,
        case_payload: dict[str, Any],
        session_feed: list[dict[str, Any]],
        handoffs: list[dict[str, Any]],
    ) -> dict[str, object]:
        recommendation = self._coordinator_service.recommend(
            CaseCoordinationInput(
                case_id=str(case_payload["case_id"]),
                current_stage=str(case_payload["current_stage"]),
                artifact_types=[
                    str(item.get("artifact_type", ""))
                    for item in case_payload.get("artifacts", [])
                ],
                session_summaries=[
                    str(item.get("summary", "")) for item in session_feed if item.get("summary")
                ],
                handoff_count=len(handoffs),
            )
        )
        return asdict(recommendation)

    def _available_agents(self) -> list[dict[str, object]]:
        capability_payload = self._capability_facade.list_capabilities()
        capability_map = {
            str(item.get("agent_id", "")): item
            for item in capability_payload.get("agent_capabilities", [])
        }
        return [
            {
                "agent_id": descriptor.agent_id,
                "name": descriptor.name,
                "role": descriptor.role,
                "capability_summary": self._capability_summary_for(
                    capability_map.get(descriptor.agent_id)
                ),
            }
            for descriptor in EducationDomainPack.get_agent_descriptors()
        ]

    def _capability_summary_for(
        self,
        capability_payload: dict[str, Any] | None,
    ) -> dict[str, object] | None:
        if not capability_payload:
            return None
        preview = capability_payload.get("resolved_preview") or {}
        handoff_policy = preview.get("handoff_policy") or {}
        approval_policy = preview.get("approval_policy") or {}
        return {
            "enabled": bool(capability_payload.get("enabled", True)),
            "mcp_servers": list(preview.get("enabled_mcp_servers") or []),
            "skills": list(preview.get("enabled_skills") or []),
            "approval_mode": str(approval_policy.get("mode", "none")),
            "handoff_mode": str(handoff_policy.get("mode", "manual")),
            "allowed_targets": list(handoff_policy.get("allowed_targets") or []),
            "operational_summary": str(preview.get("operational_summary", "")),
            "collaboration_summary": str(preview.get("collaboration_summary", "")),
            "usage_guidance": list(preview.get("usage_guidance") or []),
            "attention_points": list(preview.get("attention_points") or []),
        }

    def _available_workflows(self) -> list[dict[str, object]]:
        return [
            {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
            }
            for workflow in EducationDomainPack.get_workflow_definitions()
        ]
