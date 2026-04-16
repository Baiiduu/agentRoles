from __future__ import annotations

from core.agents.implementation import AgentImplementation
from domain_packs.test_pro.agents.implementations import TestProChatImplementation


def get_software_supply_chain_agent_implementations() -> list[AgentImplementation]:
    return [implementation_type() for implementation_type in _IMPLEMENTATION_TYPES]


class DependencyAuditorImplementation(TestProChatImplementation):
    implementation_ref = "software_supply_chain.dependency_auditor"


class VulnerabilityRemediatorImplementation(TestProChatImplementation):
    implementation_ref = "software_supply_chain.vulnerability_remediator"


class ComplianceSpecialistImplementation(TestProChatImplementation):
    implementation_ref = "software_supply_chain.compliance_specialist"


class EvolverAgentImplementation(TestProChatImplementation):
    implementation_ref = "software_supply_chain.evolver_agent"


_IMPLEMENTATION_TYPES = [
    DependencyAuditorImplementation,
    VulnerabilityRemediatorImplementation,
    ComplianceSpecialistImplementation,
    EvolverAgentImplementation,
]
