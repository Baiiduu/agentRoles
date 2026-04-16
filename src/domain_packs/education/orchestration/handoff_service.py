from __future__ import annotations

from copy import deepcopy

from core.agents import AgentDescriptor

from .handoff_models import CaseHandoffRecord, CaseHandoffRequest


class CaseHandoffService:
    """
    Human-controlled case handoff service.

    This records the operator's choice of the next agent without changing
    runtime semantics or auto-executing the next step.
    """

    def __init__(self, *, agent_descriptors: list[AgentDescriptor]) -> None:
        self._agent_descriptors = {
            descriptor.agent_id: deepcopy(descriptor) for descriptor in agent_descriptors
        }

    def create_handoff(self, request: CaseHandoffRequest) -> CaseHandoffRecord:
        if request.target_agent_id not in self._agent_descriptors:
            raise KeyError(f"unknown target_agent_id '{request.target_agent_id}'")
        return CaseHandoffRecord(
            case_id=request.case_id,
            target_agent_id=request.target_agent_id,
            requested_by=request.requested_by,
            reason=request.reason,
            context_overrides=deepcopy(request.context_overrides),
        )
