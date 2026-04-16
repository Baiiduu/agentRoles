"""Evaluation scaffold for runtime regression, scoring, and suite execution."""

from .aggregates import (
    ExecutionAggregate,
    MetricAggregate,
    SuiteMetricsAggregator,
    SuiteMetricsSummary,
)
from .models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationExecution,
    EvaluationMetricResult,
    EvaluationStatus,
    EvaluationSuite,
    EvaluationSuiteResult,
)
from .runner import DefaultEvaluationDriver, EvaluationDriver, EvaluationRunner
from .scorers import (
    CompletedNodesScorer,
    EvaluationScorer,
    EventPresenceScorer,
    MetadataScorer,
    RunStatusScorer,
    SideEffectCountScorer,
)

__all__ = [
    "CompletedNodesScorer",
    "DefaultEvaluationDriver",
    "ExecutionAggregate",
    "EvaluationCase",
    "EvaluationCaseResult",
    "EvaluationDriver",
    "EvaluationExecution",
    "EvaluationMetricResult",
    "EvaluationRunner",
    "EvaluationScorer",
    "EvaluationStatus",
    "EvaluationSuite",
    "EvaluationSuiteResult",
    "EventPresenceScorer",
    "MetricAggregate",
    "MetadataScorer",
    "RunStatusScorer",
    "SideEffectCountScorer",
    "SuiteMetricsAggregator",
    "SuiteMetricsSummary",
]
