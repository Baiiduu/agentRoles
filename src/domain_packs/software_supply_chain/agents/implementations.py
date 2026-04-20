from __future__ import annotations

"""Compatibility exports for software supply chain agent implementations.

Keep this module thin so callers can continue importing from
`domain_packs.software_supply_chain.agents.implementations` while the real
logic lives in small internal modules and per-agent folders.
"""

from core.agents.implementation import AgentImplementation

from .compliance_specialist import ComplianceSpecialistImplementation
from .dependency_auditor import DependencyAuditorImplementation
from .evolver_agent import EvolverAgentImplementation
from .shared_impl.llm_loop import (
    _invoke_final_response,
    _invoke_structured_decision,
    _invoke_tool_if_available,
    _normalize_decision_output,
    _persist_memory_snapshot,
)
from .shared_impl.loop import (
    SoftwareSupplyChainChatImplementation,
    build_software_supply_chain_implementations,
)
from .shared_impl.policy import _apply_policy_to_decision, _preferred_tool_decision
from .shared_impl.shared import _NormalizedSupplyChainInput, _ToolExecutionBundle
from .shared_impl.state import (
    _build_working_summary,
    _edit_readiness_status,
    _enrich_final_reply,
    _infer_current_phase,
    _task_state,
    _validation_plan,
)
from .vulnerability_remediator import VulnerabilityRemediatorImplementation


_IMPLEMENTATION_TYPES: list[type[AgentImplementation]] = [
    DependencyAuditorImplementation,
    VulnerabilityRemediatorImplementation,
    ComplianceSpecialistImplementation,
    EvolverAgentImplementation,
]


def get_software_supply_chain_agent_implementations() -> list[AgentImplementation]:
    return build_software_supply_chain_implementations(_IMPLEMENTATION_TYPES)


__all__ = [
    "_NormalizedSupplyChainInput",
    "_ToolExecutionBundle",
    "_apply_policy_to_decision",
    "_build_working_summary",
    "_edit_readiness_status",
    "_enrich_final_reply",
    "_infer_current_phase",
    "_invoke_final_response",
    "_invoke_structured_decision",
    "_invoke_tool_if_available",
    "_normalize_decision_output",
    "_persist_memory_snapshot",
    "_preferred_tool_decision",
    "_task_state",
    "_validation_plan",
    "ComplianceSpecialistImplementation",
    "DependencyAuditorImplementation",
    "EvolverAgentImplementation",
    "SoftwareSupplyChainChatImplementation",
    "VulnerabilityRemediatorImplementation",
    "get_software_supply_chain_agent_implementations",
]
