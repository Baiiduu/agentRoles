from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable
from uuid import uuid4

from core.agents import ResolvedAgentBinding, ResolvedWorkflowBindings
from core.checkpoint import CheckpointRecord, SnapshotPayload
from core.contracts import (
    AgentBindingResolver,
    ExecutionContext,
    NodeExecutor,
    ReplayHandle,
    ReplayMode,
    RuntimeServices,
    StateSelector,
    WorkflowProvider,
)
from core.events import (
    EventDraft,
    RuntimeEvent,
    RuntimeEventEmitter,
    child_trace_context,
    root_trace_context,
)
from core.runtime.scheduler import FrontierDecisionType, FrontierScheduler
from core.state import DefaultStateSelector, StateReducer
from core.state.models import (
    ArtifactRecord,
    InterruptStatus,
    NodeState,
    NodeStatus,
    RunRecord,
    RunState,
    RunStatus,
    StatePatch,
    ThreadRecord,
    ThreadState,
    ThreadStatus,
)
from core.workflow import CompiledWorkflow, WorkflowCompiler


TERMINAL_NODE_STATUSES = {
    NodeStatus.SUCCEEDED,
    NodeStatus.FAILED,
    NodeStatus.SKIPPED,
    NodeStatus.CANCELLED,
}

TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _UuidGenerator:
    def new(self, prefix: str | None = None) -> str:
        base = uuid4().hex
        if prefix:
            return f"{prefix}_{base}"
        return base


class _Clock:
    def now(self) -> datetime:
        return _utcnow()


@dataclass
class _RuntimeDependencies:
    services: RuntimeServices
    workflow_provider: WorkflowProvider
    node_executor: NodeExecutor
    agent_binding_resolver: AgentBindingResolver | None
    workflow_compiler: WorkflowCompiler
    selector: StateSelector
    scheduler: FrontierScheduler
    reducer: StateReducer


