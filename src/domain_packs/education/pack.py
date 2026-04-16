from __future__ import annotations

from core.agents import AgentDescriptor
from core.agents.implementation import AgentImplementation
from core.evaluation import EvaluationCase, EvaluationSuite
from core.tools import ToolDescriptor
from core.workflow import WorkflowDefinition

from domain_packs.education.agents import (
    get_education_agent_descriptors,
    get_education_agent_implementations,
)
from domain_packs.education.metadata import (
    EDUCATION_DOMAIN_METADATA,
    EducationDomainMetadata,
)
from domain_packs.education.evals import (
    get_education_eval_cases,
    get_education_eval_suites,
)
from domain_packs.education.tools import get_education_tool_descriptors
from domain_packs.education.workflows import get_education_workflow_definitions


class EducationDomainPack:
    """
    Composition root for the education domain pack.

    This first version intentionally exposes stable registration surfaces
    without embedding domain behavior in the pack root.
    """

    @staticmethod
    def get_metadata() -> EducationDomainMetadata:
        return EDUCATION_DOMAIN_METADATA

    @staticmethod
    def get_agent_descriptors() -> list[AgentDescriptor]:
        return get_education_agent_descriptors()

    @staticmethod
    def get_agent_implementations() -> list[AgentImplementation]:
        return get_education_agent_implementations()

    @staticmethod
    def get_workflow_definitions() -> list[WorkflowDefinition]:
        return get_education_workflow_definitions()

    @staticmethod
    def get_tool_descriptors() -> list[ToolDescriptor]:
        return get_education_tool_descriptors()

    @staticmethod
    def get_eval_cases() -> list[EvaluationCase]:
        return get_education_eval_cases()

    @staticmethod
    def get_eval_suites() -> list[EvaluationSuite]:
        return get_education_eval_suites()
