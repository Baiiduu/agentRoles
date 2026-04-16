from __future__ import annotations

from dataclasses import dataclass, field

from .models import EvaluationCaseResult, EvaluationMetricResult, EvaluationStatus, EvaluationSuiteResult


@dataclass
class MetricAggregate:
    metric_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_numeric_value: float | None = None
    min_numeric_value: float | None = None
    max_numeric_value: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ExecutionAggregate:
    average_event_count: float = 0.0
    average_side_effect_count: float = 0.0
    average_interrupt_count: float = 0.0
    average_tool_event_count: float = 0.0
    average_completed_node_count: float = 0.0


@dataclass
class SuiteMetricsSummary:
    suite_id: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    case_pass_rate: float
    metric_aggregates: dict[str, MetricAggregate] = field(default_factory=dict)
    execution: ExecutionAggregate = field(default_factory=ExecutionAggregate)
    metadata: dict[str, object] = field(default_factory=dict)


class SuiteMetricsAggregator:
    def summarize(self, suite_result: EvaluationSuiteResult) -> SuiteMetricsSummary:
        total_cases = len(suite_result.case_results)
        passed_cases = sum(
            1 for result in suite_result.case_results if result.status == EvaluationStatus.PASSED
        )
        failed_cases = sum(
            1 for result in suite_result.case_results if result.status == EvaluationStatus.FAILED
        )
        error_cases = sum(
            1 for result in suite_result.case_results if result.status == EvaluationStatus.ERROR
        )
        case_pass_rate = (passed_cases / total_cases) if total_cases else 0.0
        metric_aggregates = self._aggregate_metrics(suite_result.case_results)
        execution_aggregate = self._aggregate_execution(suite_result.case_results)
        return SuiteMetricsSummary(
            suite_id=suite_result.suite.suite_id,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            error_cases=error_cases,
            case_pass_rate=case_pass_rate,
            metric_aggregates=metric_aggregates,
            execution=execution_aggregate,
            metadata={
                **suite_result.metadata,
                "suite_name": suite_result.suite.name,
            },
        )

    def _aggregate_metrics(
        self,
        case_results: list[EvaluationCaseResult],
    ) -> dict[str, MetricAggregate]:
        buckets: dict[str, list[EvaluationMetricResult]] = {}
        for case_result in case_results:
            for metric in case_result.metrics:
                buckets.setdefault(metric.metric_name, []).append(metric)

        aggregates: dict[str, MetricAggregate] = {}
        for metric_name, metrics in buckets.items():
            passed_cases = sum(1 for metric in metrics if metric.passed)
            failed_cases = len(metrics) - passed_cases
            numeric_values = [
                float(metric.value)
                for metric in metrics
                if isinstance(metric.value, (int, float)) and not isinstance(metric.value, bool)
            ]
            aggregates[metric_name] = MetricAggregate(
                metric_name=metric_name,
                total_cases=len(metrics),
                passed_cases=passed_cases,
                failed_cases=failed_cases,
                pass_rate=(passed_cases / len(metrics)) if metrics else 0.0,
                average_numeric_value=(
                    sum(numeric_values) / len(numeric_values) if numeric_values else None
                ),
                min_numeric_value=min(numeric_values) if numeric_values else None,
                max_numeric_value=max(numeric_values) if numeric_values else None,
            )
        return aggregates

    def _aggregate_execution(
        self,
        case_results: list[EvaluationCaseResult],
    ) -> ExecutionAggregate:
        executions = [result.execution for result in case_results if result.execution is not None]
        if not executions:
            return ExecutionAggregate()

        event_counts = [len(execution.events) for execution in executions]
        side_effect_counts = [len(execution.final_state.side_effects) for execution in executions]
        interrupt_counts = [len(execution.final_state.interrupts) for execution in executions]
        tool_event_counts = [
            sum(1 for event in execution.events if event.event_type.startswith("tool."))
            for execution in executions
        ]
        completed_node_counts = [
            len(execution.final_state.run_state.completed_nodes) for execution in executions
        ]
        return ExecutionAggregate(
            average_event_count=_average(event_counts),
            average_side_effect_count=_average(side_effect_counts),
            average_interrupt_count=_average(interrupt_counts),
            average_tool_event_count=_average(tool_event_counts),
            average_completed_node_count=_average(completed_node_counts),
        )


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
