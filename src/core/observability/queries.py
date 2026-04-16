from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from core.contracts import Runtime
from core.events import RuntimeEvent
from core.state.models import (
    InterruptRecord,
    InterruptStatus,
    PolicyDecisionRecord,
    SideEffectRecord,
)

from .models import (
    ObservabilityDigest,
    RunObservation,
    TimelineEntry,
    event_to_timeline_entry,
    interrupt_to_timeline_entry,
    policy_decision_to_timeline_entry,
    side_effect_to_timeline_entry,
)


class RuntimeQueryService:
    """
    Read-only helper layer for extracting high-value observability views from
    the Runtime protocol without coupling directly to store implementations.
    """

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime

    def fetch_run_observation(self, run_id: str) -> RunObservation:
        snapshot = self._runtime.get_state(run_id)
        events = list(self._runtime.stream_events(run_id))
        return RunObservation(run_id=run_id, snapshot=snapshot, events=events)

    def list_tool_events(self, run_id: str) -> list[RuntimeEvent]:
        return filter_tool_events(self.fetch_run_observation(run_id).events)

    def list_node_events(self, run_id: str, node_id: str) -> list[RuntimeEvent]:
        return [event for event in self.fetch_run_observation(run_id).events if event.node_id == node_id]

    def group_events_by_node(self, run_id: str) -> dict[str, list[RuntimeEvent]]:
        return group_events_by_node(self.fetch_run_observation(run_id).events)

    def list_interrupts(
        self,
        run_id: str,
        *,
        include_resolved: bool = True,
    ) -> list[InterruptRecord]:
        return list_interrupts(
            self.fetch_run_observation(run_id),
            include_resolved=include_resolved,
        )

    def list_policy_decisions(self, run_id: str) -> list[PolicyDecisionRecord]:
        return list_policy_decisions(self.fetch_run_observation(run_id))

    def list_side_effects(self, run_id: str) -> list[SideEffectRecord]:
        return list_side_effects(self.fetch_run_observation(run_id))

    def build_timeline(self, run_id: str) -> list[TimelineEntry]:
        observation = self.fetch_run_observation(run_id)
        return build_timeline(observation)

    def build_digest(self, run_id: str) -> ObservabilityDigest:
        observation = self.fetch_run_observation(run_id)
        return build_digest(observation)


def filter_tool_events(events: Iterable[RuntimeEvent]) -> list[RuntimeEvent]:
    return [event for event in events if event.event_type.startswith("tool.")]


def group_events_by_node(events: Iterable[RuntimeEvent]) -> dict[str, list[RuntimeEvent]]:
    grouped: dict[str, list[RuntimeEvent]] = defaultdict(list)
    for event in events:
        if event.node_id:
            grouped[event.node_id].append(event)
    return {node_id: sorted(items, key=lambda item: item.sequence_no) for node_id, items in grouped.items()}


def list_interrupts(
    observation: RunObservation,
    *,
    include_resolved: bool = True,
) -> list[InterruptRecord]:
    interrupts = list(observation.snapshot.interrupts.values())
    if include_resolved:
        return sorted(interrupts, key=lambda record: record.created_at)
    return sorted(
        [record for record in interrupts if record.status == InterruptStatus.OPEN],
        key=lambda record: record.created_at,
    )


def list_policy_decisions(observation: RunObservation) -> list[PolicyDecisionRecord]:
    return sorted(
        observation.snapshot.policy_decisions.values(),
        key=lambda record: record.created_at,
    )


def list_side_effects(observation: RunObservation) -> list[SideEffectRecord]:
    return sorted(
        observation.snapshot.side_effects.values(),
        key=lambda record: record.created_at,
    )


def build_timeline(observation: RunObservation) -> list[TimelineEntry]:
    entries = [event_to_timeline_entry(event) for event in observation.events]
    entries.extend(
        side_effect_to_timeline_entry(record)
        for record in observation.snapshot.side_effects.values()
    )
    entries.extend(
        interrupt_to_timeline_entry(record)
        for record in observation.snapshot.interrupts.values()
    )
    entries.extend(
        policy_decision_to_timeline_entry(record)
        for record in observation.snapshot.policy_decisions.values()
    )
    return sorted(
        entries,
        key=lambda entry: (
            entry.occurred_at,
            entry.sequence_no if entry.sequence_no is not None else 10**9,
            entry.label,
        ),
    )


def build_digest(observation: RunObservation) -> ObservabilityDigest:
    completed = set(observation.snapshot.run_state.completed_nodes)
    return ObservabilityDigest(
        run_id=observation.run_id,
        tool_event_count=len(filter_tool_events(observation.events)),
        interrupt_count=len(observation.snapshot.interrupts),
        policy_decision_count=len(observation.snapshot.policy_decisions),
        side_effect_count=len(observation.snapshot.side_effects),
        node_count=len(observation.snapshot.node_states),
        completed_node_count=len(completed),
        metadata={
            "run_status": str(observation.snapshot.run_record.status),
            "thread_id": observation.snapshot.thread_record.thread_id,
        },
    )
