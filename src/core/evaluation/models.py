from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.events import RuntimeEvent
from core.state.models import JsonMap, ReducedSnapshot, RunRecord, ThreadRecord


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvaluationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class EvaluationCase:
    case_id: str
    workflow_id: str
    goal: str
    thread_type: str = "evaluation"
    workflow_version: str | None = None
    title: str | None = None
    owner_id: str | None = None
    tenant_id: str | None = None
    trigger: str = "evaluation"
    trigger_payload: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.workflow_id:
            raise ValueError("workflow_id must be non-empty")
        if not self.goal:
            raise ValueError("goal must be non-empty")
        if not self.thread_type:
            raise ValueError("thread_type must be non-empty")
        if not self.trigger:
            raise ValueError("trigger must be non-empty")


@dataclass
class EvaluationSuite:
    suite_id: str
    name: str
    cases: list[EvaluationCase]
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ValueError("suite_id must be non-empty")
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.cases:
            raise ValueError("cases must be non-empty")
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("cases contains duplicate case_id values")


@dataclass
class EvaluationExecution:
    case: EvaluationCase
    thread_record: ThreadRecord
    run_record: RunRecord
    final_state: ReducedSnapshot
    events: list[RuntimeEvent] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class EvaluationMetricResult:
    metric_name: str
    passed: bool
    value: Any = None
    details: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError("metric_name must be non-empty")


@dataclass
class EvaluationCaseResult:
    case: EvaluationCase
    status: EvaluationStatus
    execution: EvaluationExecution | None = None
    metrics: list[EvaluationMetricResult] = field(default_factory=list)
    error_message: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == EvaluationStatus.PASSED


@dataclass
class EvaluationSuiteResult:
    suite: EvaluationSuite
    case_results: list[EvaluationCaseResult] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    @property
    def total_cases(self) -> int:
        return len(self.case_results)

    @property
    def passed_cases(self) -> int:
        return sum(1 for result in self.case_results if result.status == EvaluationStatus.PASSED)

    @property
    def failed_cases(self) -> int:
        return sum(1 for result in self.case_results if result.status == EvaluationStatus.FAILED)

    @property
    def error_cases(self) -> int:
        return sum(1 for result in self.case_results if result.status == EvaluationStatus.ERROR)

