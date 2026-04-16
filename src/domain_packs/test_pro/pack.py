from __future__ import annotations

from core.agents import AgentDescriptor
from core.agents.implementation import AgentImplementation
from core.evaluation import EvaluationCase, EvaluationSuite
from core.tools import ToolDescriptor
from core.workflow import WorkflowDefinition

from domain_packs.test_pro.agents import (
    get_test_pro_agent_descriptors,
    get_test_pro_agent_implementations,
)
from domain_packs.test_pro.metadata import (
    TEST_PRO_DOMAIN_METADATA,
    TestProDomainMetadata,
)
from domain_packs.operations import get_operation_tool_descriptors


class TestProDomainPack:
    @staticmethod
    def get_metadata() -> TestProDomainMetadata:
        return TEST_PRO_DOMAIN_METADATA

    @staticmethod
    def get_agent_descriptors() -> list[AgentDescriptor]:
        return get_test_pro_agent_descriptors()

    @staticmethod
    def get_agent_implementations() -> list[AgentImplementation]:
        return get_test_pro_agent_implementations()

    @staticmethod
    def get_workflow_definitions() -> list[WorkflowDefinition]:
        return []

    @staticmethod
    def get_tool_descriptors() -> list[ToolDescriptor]:
        return get_operation_tool_descriptors()

    @staticmethod
    def get_eval_cases() -> list[EvaluationCase]:
        return []

    @staticmethod
    def get_eval_suites() -> list[EvaluationSuite]:
        return []
