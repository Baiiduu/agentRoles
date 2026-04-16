from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents import InMemoryAgentRegistry, RegistryBackedAgentBindingResolver
from core.contracts import RuntimeServices
from core.evaluation import (
    EvaluationRunner,
    EvaluationSuiteResult,
    SuiteMetricsAggregator,
)
from core.executors import BasicNodeExecutor, DomainAgentExecutor, ToolNodeExecutor
from core.runtime import RuntimeService
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import InMemoryToolRegistry, ObservedToolInvoker, RoutingToolInvoker
from core.workflow import InMemoryWorkflowProvider
from domain_packs.education import EducationDomainPack
from domain_packs.education.evals import (
    EDUCATION_EVAL_CASE_DIAGNOSTIC_PLAN,
    EDUCATION_EVAL_SUITE_SMOKE,
    EducationEvaluationDriver,
    build_default_education_eval_scorers,
)
from domain_packs.education.tools import build_education_function_tool_adapter


def _build_education_runtime() -> RuntimeService:
    registry = InMemoryAgentRegistry()
    for descriptor in EducationDomainPack.get_agent_descriptors():
        registry.register(descriptor)

    provider = InMemoryWorkflowProvider()
    for definition in EducationDomainPack.get_workflow_definitions():
        provider.register(definition)

    tool_registry = InMemoryToolRegistry()
    for descriptor in EducationDomainPack.get_tool_descriptors():
        tool_registry.register(descriptor)

    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
        tool_invoker=ObservedToolInvoker(
            RoutingToolInvoker(
                registry=tool_registry,
                adapters=[build_education_function_tool_adapter()],
            )
        ),
    )
    return RuntimeService(
        services=services,
        workflow_provider=provider,
        node_executor=BasicNodeExecutor(
            delegates=[
                ToolNodeExecutor(),
                DomainAgentExecutor(EducationDomainPack.get_agent_implementations()),
            ]
        ),
        agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
    )


class EducationEvaluationAssetsTestCase(unittest.TestCase):
    def test_pack_exposes_eval_cases_and_suites(self) -> None:
        cases = EducationDomainPack.get_eval_cases()
        suites = EducationDomainPack.get_eval_suites()

        self.assertEqual(len(cases), 4)
        self.assertEqual({case.workflow_id for case in cases}, {
            "education.diagnostic_plan",
            "education.practice_review",
            "education.remediation_loop",
        })
        self.assertEqual(len(suites), 3)
        self.assertEqual({suite.suite_id for suite in suites}, {
            "education.eval_suite.core_paths",
            "education.eval_suite.remediation_paths",
            "education.eval_suite.smoke",
        })

    def test_diagnostic_case_runs_with_domain_driver(self) -> None:
        runtime = _build_education_runtime()
        runner = EvaluationRunner(runtime, driver=EducationEvaluationDriver())
        case = next(
            case
            for case in EducationDomainPack.get_eval_cases()
            if case.case_id == EDUCATION_EVAL_CASE_DIAGNOSTIC_PLAN
        )

        result = runner.run_case(
            case,
            scorers=build_default_education_eval_scorers(case),
        )

        self.assertTrue(result.passed)
        self.assertIsNotNone(result.execution)
        self.assertEqual(result.execution.metadata["domain"], "education")
        self.assertIn("goal", result.execution.metadata["seeded_global_context_keys"])

    def test_smoke_suite_runs_and_aggregates_metrics(self) -> None:
        runtime = _build_education_runtime()
        runner = EvaluationRunner(runtime, driver=EducationEvaluationDriver())
        suite = next(
            suite
            for suite in EducationDomainPack.get_eval_suites()
            if suite.suite_id == EDUCATION_EVAL_SUITE_SMOKE
        )

        case_results = [
            runner.run_case(case, scorers=build_default_education_eval_scorers(case))
            for case in suite.cases
        ]
        suite_result = EvaluationSuiteResult(
            suite=suite,
            case_results=case_results,
            metadata={"domain": "education"},
        )
        summary = SuiteMetricsAggregator().summarize(suite_result)

        self.assertEqual(summary.total_cases, 4)
        self.assertEqual(summary.passed_cases, 4)
        self.assertAlmostEqual(summary.case_pass_rate, 1.0)
