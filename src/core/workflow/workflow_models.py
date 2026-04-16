from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.state.models import JsonMap, NodeId, NodeType, WorkflowId


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MergeStrategyKind(StrEnum):
    REPLACE = "replace"
    SHALLOW_MERGE = "shallow_merge"
    DEEP_MERGE = "deep_merge"


class InputSourceType(StrEnum):
    THREAD_STATE = "thread_state"
    RUN_STATE = "run_state"
    ARTIFACT = "artifact"
    LITERAL = "literal"
    INTERRUPT_RESOLUTION = "interrupt_resolution"
    MEMORY_RESULT = "memory_result"


class RetryScope(StrEnum):
    NODE_ONLY = "node_only"
    SUBGRAPH = "subgraph"
    REPLAN_REQUIRED = "replan_required"


class BackoffKind(StrEnum):
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class TimeoutBehavior(StrEnum):
    FAIL = "fail"
    RETRY = "retry"
    INTERRUPT = "interrupt"


class ApproverType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"


class JoinPolicyKind(StrEnum):
    ALL_SUCCESS = "all_success"
    ANY_SUCCESS = "any_success"
    ALL_DONE = "all_done"
    QUORUM = "quorum"


class EdgeConditionType(StrEnum):
    ALWAYS = "always"
    RESULT_FIELD_EQUALS = "result_field_equals"
    RESULT_FIELD_EXISTS = "result_field_exists"
    POLICY_ACTION = "policy_action"
    CUSTOM_REF = "custom_ref"


class TerminalConditionType(StrEnum):
    ALL_TERMINAL = "all_terminal"
    EXPLICIT_NODE_COMPLETED = "explicit_node_completed"
    ANY_FATAL_FAILURE = "any_fatal_failure"
    CUSTOM_REF = "custom_ref"


class MergeMode(StrEnum):
    COLLECT_LIST = "collect_list"
    KEYED_MAP = "keyed_map"
    CUSTOM_REF = "custom_ref"


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


@dataclass
class InputSource:
    source_type: InputSourceType
    source_ref: str
    required: bool = True
    path: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.source_ref, "source_ref")


@dataclass
class InputSelector:
    sources: list[InputSource] = field(default_factory=list)
    merge_strategy: MergeStrategyKind = MergeStrategyKind.REPLACE

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("InputSelector must define at least one source")


@dataclass
class OutputBinding:
    artifact_type: str
    write_to_thread_extensions: list[str] | None = None
    write_to_run_extensions: list[str] | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.artifact_type, "artifact_type")


@dataclass
class RetryPolicy:
    max_attempts: int
    backoff_kind: BackoffKind = BackoffKind.NONE
    backoff_ms: int = 0
    retryable_error_codes: list[str] = field(default_factory=list)
    retry_scope: RetryScope = RetryScope.NODE_ONLY

    def __post_init__(self) -> None:
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be >= 0")
        if self.backoff_ms < 0:
            raise ValueError("backoff_ms must be >= 0")


@dataclass
class TimeoutPolicy:
    timeout_ms: int
    on_timeout: TimeoutBehavior = TimeoutBehavior.FAIL

    def __post_init__(self) -> None:
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")


@dataclass
class ApprovalPolicy:
    required: bool
    approver_type: ApproverType
    approval_reason_code: str

    def __post_init__(self) -> None:
        if self.required:
            _require_non_empty(self.approval_reason_code, "approval_reason_code")


@dataclass
class JoinPolicy:
    kind: JoinPolicyKind = JoinPolicyKind.ALL_SUCCESS
    quorum: int | None = None

    def __post_init__(self) -> None:
        if self.kind == JoinPolicyKind.QUORUM:
            if self.quorum is None or self.quorum <= 0:
                raise ValueError("quorum join policy requires quorum > 0")


@dataclass
class EdgeCondition:
    condition_type: EdgeConditionType
    operand_path: str | None = None
    expected_value: Any | None = None

    def __post_init__(self) -> None:
        if self.condition_type == EdgeConditionType.RESULT_FIELD_EQUALS and not self.operand_path:
            raise ValueError("RESULT_FIELD_EQUALS requires operand_path")


