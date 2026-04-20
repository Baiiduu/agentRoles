from __future__ import annotations

from core.agents import AgentDescriptor

from .compliance_specialist import get_compliance_specialist_descriptor
from .dependency_auditor import get_dependency_auditor_descriptor
from .evolver_agent import get_evolver_agent_descriptor
from .vulnerability_remediator import get_vulnerability_remediator_descriptor


def get_software_supply_chain_agent_descriptors() -> list[AgentDescriptor]:
    return [
        get_dependency_auditor_descriptor(),
        get_vulnerability_remediator_descriptor(),
        get_compliance_specialist_descriptor(),
        get_evolver_agent_descriptor(),
    ]
