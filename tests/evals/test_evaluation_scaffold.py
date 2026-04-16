from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import Runtime, RuntimeServices
from core.evaluation import (
    CompletedNodesScorer,
    EvaluationCase,
    EvaluationExecution,
    EvaluationRunner,
    EvaluationStatus,
    EvaluationSuite,
    EventPresenceScorer,
    RunStatusScorer,
    SuiteMetricsAggregator,
)
from core.executors import BasicNodeExecutor
from core.runtime import RuntimeService
from core.state.models import NodeType, RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.workflow import InMemoryWorkflowProvider
from core.workflow.workflow_models import (
    ApprovalPolicy,
    ApproverType,
    EdgeSpec,
    InputSelector,
    InputSource,
    InputSourceType,
    NodeSpec,
    WorkflowDefinition,
)


def _literal_selector(value: str = "seed") -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


def _build_runtime(*definitions: WorkflowDefinition) -> RuntimeService:
    provider = InMemoryWorkflowProvider()
    for definition in definitions:
        provider.register(definition)
    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
    )
    return RuntimeService(
        services=services,
        workflow_provider=provider,
        node_executor=BasicNodeExecutor(),
    )


class ResumeApprovalDriver:
    def execute(self, runtime: Runtime, case: EvaluationCase):
        thread = runtime.create_thread(case.thread_type, case.goal, metadata=case.metadata)
        run = runtime.start_run(
            thread.thread_id,
            case.workflow_id,
            workflow_version=case.workflow_version,
            trigger=case.trigger,
            trigger_payload=case.trigger_payload,
        )
        state = runtime.get_state(run.run_id)
        if state.run_record.status == RunStatus.INTERRUPTED:
            runtime.resume_run(run.run_id, {"approved": True, "actor": "eval"})
            state = runtime.get_state(run.run_id)
        thread_record = runtime.get_thread(thread.thread_id)
        if thread_record is None:
            raise ValueError("thread missing after resume flow")
        return EvaluationExecution(
            case=case,
            thread_record=thread_record,
            run_record=state.run_record,
            final_state=state,
            events=list(runtime.stream_events(state.run_record.run_id)),
            metadata={},
        )


class EvaluationScaffoldTestCase(unittest.TestCase):
    def test_runner_scores_sequential_workflow(self) -> None:
        runtime = _build_runtime(
            WorkflowDefinition(
                workflow_id="wf.eval.sequential",
                name="Sequential Eval",
                version="1.0.0",
                entry_node_id="start",
                node_specs=[
                    NodeSpec(
                        node_id="start",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=_literal_selector("start"),
                    ),
                    NodeSpec(
                        node_id="finish",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=_literal_selector("finish"),
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="start", to_node_id="finish")
                ],
            )
        )
        runner = EvaluationRunner(runtime)
        case = EvaluationCase(
            case_id="case.sequential",
            workflow_id="wf.eval.sequential",
            goal="evaluate sequential completion",
        )

        result = runner.run_case(
            case,
            scorers=[
                RunStatusScorer(),
                CompletedNodesScorer(["start", "finish"]),
                EventPresenceScorer(["run.started", "run.completed"]),
            ],
        )

        self.assertEqual(result.status, EvaluationStatus.PASSED)
        self.assertIsNotNone(result.execution)
        self.assertEqual(result.execution.final_state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.metrics), 3)
        self.assertTrue(all(metric.passed for metric in result.metrics))

    def test_runner_supports_custom_driver_for_resume_flows(self) -> None:
        runtime = _build_runtime(
            WorkflowDefinition(
                workflow_id="wf.eval.approval",
                name="Approval Eval",
                version="1.0.0",
                entry_node_id="gate",
                node_specs=[
                    NodeSpec(
                        node_id="gate",
                        node_type=NodeType.HUMAN_GATE,
                        executor_ref="builtin.human_gate",
                        input_selector=_literal_selector("gate"),
                        approval_policy=ApprovalPolicy(
                            required=True,
                            approver_type=ApproverType.HUMAN,
                            approval_reason_code="eval.approval",
                        ),
                    ),
                ],
                edge_specs=[],
            )
        )
        runner = EvaluationRunner(runtime, driver=ResumeApprovalDriver())
        case = EvaluationCase(
            case_id="case.approval",
            workflow_id="wf.eval.approval",
            goal="evaluate approval resume flow",
        )

        result = runner.run_case(
            case,
            scorers=[
                RunStatusScorer(),
                EventPresenceScorer(
                    ["interrupt.created", "interrupt.resolved", "run.completed"]
                ),
            ],
        )

        self.assertEqual(result.status, EvaluationStatus.PASSED)
        self.assertTrue(all(metric.passed for metric in result.metrics))

    def test_suite_aggregates_passed_and_failed_cases(self) -> None:
        runtime = _build_runtime(
            WorkflowDefinition(
                workflow_id="wf.eval.suite",
                name="Suite Eval",
                version="1.0.0",
                entry_node_id="only",
                node_specs=[
                    NodeSpec(
                        node_id="only",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=_literal_selector("only"),
                    )
                ],
                edge_specs=[],
            )
        )
        runner = EvaluationRunner(runtime)
        suite = EvaluationSuite(
            suite_id="suite.runtime",
            name="Runtime Baseline",
            cases=[
                EvaluationCase(
                    case_id="case.pass",
                    workflow_id="wf.eval.suite",
                    goal="pass",
                ),
                EvaluationCase(
                    case_id="case.fail",
                    workflow_id="wf.eval.suite",
                    goal="fail",
                ),
            ],
        )

        result = runner.run_suite(
            suite,
            scorers=[
                EventPresenceScorer(["run.completed"]),
                CompletedNodesScorer(["missing-node"]),
            ],
        )

        self.assertEqual(result.total_cases, 2)
        self.assertEqual(result.passed_cases, 0)
        self.assertEqual(result.failed_cases, 2)
        self.assertEqual(result.error_cases, 0)

    def test_suite_metrics_aggregator_builds_summary(self) -> None:
        runtime = _build_runtime(
            WorkflowDefinition(
                workflow_id="wf.eval.metrics",
                name="Metrics Eval",
                version="1.0.0",
                entry_node_id="only",
                node_specs=[
                    NodeSpec(
                        node_id="only",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=_literal_selector("only"),
                    )
                ],
                edge_specs=[],
            )
        )
        runner = EvaluationRunner(runtime)
        suite = EvaluationSuite(
            suite_id="suite.metrics",
            name="Metrics Suite",
            cases=[
                EvaluationCase(
                    case_id="case.metrics.1",
                    workflow_id="wf.eval.metrics",
                    goal="metrics one",
                ),
                EvaluationCase(
                    case_id="case.metrics.2",
                    workflow_id="wf.eval.metrics",
                    goal="metrics two",
                ),
            ],
        )

        suite_result = runner.run_suite(
            suite,
            scorers=[
                RunStatusScorer(),
                EventPresenceScorer(["run.completed"]),
                CompletedNodesScorer(["only"]),
            ],
        )
        summary = SuiteMetricsAggregator().summarize(suite_result)

        self.assertEqual(summary.total_cases, 2)
        self.assertEqual(summary.passed_cases, 2)
        self.assertAlmostEqual(summary.case_pass_rate, 1.0)
        self.assertIn("run.status", summary.metric_aggregates)
        self.assertIn("events.presence", summary.metric_aggregates)
        self.assertGreater(summary.execution.average_event_count, 0.0)
        self.assertGreaterEqual(summary.execution.average_completed_node_count, 1.0)
