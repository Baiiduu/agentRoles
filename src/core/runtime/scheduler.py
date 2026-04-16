from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.contracts.state_selector import StateSelector
from core.state.models import QueuePolicy, ReducedSnapshot, SchedulerConfig
from core.workflow.workflow_models import CompiledWorkflow


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class FrontierDecisionType(StrEnum):
    DISPATCH = "dispatch"
    COMPLETE = "complete"
    INTERRUPT = "interrupt"
    WAIT = "wait"
    FAIL = "fail"


@dataclass
class FrontierDecision:
    decision_type: FrontierDecisionType
    ready_nodes: list[str] = field(default_factory=list)
    failure_code: str | None = None
    reason: str | None = None


class FrontierScheduler:
    """
    Minimal frontier-based scheduler for the first runtime implementation.

    It does not execute nodes itself. It only decides what the runtime should do
    next based on the current snapshot and compiled workflow.
    """

    def __init__(
        self,
        selector: StateSelector,
        config: SchedulerConfig | None = None,
    ) -> None:
        self._selector = selector
        self._config = config or SchedulerConfig()

    def decide(
        self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow
    ) -> FrontierDecision:
        ready_nodes = self._selector.select_ready_nodes(snapshot, workflow)
        ordered_ready = self._order_ready_nodes(snapshot, ready_nodes)
        available_slots = max(
            0, self._config.max_parallel_nodes - len(snapshot.run_state.active_nodes)
        )

        if ordered_ready and available_slots > 0:
            return FrontierDecision(
                decision_type=FrontierDecisionType.DISPATCH,
                ready_nodes=ordered_ready[:available_slots],
            )

        if self._selector.terminal_condition_met(snapshot, workflow):
            return FrontierDecision(FrontierDecisionType.COMPLETE)

        if snapshot.run_state.pending_interrupt_ids:
            return FrontierDecision(
                FrontierDecisionType.INTERRUPT,
                reason="pending interrupts require resolution",
            )

        if (
            snapshot.run_state.active_nodes
            or snapshot.run_state.waiting_nodes
            or snapshot.run_state.blocked_nodes
        ):
            return FrontierDecision(
                FrontierDecisionType.WAIT,
                reason="run has active or unresolved waiting/blocked nodes",
            )

        if ordered_ready and available_slots == 0:
            return FrontierDecision(
                FrontierDecisionType.WAIT,
                reason="scheduler parallelism limit reached",
            )

        if not self._config.deadlock_detection_enabled:
            return FrontierDecision(
                FrontierDecisionType.WAIT,
                reason="no ready nodes and deadlock detection disabled",
            )

        return FrontierDecision(
            FrontierDecisionType.FAIL,
            failure_code="NO_PROGRESS",
            reason="no ready nodes and no terminal or interrupt condition matched",
        )

    def _order_ready_nodes(
        self, snapshot: ReducedSnapshot, ready_nodes: list[str]
    ) -> list[str]:
        if self._config.node_queue_policy == QueuePolicy.PRIORITY:
            return sorted(ready_nodes)

        frontier_order = {
            node_id: index for index, node_id in enumerate(snapshot.run_state.frontier)
        }
        return sorted(
            ready_nodes,
            key=lambda node_id: (frontier_order.get(node_id, len(frontier_order)), node_id),
        )
