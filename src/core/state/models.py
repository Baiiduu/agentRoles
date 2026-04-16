from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict


JsonMap = Dict[str, Any]

ThreadId = str
RunId = str
NodeId = str
WorkflowId = str
CheckpointId = str
ArtifactId = str
InterruptId = str
EventId = str
PolicyDecisionId = str
SideEffectId = str


class StrEnum(str, Enum):
    """Small compatibility helper for string enums."""

    def __str__(self) -> str:
        return self.value


class ThreadStatus(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class NodeType(StrEnum):
    AGENT = "agent"
    TOOL = "tool"
    ROUTER = "router"
    MERGE = "merge"
    CONDITION = "condition"
    HUMAN_GATE = "human_gate"
    NOOP = "noop"


class InterruptType(StrEnum):
    APPROVAL_REQUIRED = "approval_required"
    MISSING_INPUT = "missing_input"
    SYSTEM_PAUSE = "system_pause"
    POLICY_PAUSE = "policy_pause"
    EXTERNAL_ASYNC_WAIT = "external_async_wait"


class InterruptStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class PolicyAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDACT = "redact"
    DEGRADE = "degrade"
    RETRY_LATER = "retry_later"


class SideEffectKind(StrEnum):
    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL_WRITE = "external_write"


class QueuePolicy(StrEnum):
    FIFO = "fifo"
    PRIORITY = "priority"


class BackendKind(StrEnum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class ArtifactBackendKind(StrEnum):
    MEMORY = "memory"
    FILESYSTEM = "filesystem"
    OBJECT_STORE = "object_store"


def _require_non_negative(value: int, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0, got {value}")


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class BudgetSnapshot:
    max_model_tokens: int | None = None
    max_tool_calls: int | None = None
    max_external_writes: int | None = None
    max_runtime_ms: int | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "max_model_tokens",
            "max_tool_calls",
            "max_external_writes",
            "max_runtime_ms",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative(value, name)


@dataclass
class BudgetUsage:
    model_tokens_used: int = 0
    tool_calls_used: int = 0
    external_writes_used: int = 0
    runtime_ms_used: int = 0
    estimated_cost_usd: float | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_negative(self.model_tokens_used, "model_tokens_used")
        _require_non_negative(self.tool_calls_used, "tool_calls_used")
        _require_non_negative(self.external_writes_used, "external_writes_used")
        _require_non_negative(self.runtime_ms_used, "runtime_ms_used")
        if self.estimated_cost_usd is not None and self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be >= 0")


@dataclass
class ThreadRecord:
    thread_id: ThreadId
    thread_type: str
    title: str | None = None
    owner_id: str | None = None
    tenant_id: str | None = None
    status: ThreadStatus = ThreadStatus.CREATED
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    current_run_id: RunId | None = None
    latest_checkpoint_id: CheckpointId | None = None
    labels: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)
    version: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.thread_id, "thread_id")
        _require_non_empty(self.thread_type, "thread_type")
        _require_unique(self.labels, "labels")
        _require_non_negative(self.version, "version")


@dataclass
class RunRecord:
    run_id: RunId
    thread_id: ThreadId
    workflow_id: WorkflowId
    workflow_version: str
    status: RunStatus
    entry_node_id: NodeId
    started_at: datetime | None = None
    ended_at: datetime | None = None
    parent_run_id: RunId | None = None
    trigger: str = "manual"
    trigger_payload: JsonMap = field(default_factory=dict)
    failure_code: str | None = None
    failure_message: str | None = None
    budget_snapshot: BudgetSnapshot = field(default_factory=BudgetSnapshot)
    metadata: JsonMap = field(default_factory=dict)
    version: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.thread_id, "thread_id")
        _require_non_empty(self.workflow_id, "workflow_id")
        _require_non_empty(self.workflow_version, "workflow_version")
        _require_non_empty(self.entry_node_id, "entry_node_id")
        _require_non_empty(self.trigger, "trigger")
        _require_non_negative(self.version, "version")


@dataclass
class ThreadState:
    thread_id: ThreadId
    goal: str
    global_context: JsonMap = field(default_factory=dict)
    shared_memory_refs: list[str] = field(default_factory=list)
    artifact_ids: list[ArtifactId] = field(default_factory=list)
    active_run_id: RunId | None = None
    thread_status: ThreadStatus = ThreadStatus.CREATED
    extensions: JsonMap = field(default_factory=dict)
    version: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.thread_id, "thread_id")
        _require_non_negative(self.version, "version")
        _require_unique(self.artifact_ids, "artifact_ids")