class RuntimeService:
    """
    First runnable runtime service for the core platform.

    The service keeps orchestration logic in one place while leaving storage,
    selection, reduction, execution, and workflow lookup behind dedicated
    abstractions.
    """

    def __init__(
        self,
        *,
        services: RuntimeServices,
        workflow_provider: WorkflowProvider,
        node_executor: NodeExecutor,
        agent_binding_resolver: AgentBindingResolver | None = None,
        selector: StateSelector | None = None,
        workflow_compiler: WorkflowCompiler | None = None,
        scheduler: FrontierScheduler | None = None,
        reducer: StateReducer | None = None,
    ) -> None:
        selector = selector or DefaultStateSelector()
        services = self._materialize_services(services)
        self._deps = _RuntimeDependencies(
            services=services,
            workflow_provider=workflow_provider,
            node_executor=node_executor,
            agent_binding_resolver=agent_binding_resolver,
            workflow_compiler=workflow_compiler or WorkflowCompiler(),
            selector=selector,
            scheduler=scheduler or FrontierScheduler(selector),
            reducer=reducer or StateReducer(),
        )

    def create_thread(
        self,
        thread_type: str,
        goal: str,
        *,
        title: str | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ThreadRecord:
        now = self._deps.services.clock.now()
        thread_id = self._deps.services.id_generator.new("thread")
        thread = ThreadRecord(
            thread_id=thread_id,
            thread_type=thread_type,
            title=title,
            owner_id=owner_id,
            tenant_id=tenant_id,
            status=ThreadStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        thread_state = ThreadState(
            thread_id=thread_id,
            goal=goal,
            thread_status=ThreadStatus.CREATED,
        )
        self._deps.services.state_store.save_thread_record(thread)
        self._deps.services.state_store.save_thread_state(thread_state)
        return self._emit_thread_event("thread.created", thread, payload={"goal": goal})

    def start_run(
        self,
        thread_id: str,
        workflow_id: str,
        *,
        workflow_version: str | None = None,
        trigger: str = "manual",
        trigger_payload: dict[str, object] | None = None,
    ) -> RunRecord:
        thread_record = self._require_thread(thread_id)
        thread_state = self._require_thread_state(thread_id)
        if thread_record.current_run_id is not None:
            raise ValueError(f"thread '{thread_id}' already has an active run")

        definition = self._require_workflow(workflow_id, workflow_version)
        workflow = self._deps.workflow_compiler.compile(definition)
        workflow_bindings = self._resolve_workflow_bindings(workflow)

        now = self._deps.services.clock.now()
        run_id = self._deps.services.id_generator.new("run")
        run_record = RunRecord(
            run_id=run_id,
            thread_id=thread_id,
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            status=RunStatus.RUNNING,
            entry_node_id=workflow.entry_node_id,
            started_at=now,
            trigger=trigger,
            trigger_payload=dict(trigger_payload or {}),
        )
        run_state = RunState(
            run_id=run_id,
            thread_id=thread_id,
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            status=RunStatus.RUNNING,
            frontier=[workflow.entry_node_id],
        )
        initial_snapshot = self._deps.reducer.apply(
            current_snapshot=self._empty_snapshot(thread_record, thread_state, run_record, run_state),
            patch=StatePatch(
                thread_record_updates={
                    "status": ThreadStatus.ACTIVE,
                    "current_run_id": run_id,
                    "updated_at": now,
                },
                thread_state_updates={
                    "active_run_id": run_id,
                    "thread_status": ThreadStatus.ACTIVE,
                },
                run_state_updates=self._binding_run_state_updates(workflow_bindings),
                node_states_to_upsert=self._build_initial_node_states(run_id, workflow),
            ),
        )
        self._persist_snapshot(initial_snapshot)
        self._append_run_events(
            run_id,
            [
                self._new_event(
                    "run.created",
                    initial_snapshot.thread_record.thread_id,
                    run_id,
                    payload={
                        "workflow_id": workflow.workflow_id,
                        "workflow_version": workflow.version,
                        "entry_node_id": workflow.entry_node_id,
                    },
                ),
                self._new_event(
                    "run.started",
                    initial_snapshot.thread_record.thread_id,
                    run_id,
                    payload={"trigger": trigger},
                ),
                self._new_event(
                    "node.ready",
                    initial_snapshot.thread_record.thread_id,
                    run_id,
                    node_id=workflow.entry_node_id,
                    payload={"reason": "entry"},
                ),
            ],
        )
        self._checkpoint(initial_snapshot)
        self._run_scheduler_loop(run_id, workflow)
        return self.get_run(run_id) or run_record

    def resume_run(
        self,
        run_id: str,
        resolution_payload: dict[str, object] | None = None,
    ) -> RunRecord:
        snapshot = self.get_state(run_id)
        if snapshot.run_record.status not in {RunStatus.INTERRUPTED, RunStatus.WAITING}:
            raise ValueError("resume_run requires run status interrupted or waiting")

        now = self._deps.services.clock.now()
        interrupt_updates = {}
        node_state_updates = {}
        resumed_frontier = list(snapshot.run_state.frontier)
        resumed_waiting_nodes = list(snapshot.run_state.waiting_nodes)
        resumed_blocked_nodes = list(snapshot.run_state.blocked_nodes)
        run_state_updates = {"status": RunStatus.RUNNING}
        events: list[RuntimeEvent] = []
        if resolution_payload is not None:
            for interrupt_id in snapshot.run_state.pending_interrupt_ids:
                interrupt = snapshot.interrupts.get(interrupt_id)
                interrupt_updates[interrupt_id] = {
                    "status": InterruptStatus.RESOLVED,
                    "resolved_at": now,
                    "resolution_payload": dict(resolution_payload),
                }
                if interrupt is not None and interrupt.node_id is not None:
                    node_state_updates[interrupt.node_id] = {
                        "status": NodeStatus.READY,
                        "error_code": None,
                        "error_message": None,
                    }
                    resumed_waiting_nodes = [
                        candidate
                        for candidate in resumed_waiting_nodes
                        if candidate != interrupt.node_id
                    ]
                    resumed_blocked_nodes = [
                        candidate
                        for candidate in resumed_blocked_nodes
                        if candidate != interrupt.node_id
                    ]
                    resumed_frontier = self._merge_unique(
                        resumed_frontier, [interrupt.node_id]
                    )
                events.append(
                    self._new_event(
                        "interrupt.resolved",
                        snapshot.thread_record.thread_id,
                        run_id,
                        payload={
                            "interrupt_id": interrupt_id,
                            "resolution_payload": dict(resolution_payload),
                        },
                        trace_context=self._node_trace_context(
                            run_id,
                            interrupt.node_id,
                            attempt=snapshot.node_states[interrupt.node_id].attempt,
                        )
                        if interrupt is not None and interrupt.node_id in snapshot.node_states
                        else self._run_trace_context(run_id),
                    )
                )
        if interrupt_updates:
            run_state_updates["waiting_nodes"] = resumed_waiting_nodes
            run_state_updates["blocked_nodes"] = resumed_blocked_nodes
            run_state_updates["frontier"] = resumed_frontier

        resumed_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={"status": ThreadStatus.ACTIVE},
                thread_state_updates={"thread_status": ThreadStatus.ACTIVE},
                run_record_updates={"status": RunStatus.RUNNING},
                run_state_updates=run_state_updates,
                node_state_updates=node_state_updates,
                interrupt_updates=interrupt_updates,
            ),
        )
        self._append_run_events(
            run_id,
            events
            + [
                self._new_event(
                    "run.resumed",
                    resumed_snapshot.thread_record.thread_id,
                    run_id,
                    payload={"resolved_interrupts": list(interrupt_updates)},
                )
            ],
        )
        self._checkpoint(resumed_snapshot)
        workflow = self._resolve_compiled_workflow(
            resumed_snapshot.run_record.workflow_id,
            resumed_snapshot.run_record.workflow_version,
        )
        self._run_scheduler_loop(run_id, workflow)
        return self.get_run(run_id) or resumed_snapshot.run_record

    def cancel_run(self, run_id: str, *, reason: str | None = None) -> RunRecord:
        snapshot = self.get_state(run_id)
        if snapshot.run_record.status in TERMINAL_RUN_STATUSES:
            return snapshot.run_record

        now = self._deps.services.clock.now()
        node_state_updates = {}
        for node_id, node_state in snapshot.node_states.items():
            if node_state.status not in TERMINAL_NODE_STATUSES:
                node_state_updates[node_id] = {
                    "status": NodeStatus.CANCELLED,
                    "ended_at": now,
                    "error_message": reason,
                }

        cancelled_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={
                    "current_run_id": None,
                    "updated_at": now,
                },
                thread_state_updates={
                    "active_run_id": None,
                    "thread_status": ThreadStatus.ACTIVE,
                },
                run_record_updates={
                    "status": RunStatus.CANCELLED,
                    "ended_at": now,
                    "failure_message": reason,
                },
                run_state_updates={
                    "status": RunStatus.CANCELLED,
                    "frontier": [],
                    "active_nodes": [],
                    "waiting_nodes": [],
                    "blocked_nodes": [],
                },
                node_state_updates=node_state_updates,
            ),
        )
        self._append_run_events(
            run_id,
            [
                self._new_event(
                    "run.cancelled",
                    cancelled_snapshot.thread_record.thread_id,
                    run_id,
                    payload={"reason": reason},
                )
            ],
        )
        self._checkpoint(cancelled_snapshot)
        return self.get_run(run_id) or cancelled_snapshot.run_record

    def replay_run(
        self,
        run_id: str,
        *,
        checkpoint_id: str | None = None,
        mode: str = "diagnostic",
    ) -> ReplayHandle:
        record = self._deps.services.state_store.get_run_record(run_id)
        if record is None:
            raise KeyError(f"run '{run_id}' not found")

        checkpoint = (
            self._deps.services.checkpoint_store.get(checkpoint_id)
            if checkpoint_id is not None
            else self._deps.services.checkpoint_store.latest(run_id)
        )
        if checkpoint is None:
            raise KeyError(f"checkpoint for run '{run_id}' not found")

        return ReplayHandle(
            run_id=self._deps.services.id_generator.new("replay"),
            source_run_id=run_id,
            checkpoint_id=checkpoint.checkpoint_id,
            mode=ReplayMode(mode),
        )

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        return self._deps.services.state_store.get_thread_record(thread_id)

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._deps.services.state_store.get_run_record(run_id)

    def get_state(self, run_id: str):
        store_snapshot = self._deps.services.state_store.build_snapshot(run_id)
        return self._to_reduced_snapshot(store_snapshot)

    def stream_events(
        self,
        run_id: str,
        *,
        after_sequence_no: int | None = None,
        limit: int | None = None,
    ) -> Iterable[RuntimeEvent]:
        return self._deps.services.event_store.list_by_run(
            run_id,
            after_sequence_no=after_sequence_no,
            limit=limit,
        )

    def _run_scheduler_loop(self, run_id: str, workflow: CompiledWorkflow) -> None:
        while True:
            snapshot = self.get_state(run_id)
            if snapshot.run_record.status in TERMINAL_RUN_STATUSES:
                return

            decision = self._deps.scheduler.decide(snapshot, workflow)
            if decision.ready_nodes:
                snapshot = self._apply_patch(
                    snapshot,
                    StatePatch(run_state_updates={"frontier": list(decision.ready_nodes)}),
                )

            if decision.decision_type == FrontierDecisionType.DISPATCH:
                for node_id in decision.ready_nodes:
                    current_snapshot = self.get_state(run_id)
                    if current_snapshot.run_record.status in TERMINAL_RUN_STATUSES:
                        return
                    self._execute_node(current_snapshot, workflow, node_id)
                continue

            if decision.decision_type == FrontierDecisionType.COMPLETE:
                self._mark_run_completed(snapshot)
                return

            if decision.decision_type == FrontierDecisionType.INTERRUPT:
                self._mark_run_interrupted(snapshot, reason=decision.reason)
                return

            if decision.decision_type == FrontierDecisionType.WAIT:
                self._mark_run_waiting(snapshot, reason=decision.reason)
                return

            if decision.decision_type == FrontierDecisionType.FAIL:
                self._mark_run_failed(
                    snapshot,
                    failure_code=decision.failure_code or "NO_PROGRESS",
                    failure_message=decision.reason,
                )
                return

            raise ValueError(f"unsupported scheduler decision={decision.decision_type}")

    def _execute_node(
        self,
        snapshot,
        workflow: CompiledWorkflow,
        node_id: str,
    ) -> None:
        node_spec = workflow.node_map[node_id]
        effective_executor_ref = self._resolve_executor_ref(snapshot, node_id, node_spec.executor_ref)
        if not self._deps.node_executor.can_execute(node_spec.node_type, effective_executor_ref):
            self._mark_run_failed(
                snapshot,
                failure_code="EXECUTOR_NOT_AVAILABLE",
                failure_message=f"no executor available for node '{node_id}'",
            )
            return

        now = self._deps.services.clock.now()
        selected_input = self._deps.selector.select_node_input(snapshot, node_spec.input_selector)
        started_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                run_state_updates={
                    "active_nodes": self._merge_unique(snapshot.run_state.active_nodes, [node_id]),
                    "frontier": [
                        candidate
                        for candidate in snapshot.run_state.frontier
                        if candidate != node_id
                    ],
                },
                node_state_updates={
                    node_id: {
                        "attempt": snapshot.node_states[node_id].attempt + 1,
                        "status": NodeStatus.RUNNING,
                        "started_at": now,
                        "input_snapshot": selected_input,
                        "executor_ref": effective_executor_ref,
                    }
                },
            ),
        )
        self._append_run_events(
            snapshot.run_record.run_id,
            [
                self._new_event(
                    "node.started",
                    started_snapshot.thread_record.thread_id,
                    started_snapshot.run_record.run_id,
                    node_id=node_id,
                    payload={"executor_ref": effective_executor_ref},
                    trace_context=self._node_trace_context(
                        started_snapshot.run_record.run_id,
                        node_id,
                        attempt=started_snapshot.node_states[node_id].attempt,
                    ),
                )
            ],
        )
        self._checkpoint(started_snapshot)

        execution_context = self._build_execution_context(started_snapshot, workflow, node_id)
        result = self._deps.node_executor.execute(execution_context)

        current_snapshot = self.get_state(snapshot.run_record.run_id)
        result_patch = self._build_result_patch(current_snapshot, workflow, node_id, result)
        result_snapshot = self._apply_patch(current_snapshot, result_patch)
        result_events = [
            self._new_event(
                self._node_event_type(result.status),
                result_snapshot.thread_record.thread_id,
                result_snapshot.run_record.run_id,
                node_id=node_id,
                payload={
                    "status": str(result.status),
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                },
                trace_context=self._node_trace_context(
                    result_snapshot.run_record.run_id,
                    node_id,
                    attempt=result_snapshot.node_states[node_id].attempt,
                ),
            )
        ]
        for interrupt in result.interrupts:
            result_events.append(
                self._new_event(
                    "interrupt.created",
                    result_snapshot.thread_record.thread_id,
                    result_snapshot.run_record.run_id,
                    node_id=interrupt.node_id,
                    payload={
                        "interrupt_id": interrupt.interrupt_id,
                        "interrupt_type": str(interrupt.interrupt_type),
                        "reason_code": interrupt.reason_code,
                    },
                    trace_context=self._node_trace_context(
                        result_snapshot.run_record.run_id,
                        node_id,
                        attempt=result_snapshot.node_states[node_id].attempt,
                    ),
                )
            )
        self._append_run_events(snapshot.run_record.run_id, result_events)
        self._checkpoint(result_snapshot)

        if result.status == NodeStatus.FAILED:
            self._mark_run_failed(
                result_snapshot,
                failure_code=result.error_code or "NODE_EXECUTION_ERROR",
                failure_message=result.error_message,
            )

    def _build_execution_context(
        self,
        snapshot,
        workflow: CompiledWorkflow,
        node_id: str,
    ) -> ExecutionContext:
        node_spec = workflow.node_map[node_id]
        agent_binding = self._read_agent_binding(snapshot, node_id)
        return ExecutionContext(
            thread_record=snapshot.thread_record,
            run_record=snapshot.run_record,
            thread_state=snapshot.thread_state,
            run_state=snapshot.run_state,
            node_state=snapshot.node_states[node_id],
            workflow=workflow,
            node_spec=node_spec,
            agent_binding=agent_binding,
            selected_input=self._deps.selector.select_node_input(
                snapshot, node_spec.input_selector
            ),
            services=self._deps.services,
            trace_context=self._node_trace_context(
                snapshot.run_record.run_id,
                node_id,
                attempt=snapshot.node_states[node_id].attempt,
            ).to_map(),
        )

    def _build_result_patch(self, snapshot, workflow, node_id: str, result) -> StatePatch:
        now = self._deps.services.clock.now()
        run_state = snapshot.run_state
        thread_state_updates = {}
        node_updates = {
            "status": result.status,
            "ended_at": now,
            "error_code": result.error_code,
            "error_message": result.error_message,
        }
        active_nodes = [candidate for candidate in run_state.active_nodes if candidate != node_id]
        completed_nodes = [
            candidate for candidate in run_state.completed_nodes if candidate != node_id
        ]
        failed_nodes = [candidate for candidate in run_state.failed_nodes if candidate != node_id]
        waiting_nodes = [candidate for candidate in run_state.waiting_nodes if candidate != node_id]
        blocked_nodes = [candidate for candidate in run_state.blocked_nodes if candidate != node_id]

        if result.status == NodeStatus.SUCCEEDED:
            completed_nodes.append(node_id)
        elif result.status == NodeStatus.FAILED:
            failed_nodes.append(node_id)
        elif result.status == NodeStatus.WAITING:
            waiting_nodes.append(node_id)
        elif result.status == NodeStatus.BLOCKED:
            blocked_nodes.append(node_id)

        run_state_updates = {
            "active_nodes": active_nodes,
            "completed_nodes": self._dedupe(completed_nodes),
            "failed_nodes": self._dedupe(failed_nodes),
            "waiting_nodes": self._dedupe(waiting_nodes),
            "blocked_nodes": self._dedupe(blocked_nodes),
        }
        self._apply_result_hints(
            result,
            run_state_updates=run_state_updates,
            thread_state_updates=thread_state_updates,
        )

        artifacts_to_create = []
        if result.artifact is not None:
            artifacts_to_create.append(deepcopy(result.artifact))
        elif result.output is not None and workflow.node_map[node_id].output_binding is not None:
            binding = workflow.node_map[node_id].output_binding
            artifacts_to_create.append(
                ArtifactRecord(
                    artifact_id=self._deps.services.id_generator.new("artifact"),
                    run_id=snapshot.run_record.run_id,
                    thread_id=snapshot.thread_record.thread_id,
                    producer_node_id=node_id,
                    artifact_type=binding.artifact_type,
                    schema_version="1.0",
                    payload_inline=deepcopy(result.output),
                )
            )

        return StatePatch(
            thread_state_updates=thread_state_updates,
            run_state_updates=run_state_updates,
            node_state_updates={node_id: node_updates},
            artifacts_to_create=artifacts_to_create,
            interrupts_to_create=[deepcopy(item) for item in result.interrupts],
            policy_decisions_to_create=[deepcopy(item) for item in result.policy_decisions],
            side_effects_to_create=[deepcopy(item) for item in result.side_effects],
        )

    def _apply_result_hints(
        self,
        result,
        *,
        run_state_updates: dict[str, object],
        thread_state_updates: dict[str, object],
    ) -> None:
        if not result.next_hints:
            return

        run_state_extensions = result.next_hints.get("run_state_extensions")
        if run_state_extensions is not None:
            if not isinstance(run_state_extensions, dict):
                raise ValueError("next_hints.run_state_extensions must be a dict")
            run_state_updates["extensions"] = deepcopy(run_state_extensions)

        thread_state_extensions = result.next_hints.get("thread_state_extensions")
        if thread_state_extensions is not None:
            if not isinstance(thread_state_extensions, dict):
                raise ValueError("next_hints.thread_state_extensions must be a dict")
            thread_state_updates["extensions"] = deepcopy(thread_state_extensions)

    def _mark_run_completed(self, snapshot) -> None:
        now = self._deps.services.clock.now()
        updated_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={
                    "current_run_id": None,
                    "updated_at": now,
                },
                thread_state_updates={
                    "active_run_id": None,
                    "thread_status": ThreadStatus.ACTIVE,
                },
                run_record_updates={"status": RunStatus.COMPLETED, "ended_at": now},
                run_state_updates={
                    "status": RunStatus.COMPLETED,
                    "frontier": [],
                    "active_nodes": [],
                },
            ),
        )
        self._append_run_events(
            snapshot.run_record.run_id,
            [
                self._new_event(
                    "run.completed",
                    updated_snapshot.thread_record.thread_id,
                    updated_snapshot.run_record.run_id,
                )
            ],
        )
        self._checkpoint(updated_snapshot)

    def _mark_run_interrupted(self, snapshot, *, reason: str | None) -> None:
        updated_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={"status": ThreadStatus.PAUSED},
                thread_state_updates={"thread_status": ThreadStatus.PAUSED},
                run_record_updates={"status": RunStatus.INTERRUPTED},
                run_state_updates={"status": RunStatus.INTERRUPTED, "frontier": []},
            ),
        )
        self._append_run_events(
            snapshot.run_record.run_id,
            [
                self._new_event(
                    "run.interrupted",
                    updated_snapshot.thread_record.thread_id,
                    updated_snapshot.run_record.run_id,
                    payload={"reason": reason},
                )
            ],
        )
        self._checkpoint(updated_snapshot)

    def _mark_run_waiting(self, snapshot, *, reason: str | None) -> None:
        updated_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={"status": ThreadStatus.PAUSED},
                thread_state_updates={"thread_status": ThreadStatus.PAUSED},
                run_record_updates={"status": RunStatus.WAITING},
                run_state_updates={"status": RunStatus.WAITING, "frontier": []},
            ),
        )
        self._append_run_events(
            snapshot.run_record.run_id,
            [
                self._new_event(
                    "run.waiting",
                    updated_snapshot.thread_record.thread_id,
                    updated_snapshot.run_record.run_id,
                    payload={"reason": reason},
                )
            ],
        )
        self._checkpoint(updated_snapshot)

    def _mark_run_failed(
        self,
        snapshot,
        *,
        failure_code: str,
        failure_message: str | None,
    ) -> None:
        now = self._deps.services.clock.now()
        updated_snapshot = self._apply_patch(
            snapshot,
            StatePatch(
                thread_record_updates={
                    "current_run_id": None,
                    "updated_at": now,
                },
                thread_state_updates={
                    "active_run_id": None,
                    "thread_status": ThreadStatus.ACTIVE,
                },
                run_record_updates={
                    "status": RunStatus.FAILED,
                    "ended_at": now,
                    "failure_code": failure_code,
                    "failure_message": failure_message,
                },
                run_state_updates={
                    "status": RunStatus.FAILED,
                    "frontier": [],
                    "active_nodes": [],
                },
            ),
        )
        self._append_run_events(
            snapshot.run_record.run_id,
            [
                self._new_event(
                    "run.failed",
                    updated_snapshot.thread_record.thread_id,
                    updated_snapshot.run_record.run_id,
                    payload={
                        "failure_code": failure_code,
                        "failure_message": failure_message,
                    },
                )
            ],
        )
        self._checkpoint(updated_snapshot)

    def _append_run_events(self, run_id: str, events: list[EventDraft]) -> None:
        if not events:
            return
        materialized = self._event_emitter().emit_run_events(run_id, events)
        latest = materialized[-1]
        current_snapshot = self.get_state(run_id)
        updated_snapshot = self._deps.reducer.apply(
            current_snapshot,
            StatePatch(run_state_updates={"last_event_id": latest.event_id}),
        )
        self._persist_snapshot(updated_snapshot)

    def _checkpoint(self, snapshot) -> CheckpointRecord:
        current_snapshot = self.get_state(snapshot.run_record.run_id)
        latest_event = self._deps.services.event_store.latest_for_run(
            current_snapshot.run_record.run_id
        )
        checkpoint = CheckpointRecord(
            checkpoint_id=self._deps.services.id_generator.new("checkpoint"),
            thread_id=current_snapshot.thread_record.thread_id,
            run_id=current_snapshot.run_record.run_id,
            sequence_no=latest_event.sequence_no if latest_event is not None else 0,
            snapshot_ref="inline",
            frontier_snapshot=list(current_snapshot.run_state.frontier),
            event_cursor=latest_event.event_id if latest_event is not None else None,
        )
        stored = self._deps.services.checkpoint_store.create(
            checkpoint, self._snapshot_to_payload(current_snapshot)
        )
        updated_snapshot = self._deps.reducer.apply(
            current_snapshot,
            StatePatch(
                thread_record_updates={"latest_checkpoint_id": stored.checkpoint_id}
            ),
        )
        self._persist_snapshot(updated_snapshot)
        return stored

    def _snapshot_to_payload(self, snapshot) -> SnapshotPayload:
        latest_event = self._deps.services.event_store.latest_for_run(snapshot.run_record.run_id)
        return SnapshotPayload(
            thread_record=deepcopy(snapshot.thread_record),
            run_record=deepcopy(snapshot.run_record),
            thread_state=deepcopy(snapshot.thread_state),
            run_state=deepcopy(snapshot.run_state),
            node_states=[deepcopy(item) for item in snapshot.node_states.values()],
            artifact_ids=list(snapshot.artifacts),
            interrupt_ids=list(snapshot.interrupts),
            policy_decision_ids=list(snapshot.policy_decisions),
            side_effect_ids=list(snapshot.side_effects),
            last_event_id=latest_event.event_id if latest_event is not None else None,
        )

    def _apply_patch(self, snapshot, patch: StatePatch):
        reduced = self._deps.reducer.apply(snapshot, patch)
        self._persist_snapshot(reduced)
        return reduced

    def _persist_snapshot(self, snapshot) -> None:
        store = self._deps.services.state_store
        store.save_thread_record(snapshot.thread_record)
        store.save_run_record(snapshot.run_record)
        store.save_thread_state(snapshot.thread_state)
        store.save_run_state(snapshot.run_state)
        for node_state in snapshot.node_states.values():
            store.save_node_state(node_state)
        for artifact in snapshot.artifacts.values():
            store.save_artifact(artifact)
        for interrupt in snapshot.interrupts.values():
            store.save_interrupt(interrupt)
        for decision in snapshot.policy_decisions.values():
            store.save_policy_decision(decision)
        for side_effect in snapshot.side_effects.values():
            store.save_side_effect(side_effect)

    def _empty_snapshot(
        self,
        thread_record: ThreadRecord,
        thread_state: ThreadState,
        run_record: RunRecord,
        run_state: RunState,
    ):
        from core.state.models import ReducedSnapshot

        return ReducedSnapshot(
            thread_record=thread_record,
            run_record=run_record,
            thread_state=thread_state,
            run_state=run_state,
        )

    def _build_initial_node_states(
        self, run_id: str, workflow: CompiledWorkflow
    ) -> list[NodeState]:
        states: list[NodeState] = []
        for node_id, node_spec in workflow.node_map.items():
            states.append(
                NodeState(
                    run_id=run_id,
                    node_id=node_id,
                    node_type=node_spec.node_type,
                    status=NodeStatus.READY
                    if node_id == workflow.entry_node_id
                    else NodeStatus.PENDING,
                    executor_ref=node_spec.executor_ref,
                )
            )
        return states

    def _resolve_compiled_workflow(
        self, workflow_id: str, workflow_version: str
    ) -> CompiledWorkflow:
        definition = self._require_workflow(workflow_id, workflow_version)
        return self._deps.workflow_compiler.compile(definition)

    def _require_workflow(self, workflow_id: str, workflow_version: str | None):
        definition = self._deps.workflow_provider.get_definition(
            workflow_id, version=workflow_version
        )
        if definition is None:
            if workflow_version is None:
                raise KeyError(f"workflow '{workflow_id}' not found")
            raise KeyError(
                f"workflow '{workflow_id}' version '{workflow_version}' not found"
            )
        return definition

    def _resolve_workflow_bindings(
        self, workflow: CompiledWorkflow
    ) -> ResolvedWorkflowBindings | None:
        agent_nodes_with_ref = [
            node_spec
            for node_spec in workflow.node_map.values()
            if node_spec.agent_ref is not None
        ]
        if not agent_nodes_with_ref:
            return None
        if self._deps.agent_binding_resolver is None:
            raise ValueError(
                "workflow declares agent_ref but RuntimeService has no AgentBindingResolver"
            )
        return self._deps.agent_binding_resolver.resolve_workflow_bindings(workflow)

    def _binding_run_state_updates(
        self, bindings: ResolvedWorkflowBindings | None
    ) -> dict[str, object]:
        if bindings is None:
            return {}
        return {"extensions": {"agent_bindings": bindings.to_extension_map()}}

    def _read_agent_binding(self, snapshot, node_id: str) -> ResolvedAgentBinding | None:
        agent_bindings = snapshot.run_state.extensions.get("agent_bindings")
        if not isinstance(agent_bindings, dict):
            return None
        bindings_by_node = agent_bindings.get("agent_bindings_by_node")
        if not isinstance(bindings_by_node, dict):
            return None
        payload = bindings_by_node.get(node_id)
        if not isinstance(payload, dict):
            return None
        return ResolvedAgentBinding.from_map(payload)

    def _resolve_executor_ref(self, snapshot, node_id: str, fallback: str) -> str:
        binding = self._read_agent_binding(snapshot, node_id)
        if binding is None:
            return fallback
        return binding.executor_ref

    def _require_thread(self, thread_id: str) -> ThreadRecord:
        record = self._deps.services.state_store.get_thread_record(thread_id)
        if record is None:
            raise KeyError(f"thread '{thread_id}' not found")
        return record

    def _require_thread_state(self, thread_id: str) -> ThreadState:
        state = self._deps.services.state_store.get_thread_state(thread_id)
        if state is None:
            raise KeyError(f"thread_state '{thread_id}' not found")
        return state

    def _to_reduced_snapshot(self, store_snapshot):
        from core.state.models import ReducedSnapshot

        return ReducedSnapshot(
            thread_record=store_snapshot.thread_record,
            run_record=store_snapshot.run_record,
            thread_state=store_snapshot.thread_state,
            run_state=store_snapshot.run_state,
            node_states=store_snapshot.node_states,
            artifacts=store_snapshot.artifacts,
            interrupts=store_snapshot.interrupts,
            policy_decisions=store_snapshot.policy_decisions,
            side_effects=store_snapshot.side_effects,
        )

    def _emit_thread_event(
        self,
        event_type: str,
        thread: ThreadRecord,
        *,
        payload: dict[str, object] | None = None,
    ) -> ThreadRecord:
        self._event_emitter().emit_thread_event(
            EventDraft(
                event_type=event_type,
                thread_id=thread.thread_id,
                run_id=None,
                payload=dict(payload or {}),
                trace_context=root_trace_context(thread.thread_id, scope="thread"),
            )
        )
        return thread

    def _new_event(
        self,
        event_type: str,
        thread_id: str,
        run_id: str,
        *,
        node_id: str | None = None,
        payload: dict[str, object] | None = None,
        trace_context=None,
        actor_type: str | None = None,
        actor_ref: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> EventDraft:
        return EventDraft(
            event_type=event_type,
            thread_id=thread_id,
            run_id=run_id,
            node_id=node_id,
            payload=dict(payload or {}),
            actor_type=actor_type,
            actor_ref=actor_ref,
            metadata=dict(metadata or {}),
            trace_context=trace_context or self._run_trace_context(run_id),
        )

    def _node_event_type(self, status: NodeStatus) -> str:
        mapping = {
            NodeStatus.SUCCEEDED: "node.succeeded",
            NodeStatus.FAILED: "node.failed",
            NodeStatus.WAITING: "node.waiting",
            NodeStatus.BLOCKED: "node.blocked",
            NodeStatus.SKIPPED: "node.skipped",
            NodeStatus.CANCELLED: "node.cancelled",
        }
        return mapping.get(status, "node.updated")

    def _materialize_services(self, services: RuntimeServices) -> RuntimeServices:
        return RuntimeServices(
            state_store=services.state_store,
            event_store=services.event_store,
            checkpoint_store=services.checkpoint_store,
            policy_engine=services.policy_engine,
            tool_invoker=services.tool_invoker,
            llm_invoker=services.llm_invoker,
            memory_provider=services.memory_provider,
            clock=services.clock or _Clock(),
            id_generator=services.id_generator or _UuidGenerator(),
            logger=services.logger,
        )

    def _event_emitter(self) -> RuntimeEventEmitter:
        return RuntimeEventEmitter(
            event_store=self._deps.services.event_store,
            clock=self._deps.services.clock,
            id_generator=self._deps.services.id_generator,
        )

    def _run_trace_context(self, run_id: str):
        return root_trace_context(run_id, scope="run")

    def _node_trace_context(self, run_id: str, node_id: str, *, attempt: int):
        return child_trace_context(
            self._run_trace_context(run_id),
            scope="node",
            span_id=f"node:{node_id}:{attempt}",
            attributes={"node_id": node_id, "attempt": attempt},
        )

    def _merge_unique(self, base: list[str], incoming: list[str]) -> list[str]:
        merged = list(base)
        for item in incoming:
            if item not in merged:
                merged.append(item)
        return merged

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered
