from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from core.state.models import JsonMap, RunStatus

from .models import EvaluationExecution, EvaluationMetricResult


class EvaluationScorer(Protocol):
    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult: ...


@dataclass
class RunStatusScorer:
    expected_status: RunStatus = RunStatus.COMPLETED
    metric_name: str = "run.status"

    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult:
        actual_status = execution.final_state.run_record.status
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            passed=actual_status == self.expected_status,
            value=str(actual_status),
            details={"expected_status": str(self.expected_status)},
        )


@dataclass
class CompletedNodesScorer:
    required_node_ids: Sequence[str]
    metric_name: str = "run.completed_nodes"

    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult:
        completed = set(execution.final_state.run_state.completed_nodes)
        required = list(self.required_node_ids)
        missing = [node_id for node_id in required if node_id not in completed]
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            passed=not missing,
            value=len(completed),
            details={
                "required_node_ids": required,
                "missing_node_ids": missing,
                "completed_node_ids": sorted(completed),
            },
        )


@dataclass
class EventPresenceScorer:
    required_event_types: Sequence[str]
    metric_name: str = "events.presence"

    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult:
        seen = {event.event_type for event in execution.events}
        required = list(self.required_event_types)
        missing = [event_type for event_type in required if event_type not in seen]
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            passed=not missing,
            value=len(seen),
            details={
                "required_event_types": required,
                "missing_event_types": missing,
                "seen_event_types": sorted(seen),
            },
        )


@dataclass
class SideEffectCountScorer:
    minimum_count: int = 1
    metric_name: str = "run.side_effect_count"

    def __post_init__(self) -> None:
        if self.minimum_count < 0:
            raise ValueError("minimum_count must be >= 0")

    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult:
        actual_count = len(execution.final_state.side_effects)
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            passed=actual_count >= self.minimum_count,
            value=actual_count,
            details={"minimum_count": self.minimum_count},
        )


@dataclass
class MetadataScorer:
    field_path: str
    expected_value: object
    metric_name: str = "run.metadata_field"
    source: str = "run_record"

    def __post_init__(self) -> None:
        if not self.field_path:
            raise ValueError("field_path must be non-empty")
        if self.source not in {"run_record", "run_state", "execution"}:
            raise ValueError("source must be one of: run_record, run_state, execution")

    def score(self, execution: EvaluationExecution) -> EvaluationMetricResult:
        root: JsonMap
        if self.source == "run_record":
            root = execution.final_state.run_record.metadata
        elif self.source == "run_state":
            root = execution.final_state.run_state.extensions
        else:
            root = execution.metadata
        actual_value = _lookup_path(root, self.field_path)
        return EvaluationMetricResult(
            metric_name=self.metric_name,
            passed=actual_value == self.expected_value,
            value=actual_value,
            details={
                "source": self.source,
                "field_path": self.field_path,
                "expected_value": self.expected_value,
            },
        )


def _lookup_path(payload: JsonMap, field_path: str) -> object:
    current: object = payload
    for segment in field_path.split("."):
        if not isinstance(current, dict):
            return None
        if segment not in current:
            return None
        current = current[segment]
    return current
