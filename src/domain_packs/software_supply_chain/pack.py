from __future__ import annotations

from core.agents import AgentDescriptor
from core.agents.implementation import AgentImplementation
from core.evaluation import EvaluationCase, EvaluationSuite
from core.tools import ToolDescriptor
from core.workflow import WorkflowDefinition

from domain_packs.software_supply_chain.agents import (
    get_software_supply_chain_agent_descriptors,
    get_software_supply_chain_agent_implementations,
)
from domain_packs.software_supply_chain.metadata import (
    SOFTWARE_SUPPLY_CHAIN_DOMAIN_METADATA,
    SoftwareSupplyChainDomainMetadata,
)


class SoftwareSupplyChainDomainPack:
    @staticmethod
    def get_metadata() -> SoftwareSupplyChainDomainMetadata:
        return SOFTWARE_SUPPLY_CHAIN_DOMAIN_METADATA

    @staticmethod
    def get_agent_descriptors() -> list[AgentDescriptor]:
        return get_software_supply_chain_agent_descriptors()

    @staticmethod
    def get_agent_implementations() -> list[AgentImplementation]:
        return get_software_supply_chain_agent_implementations()

    @staticmethod
    def get_workflow_definitions() -> list[WorkflowDefinition]:
        return []

    @staticmethod
    def get_tool_descriptors() -> list[ToolDescriptor]:
        return []

    @staticmethod
    def get_eval_cases() -> list[EvaluationCase]:
        return []

    @staticmethod
    def get_eval_suites() -> list[EvaluationSuite]:
        return []