@dataclass
class RunState:
    run_id: RunId
    thread_id: ThreadId
    workflow_id: WorkflowId
    workflow_version: str
    status: RunStatus
    frontier: list[NodeId] = field(default_factory=list)
    completed_nodes: list[NodeId] = field(default_factory=list)
    failed_nodes: list[NodeId] = field(default_factory=list)
    waiting_nodes: list[NodeId] = field(default_factory=list)
    blocked_nodes: list[NodeId] = field(default_factory=list)
    active_nodes: list[NodeId] = field(default_factory=list)
    pending_interrupt_ids: list[InterruptId] = field(default_factory=list)
    pending_approval_ids: list[InterruptId] = field(default_factory=list)
    budget_usage: BudgetUsage = field(default_factory=BudgetUsage)
    last_event_id: EventId | None = None
    extensions: JsonMap = field(default_factory=dict)
    version: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.thread_id, "thread_id")
        _require_non_empty(self.workflow_id, "workflow_id")
        _require_non_empty(self.workflow_version, "workflow_version")
        _require_non_negative(self.version, "version")
        for field_name in (
            "frontier",
            "completed_nodes",
            "failed_nodes",
            "waiting_nodes",
            "blocked_nodes",
            "active_nodes",
            "pending_interrupt_ids",
            "pending_approval_ids",
        ):
            _require_unique(list(getattr(self, field_name)), field_name)

        overlap = set(self.frontier) & set(self.completed_nodes)
        if overlap:
            raise ValueError(
                "frontier and completed_nodes must not overlap; "
                f"overlap={sorted(overlap)}"
            )
        if self.status == RunStatus.COMPLETED and self.frontier:
            raise ValueError("completed run cannot have frontier nodes")


@dataclass
class NodeState:
    run_id: RunId
    node_id: NodeId
    node_type: NodeType
    status: NodeStatus
    attempt: int = 0
    input_snapshot: JsonMap = field(default_factory=dict)
    output_artifact_id: ArtifactId | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    executor_ref: str = ""
    error_code: str | None = None
    error_message: str | None = None
    side_effect_ids: list[SideEffectId] = field(default_factory=list)
    policy_decision_ids: list[PolicyDecisionId] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)
    version: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.node_id, "node_id")
        _require_non_negative(self.attempt, "attempt")
        _require_non_negative(self.version, "version")
        _require_unique(self.side_effect_ids, "side_effect_ids")
        _require_unique(self.policy_decision_ids, "policy_decision_ids")
        if self.status == NodeStatus.RUNNING and self.started_at is None:
            raise ValueError("running node must have started_at")


@dataclass
class ArtifactRecord:
    artifact_id: ArtifactId
    run_id: RunId
    thread_id: ThreadId
    producer_node_id: NodeId
    artifact_type: str
    schema_version: str
    payload_ref: str | None = None
    payload_inline: JsonMap | None = None
    summary: str | None = None
    quality_status: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("artifact_id", self.artifact_id),
            ("run_id", self.run_id),
            ("thread_id", self.thread_id),
            ("producer_node_id", self.producer_node_id),
            ("artifact_type", self.artifact_type),
            ("schema_version", self.schema_version),
        ):
            _require_non_empty(value, name)
        if not self.payload_ref and self.payload_inline is None:
            raise ValueError("artifact must define payload_ref or payload_inline")


@dataclass
class InterruptRecord:
    interrupt_id: InterruptId
    run_id: RunId
    thread_id: ThreadId
    node_id: NodeId | None
    interrupt_type: InterruptType
    reason_code: str
    reason_message: str
    payload: JsonMap = field(default_factory=dict)
    status: InterruptStatus = InterruptStatus.OPEN
    created_at: datetime = field(default_factory=_utcnow)
    resolved_at: datetime | None = None
    resolution_payload: JsonMap | None = None
    version: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("interrupt_id", self.interrupt_id),
            ("run_id", self.run_id),
            ("thread_id", self.thread_id),
            ("reason_code", self.reason_code),
            ("reason_message", self.reason_message),
        ):
            _require_non_empty(value, name)
        if self.status == InterruptStatus.RESOLVED and self.resolved_at is None:
            raise ValueError("resolved interrupt must have resolved_at")
        _require_non_negative(self.version, "version")