@dataclass
class TerminalCondition:
    condition_type: TerminalConditionType
    node_id: NodeId | None = None
    config: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.condition_type == TerminalConditionType.EXPLICIT_NODE_COMPLETED and not self.node_id:
            raise ValueError("EXPLICIT_NODE_COMPLETED requires node_id")


@dataclass
class MergeStrategySpec:
    mode: MergeMode
    key_field: str | None = None
    custom_ref: str | None = None

    def __post_init__(self) -> None:
        if self.mode == MergeMode.CUSTOM_REF and not self.custom_ref:
            raise ValueError("CUSTOM_REF merge mode requires custom_ref")


@dataclass
class NodeSpec:
    node_id: NodeId
    node_type: NodeType
    executor_ref: str
    input_selector: InputSelector
    agent_ref: str | None = None
    output_binding: OutputBinding | None = None
    retry_policy: RetryPolicy | None = None
    timeout_policy: TimeoutPolicy | None = None
    approval_policy: ApprovalPolicy | None = None
    join_policy: JoinPolicy | None = None
    merge_strategy: MergeStrategySpec | None = None
    config: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.node_id, "node_id")
        _require_non_empty(self.executor_ref, "executor_ref")
        if self.agent_ref is not None:
            _require_non_empty(self.agent_ref, "agent_ref")
        if self.agent_ref is not None and self.node_type != NodeType.AGENT:
            raise ValueError("only agent nodes may declare agent_ref")
        if self.node_type == NodeType.MERGE and self.merge_strategy is None:
            raise ValueError("merge node must declare merge_strategy")
        if self.node_type == NodeType.HUMAN_GATE and self.approval_policy is None:
            raise ValueError("human_gate node must declare approval_policy")


@dataclass
class EdgeSpec:
    edge_id: str
    from_node_id: NodeId
    to_node_id: NodeId
    condition: EdgeCondition | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.edge_id, "edge_id")
        _require_non_empty(self.from_node_id, "from_node_id")
        _require_non_empty(self.to_node_id, "to_node_id")


@dataclass
class WorkflowDefinition:
    workflow_id: WorkflowId
    name: str
    version: str
    entry_node_id: NodeId
    node_specs: list[NodeSpec]
    edge_specs: list[EdgeSpec]
    default_retry_policy: RetryPolicy | None = None
    default_timeout_policy: TimeoutPolicy | None = None
    allow_cycles: bool = False
    terminal_conditions: list[TerminalCondition] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("workflow_id", self.workflow_id),
            ("name", self.name),
            ("version", self.version),
            ("entry_node_id", self.entry_node_id),
        ):
            _require_non_empty(value, field_name)
        if not self.node_specs:
            raise ValueError("workflow must define at least one node")

        node_ids = [node.node_id for node in self.node_specs]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("workflow contains duplicate node IDs")
        if self.entry_node_id not in set(node_ids):
            raise ValueError("entry_node_id must exist in node_specs")

        edge_ids = [edge.edge_id for edge in self.edge_specs]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("workflow contains duplicate edge IDs")


@dataclass
class CompiledWorkflow:
    workflow_id: WorkflowId
    version: str
    entry_node_id: NodeId
    node_map: dict[NodeId, NodeSpec]
    outgoing_edges: dict[NodeId, list[EdgeSpec]]
    incoming_edges: dict[NodeId, list[EdgeSpec]]
    allow_cycles: bool = False
    contains_cycles: bool = False
    terminal_conditions: list[TerminalCondition] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_non_empty(self.workflow_id, "workflow_id")
        _require_non_empty(self.version, "version")
        _require_non_empty(self.entry_node_id, "entry_node_id")
        if self.entry_node_id not in self.node_map:
            raise ValueError("compiled workflow entry_node_id must exist in node_map")
        if self.contains_cycles and not self.allow_cycles:
            raise ValueError("compiled workflow cannot contain cycles when allow_cycles is False")
