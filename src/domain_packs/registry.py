from __future__ import annotations

from core.agents import AgentDescriptor
from core.agents.implementation import AgentImplementation
from core.evaluation import EvaluationCase, EvaluationSuite
from core.tools import ToolDescriptor
from core.workflow import WorkflowDefinition

from .education import EducationDomainPack
from .software_supply_chain import SoftwareSupplyChainDomainPack
from .test_pro import TestProDomainPack


REGISTERED_DOMAIN_PACKS = [
    EducationDomainPack,
    SoftwareSupplyChainDomainPack,
    TestProDomainPack,
]


def get_registered_domain_packs():
    return list(REGISTERED_DOMAIN_PACKS)


def get_registered_agent_descriptors() -> list[AgentDescriptor]:
    descriptors: list[AgentDescriptor] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        descriptors.extend(pack.get_agent_descriptors())
    return descriptors


def get_registered_agent_implementations() -> list[AgentImplementation]:
    implementations: list[AgentImplementation] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        implementations.extend(pack.get_agent_implementations())
    return implementations


def get_registered_workflow_definitions() -> list[WorkflowDefinition]:
    workflows: list[WorkflowDefinition] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        workflows.extend(pack.get_workflow_definitions())
    return workflows


def get_registered_tool_descriptors() -> list[ToolDescriptor]:
    tools: list[ToolDescriptor] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        tools.extend(pack.get_tool_descriptors())
    return tools


def get_registered_eval_cases() -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        cases.extend(pack.get_eval_cases())
    return cases


def get_registered_eval_suites() -> list[EvaluationSuite]:
    suites: list[EvaluationSuite] = []
    for pack in REGISTERED_DOMAIN_PACKS:
        suites.extend(pack.get_eval_suites())
    return suites
