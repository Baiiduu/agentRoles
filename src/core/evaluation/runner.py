from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from core.contracts import Runtime

from .models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationExecution,
    EvaluationStatus,
    EvaluationSuite,
    EvaluationSuiteResult,
)
from .scorers import EvaluationScorer


class EvaluationDriver(Protocol):
    def execute(self, runtime: Runtime, case: EvaluationCase) -> EvaluationExecution: ...


@dataclass
class DefaultEvaluationDriver:
    def execute(self, runtime: Runtime, case: EvaluationCase) -> EvaluationExecution:
        thread = runtime.create_thread(
            case.thread_type,
            case.goal,
            title=case.title,
            owner_id=case.owner_id,
            tenant_id=case.tenant_id,
            metadata={
                **case.metadata,
                "evaluation_case_id": case.case_id,
            },
        )
        run = runtime.start_run(
            thread.thread_id,
            case.workflow_id,
            workflow_version=case.workflow_version,
            trigger=case.trigger,
            trigger_payload=case.trigger_payload,
        )
        final_state = runtime.get_state(run.run_id)
        thread_record = runtime.get_thread(thread.thread_id)
        if thread_record is None:
            raise ValueError(f"thread '{thread.thread_id}' disappeared during evaluation")
        run_record = final_state.run_record
        events = list(runtime.stream_events(run_record.run_id))
        return EvaluationExecution(
            case=case,
            thread_record=thread_record,
            run_record=run_record,
            final_state=final_state,
            events=events,
        )


class EvaluationRunner:
    """
    Evaluation scaffold that consumes the Runtime protocol without coupling
    scoring logic back into runtime orchestration.
    """

    def __init__(
        self,
        runtime: Runtime,
        *,
        driver: EvaluationDriver | None = None,
    ) -> None:
        self._runtime = runtime
        self._driver = driver or DefaultEvaluationDriver()

    def run_case(
        self,
        case: EvaluationCase,
        *,
        scorers: Sequence[EvaluationScorer],
        driver: EvaluationDriver | None = None,
    ) -> EvaluationCaseResult:
        active_driver = driver or self._driver
        try:
            execution = active_driver.execute(self._runtime, case)
            metrics = [scorer.score(execution) for scorer in scorers]
        except Exception as exc:
            return EvaluationCaseResult(
                case=case,
                status=EvaluationStatus.ERROR,
                error_message=str(exc),
            )

        status = EvaluationStatus.PASSED
        if any(not metric.passed for metric in metrics):
            status = EvaluationStatus.FAILED

        return EvaluationCaseResult(
            case=case,
            status=status,
            execution=execution,
            metrics=metrics,
            metadata={
                "workflow_id": execution.run_record.workflow_id,
                "workflow_version": execution.run_record.workflow_version,
                "event_count": len(execution.events),
            },
        )

    def run_suite(
        self,
        suite: EvaluationSuite,
        *,
        scorers: Sequence[EvaluationScorer],
        driver: EvaluationDriver | None = None,
    ) -> EvaluationSuiteResult:
        case_results = [
            self.run_case(case, scorers=scorers, driver=driver) for case in suite.cases
        ]
        return EvaluationSuiteResult(
            suite=suite,
            case_results=case_results,
            metadata={
                "suite_id": suite.suite_id,
                "passed_cases": sum(1 for result in case_results if result.passed),
            },
        )
