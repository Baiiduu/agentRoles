from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from core.checkpoint.checkpoint_models import CheckpointRecord
from core.events.event_models import RuntimeEvent
from core.state.models import (
    ArtifactRecord,
    InterruptRecord,
    JsonMap,
    NodeState,
    NodeStatus,
    PolicyDecisionRecord,
    ReducedSnapshot,
    RunRecord,
    RunState,
    SideEffectRecord,
    ThreadRecord,
    ThreadState,
)
from core.workflow.workflow_models import CompiledWorkflow, NodeSpec

if TYPE_CHECKING:
    from core.agents.bindings import ResolvedAgentBinding
    from core.contracts.llm_invoker import LLMInvoker
    from .checkpoint_store import CheckpointStore
    from .event_store import EventStore
    from .memory_provider import MemoryProvider
    from .policy_engine import PolicyEngine
    from .state_store import StateStore
    from .tool_invoker import ToolInvoker


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ReplayMode(StrEnum):
    DIAGNOSTIC = "diagnostic"
    EXECUTION = "execution"


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self, prefix: str | None = None) -> str: ...


class Logger(Protocol):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


@dataclass
class RuntimeServices:
    state_store: StateStore
    event_store: EventStore
    checkpoint_store: CheckpointStore
    policy_engine: PolicyEngine | None = None
    tool_invoker: ToolInvoker | None = None
    llm_invoker: LLMInvoker | None = None
    memory_provider: MemoryProvider | None = None
    clock: Clock | None = None
    id_generator: IdGenerator | None = None
    logger: Logger | None = None


@dataclass
class ExecutionContext:
    thread_record: ThreadRecord
    run_record: RunRecord
    thread_state: ThreadState
    run_state: RunState
    node_state: NodeState
    workflow: CompiledWorkflow
    node_spec: NodeSpec
    agent_binding: ResolvedAgentBinding | None = None
    selected_input: JsonMap = field(default_factory=dict)
    services: RuntimeServices | None = None
    trace_context: JsonMap = field(default_factory=dict)


@dataclass
class NodeExecutionResult:
    status: NodeStatus
    output: JsonMap | None = None
    artifact_type: str | None = None
    artifact: ArtifactRecord | None = None
    interrupts: list[InterruptRecord] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    policy_decisions: list[PolicyDecisionRecord] = field(default_factory=list)
    side_effects: list[SideEffectRecord] = field(default_factory=list)
    next_hints: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class ToolInvocationResult:
    success: bool
    output: JsonMap | None = None
    error_code: str | None = None
    error_message: str | None = None
    policy_decisions: list[PolicyDecisionRecord] = field(default_factory=list)
    side_effects: list[SideEffectRecord] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class MemoryResult:
    memory_id: str
    scope: str
    score: float | None = None
    payload: JsonMap = field(default_factory=dict)
    source_ref: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.memory_id:
            raise ValueError("memory_id must be non-empty")
        if not self.scope:
            raise ValueError("scope must be non-empty")


@dataclass
class ReplayHandle:
    run_id: str
    source_run_id: str
    checkpoint_id: str | None = None
    mode: ReplayMode = ReplayMode.DIAGNOSTIC
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class RuntimeStateView:
    run_record: RunRecord
    run_state: RunState
    snapshot: ReducedSnapshot | None = None
    latest_checkpoint: CheckpointRecord | None = None
    latest_event: RuntimeEvent | None = None
    metadata: JsonMap = field(default_factory=dict)


@dataclass
class StateStoreSnapshot:
    thread_record: ThreadRecord
    run_record: RunRecord
    thread_state: ThreadState
    run_state: RunState
    node_states: dict[str, NodeState] = field(default_factory=dict)
    artifacts: dict[str, ArtifactRecord] = field(default_factory=dict)
    interrupts: dict[str, InterruptRecord] = field(default_factory=dict)
    policy_decisions: dict[str, PolicyDecisionRecord] = field(default_factory=dict)
    side_effects: dict[str, SideEffectRecord] = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)