@dataclass
class PolicyDecisionRecord:
    decision_id: PolicyDecisionId
    run_id: RunId
    node_id: NodeId | None
    action: PolicyAction
    policy_name: str
    reason_code: str
    reason_message: str
    redactions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("decision_id", self.decision_id),
            ("run_id", self.run_id),
            ("policy_name", self.policy_name),
            ("reason_code", self.reason_code),
            ("reason_message", self.reason_message),
        ):
            _require_non_empty(value, name)
        _require_unique(self.redactions, "redactions")


@dataclass
class SideEffectRecord:
    side_effect_id: SideEffectId
    run_id: RunId
    node_id: NodeId
    kind: SideEffectKind
    target_type: str
    target_ref: str
    action: str
    args_summary: JsonMap = field(default_factory=dict)
    is_idempotent: bool = False
    succeeded: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("side_effect_id", self.side_effect_id),
            ("run_id", self.run_id),
            ("node_id", self.node_id),
            ("target_type", self.target_type),
            ("target_ref", self.target_ref),
            ("action", self.action),
        ):
            _require_non_empty(value, name)


@dataclass
class StatePatch:
    thread_record_updates: JsonMap = field(default_factory=dict)
    run_record_updates: JsonMap = field(default_factory=dict)
    thread_state_updates: JsonMap = field(default_factory=dict)
    run_state_updates: JsonMap = field(default_factory=dict)
    node_state_updates: dict[NodeId, JsonMap] = field(default_factory=dict)
    node_states_to_upsert: list[NodeState] = field(default_factory=list)
    artifacts_to_create: list[ArtifactRecord] = field(default_factory=list)
    interrupts_to_create: list[InterruptRecord] = field(default_factory=list)
    interrupt_updates: dict[InterruptId, JsonMap] = field(default_factory=dict)
    policy_decisions_to_create: list[PolicyDecisionRecord] = field(default_factory=list)
    side_effects_to_create: list[SideEffectRecord] = field(default_factory=list)


@dataclass
class ReducedSnapshot:
    thread_record: ThreadRecord
    run_record: RunRecord
    thread_state: ThreadState
    run_state: RunState
    node_states: dict[NodeId, NodeState] = field(default_factory=dict)
    artifacts: dict[ArtifactId, ArtifactRecord] = field(default_factory=dict)
    interrupts: dict[InterruptId, InterruptRecord] = field(default_factory=dict)
    policy_decisions: dict[PolicyDecisionId, PolicyDecisionRecord] = field(
        default_factory=dict
    )
    side_effects: dict[SideEffectId, SideEffectRecord] = field(default_factory=dict)


@dataclass
class SchedulerConfig:
    max_parallel_nodes: int = 1
    node_queue_policy: QueuePolicy = QueuePolicy.FIFO
    deadlock_detection_enabled: bool = True
    deadlock_timeout_ms: int = 30_000

    def __post_init__(self) -> None:
        if self.max_parallel_nodes <= 0:
            raise ValueError("max_parallel_nodes must be > 0")
        _require_non_negative(self.deadlock_timeout_ms, "deadlock_timeout_ms")


@dataclass
class RuntimeConfig:
    state_backend: BackendKind = BackendKind.MEMORY
    checkpoint_backend: BackendKind = BackendKind.MEMORY
    artifact_backend: ArtifactBackendKind = ArtifactBackendKind.MEMORY
    event_backend: BackendKind = BackendKind.MEMORY
    max_parallel_nodes: int = 1
    auto_checkpoint: bool = True
    auto_replay_index: bool = True
    default_node_timeout_ms: int = 30_000
    default_retry_max_attempts: int = 0
    enable_policy_hooks: bool = True
    enable_metrics: bool = True

    def __post_init__(self) -> None:
        if self.max_parallel_nodes <= 0:
            raise ValueError("max_parallel_nodes must be > 0")
        _require_non_negative(self.default_node_timeout_ms, "default_node_timeout_ms")
        _require_non_negative(
            self.default_retry_max_attempts, "default_retry_max_attempts"
        )
