# 底层内核设计规格书

更新时间：2026-04-10

这份文档是面向代码生成的底层内核规格书。它不再停留在架构讨论层，而是把最底层内核拆解成可实现的模块、类型、接口、状态机、执行流程和约束。

配套关系：

1. [ARCHITECTURE_LANDSCAPE.md](./ARCHITECTURE_LANDSCAPE.md)
   解释为什么我们要采用这类平台路线。
2. [platform-architecture.md](./platform-architecture.md)
   定义平台的总分层与扩展原则。
3. [README.md](./README.md)
   提供当前项目状态、推荐入口与文档索引。
4. 本文档
   定义足以指导代码生成的底层实现规格。

本文档默认目标语言可以是 Python、TypeScript 或 Kotlin，但抽象本身不绑定语言。

## 0. 版本策略

为了避免“设计文档按一个版本写、实际机器按另一个版本跑”的偏差，底层内核开发必须遵守下面这条要求：

1. 主流代码框架、语言特性和工程依赖，默认采用本机当前正在使用的稳定版本。
2. 如果本机当前版本与文档历史约定冲突，以本机当前稳定可执行版本为准，再回写文档。
3. 只有在明确说明需要跨版本兼容时，才为了旧版本主动降级代码写法。

当前会话确认的本机 Python 版本为：

1. `Python 3.13.12`

这意味着当前 Python 代码默认可以使用与 Python 3.13 兼容的主流写法和依赖版本，不需要为了旧解释器优先牺牲表达力。若后续要引入第三方框架，也应优先选择当前主流且兼容 Python 3.13 的版本。

## 1. 设计目标

底层内核必须满足以下目标：

1. 能运行单节点、顺序、多分支、并行、回环和人工中断流程。
2. 能把运行事实稳定落盘，支持 checkpoint、resume 和 replay。
3. 能与上层 agent、tool、memory、governance、domain pack 解耦。
4. 能支撑多个领域共用一套执行内核，而不把领域逻辑写进核心代码。
5. 能在后续替换具体执行框架时，保留核心数据模型和接口契约。

## 2. 非目标

底层内核当前不负责：

1. 设计 prompt。
2. 决定具体领域的业务流程。
3. 决定某个 agent 的业务知识。
4. 构建长期知识库内容。
5. 实现前端交互层。

## 3. 核心原则

## 3.1 State First

运行状态必须比文本输出更可信。凡是控制流程需要依赖的信息，都必须进入 typed state，而不是只存在于自然语言或日志里。

## 3.2 Event Backed

底层不仅维护当前状态，还必须记录结构化事件流。状态用于当前执行，事件用于回放、审计、分析和评测。

## 3.3 Explicit Side Effects

任何外部副作用必须显式记录。底层不能默许“工具已经执行了，但系统里没有痕迹”。

## 3.4 Domain Neutral

底层只承载通用执行语义，不允许出现教育、供应链、医疗等领域专属字段。

## 3.5 Replaceable Runtime

底层数据模型和外部接口应稳定于具体 runtime 引擎之上。可以先用简单执行器实现，后续再对接 LangGraph 或其他图引擎。

## 4. 模块总览

底层内核由以下模块组成：

```text
core/
  runtime/
    runtime_api
    runtime_service
    scheduler
    dispatcher
    executors
    interrupts
  state/
    models
    state_store
    reducers
    selectors
  events/
    event_models
    event_store
    event_bus
  checkpoint/
    checkpoint_models
    checkpoint_store
    snapshot_builder
  workflow/
    workflow_models
    compiler
    join_policies
  contracts/
    workflow_provider
    node_executor
    policy_engine
    tool_invoker
    memory_provider
```

职责拆分：

1. `runtime/`
   对外提供运行控制能力。
2. `state/`
   提供 typed state、state reducer 和 selector。
3. `events/`
   定义事件模型并负责持久化。
4. `checkpoint/`
   负责快照与恢复。
5. `workflow/`
   定义 workflow spec 和节点语义。
6. `contracts/`
   定义外部依赖接口。

## 5. 核心类型系统

以下类型必须在实现最早期稳定下来。

## 5.1 基础标识类型

```text
ThreadId
RunId
NodeId
WorkflowId
CheckpointId
ArtifactId
InterruptId
EventId
PolicyDecisionId
```

要求：

1. 这些 ID 必须是字符串。
2. 生成策略需全局唯一。
3. 所有状态、事件、快照都必须带上关联 ID。

## 5.2 枚举类型

### `ThreadStatus`

```text
created
active
paused
completed
failed
archived
```

### `RunStatus`

```text
queued
running
waiting
interrupted
completed
failed
cancelled
```

### `NodeStatus`

```text
pending
ready
running
waiting
blocked
succeeded
failed
skipped
cancelled
```

### `NodeType`

```text
agent
tool
router
merge
condition
human_gate
noop
```

### `InterruptType`

```text
approval_required
missing_input
system_pause
policy_pause
external_async_wait
```

### `PolicyAction`

```text
allow
deny
require_approval
redact
degrade
retry_later
```

### `SideEffectKind`

```text
read_only
local_write
external_write
```

## 5.3 支撑类型

下面这些类型虽然不是一级实体，但会直接决定后续代码生成是否顺滑，因此需要在底层规格里先固定。

### `BudgetSnapshot`

```text
BudgetSnapshot {
  max_model_tokens: int | null
  max_tool_calls: int | null
  max_external_writes: int | null
  max_runtime_ms: int | null
  metadata: map<string, any>
}
```

### `BudgetUsage`

```text
BudgetUsage {
  model_tokens_used: int
  tool_calls_used: int
  external_writes_used: int
  runtime_ms_used: int
  estimated_cost_usd: number | null
  metadata: map<string, any>
}
```

### `RuntimeServices`

```text
RuntimeServices {
  state_store: StateStore
  event_store: EventStore
  checkpoint_store: CheckpointStore
  policy_engine: PolicyEngine | null
  tool_invoker: ToolInvoker | null
  memory_provider: MemoryProvider | null
  clock: Clock
  id_generator: IdGenerator
  logger: Logger
}
```

要求：

1. `RuntimeServices` 只暴露抽象接口，不暴露领域实现细节。
2. 执行器只能通过 `RuntimeServices` 与外部能力交互。

## 6. 状态模型

## 6.1 `ThreadRecord`

用途：

1. 承载一个长期任务容器。
2. 支持 thread 级别的多次 run。

建议结构：

```text
ThreadRecord {
  thread_id: ThreadId
  thread_type: string
  title: string | null
  owner_id: string | null
  tenant_id: string | null
  status: ThreadStatus
  created_at: datetime
  updated_at: datetime
  current_run_id: RunId | null
  latest_checkpoint_id: CheckpointId | null
  labels: string[]
  metadata: map<string, any>
}
```

约束：

1. `thread_id` 创建后不可变。
2. `current_run_id` 可为空，但同一时刻最多只指向一个活跃 run。

## 6.2 `RunRecord`

用途：

1. 表示一次实际执行尝试。
2. 与 thread 解耦，便于 replay、重跑、审计。

```text
RunRecord {
  run_id: RunId
  thread_id: ThreadId
  workflow_id: WorkflowId
  workflow_version: string
  status: RunStatus
  entry_node_id: NodeId
  started_at: datetime | null
  ended_at: datetime | null
  parent_run_id: RunId | null
  trigger: string
  trigger_payload: map<string, any>
  failure_code: string | null
  failure_message: string | null
  budget_snapshot: BudgetSnapshot
  metadata: map<string, any>
}
```

## 6.3 `ThreadState`

用途：

1. 提供 thread 级共享上下文。
2. 不承载节点瞬时运行细节。

```text
ThreadState {
  thread_id: ThreadId
  goal: string
  global_context: map<string, any>
  shared_memory_refs: string[]
  artifact_ids: ArtifactId[]
  active_run_id: RunId | null
  thread_status: ThreadStatus
  extensions: map<string, any>
  version: int
}
```

领域扩展规则：

1. 领域字段只能进入 `extensions` 或后续领域子 schema。
2. 通用运行代码不得直接依赖某个领域扩展键名。

## 6.4 `RunState`

用途：

1. 表示一次 run 的聚合控制状态。

```text
RunState {
  run_id: RunId
  thread_id: ThreadId
  workflow_id: WorkflowId
  workflow_version: string
  status: RunStatus
  frontier: NodeId[]
  completed_nodes: NodeId[]
  failed_nodes: NodeId[]
  waiting_nodes: NodeId[]
  blocked_nodes: NodeId[]
  active_nodes: NodeId[]
  pending_interrupt_ids: InterruptId[]
  pending_approval_ids: InterruptId[]
  budget_usage: BudgetUsage
  last_event_id: EventId | null
  extensions: map<string, any>
  version: int
}
```

不变量：

1. 一个节点不能同时出现在 `frontier` 和 `completed_nodes`。
2. `active_nodes` 中的节点必须在 `NodeState.status == running`。
3. `status == completed` 时，`frontier` 必须为空。

## 6.5 `NodeState`

用途：

1. 表示单节点运行事实。

```text
NodeState {
  run_id: RunId
  node_id: NodeId
  node_type: NodeType
  status: NodeStatus
  attempt: int
  input_snapshot: map<string, any>
  output_artifact_id: ArtifactId | null
  started_at: datetime | null
  ended_at: datetime | null
  executor_ref: string
  error_code: string | null
  error_message: string | null
  side_effect_ids: string[]
  policy_decision_ids: PolicyDecisionId[]
  metadata: map<string, any>
  version: int
}
```

不变量：

1. `attempt >= 0`
2. `status == succeeded` 时 `output_artifact_id` 可为空，但必须明确说明该节点为控制节点。
3. `status == running` 时 `started_at` 不可为空。

## 6.6 `ArtifactRecord`

```text
ArtifactRecord {
  artifact_id: ArtifactId
  run_id: RunId
  thread_id: ThreadId
  producer_node_id: NodeId
  artifact_type: string
  schema_version: string
  payload_ref: string
  payload_inline: map<string, any> | null
  summary: string | null
  quality_status: string | null
  created_at: datetime
  metadata: map<string, any>
}
```

设计要求：

1. 小产物可内联。
2. 大产物必须支持 `payload_ref` 外部存储。
3. `artifact_type` 必须稳定，用于上层 merge 和 review。

## 6.7 `InterruptRecord`

```text
InterruptRecord {
  interrupt_id: InterruptId
  run_id: RunId
  thread_id: ThreadId
  node_id: NodeId | null
  interrupt_type: InterruptType
  reason_code: string
  reason_message: string
  payload: map<string, any>
  status: string
  created_at: datetime
  resolved_at: datetime | null
  resolution_payload: map<string, any> | null
}
```

## 6.8 `PolicyDecisionRecord`

```text
PolicyDecisionRecord {
  decision_id: PolicyDecisionId
  run_id: RunId
  node_id: NodeId | null
  action: PolicyAction
  policy_name: string
  reason_code: string
  reason_message: string
  redactions: string[]
  created_at: datetime
  metadata: map<string, any>
}
```

## 6.9 `SideEffectRecord`

```text
SideEffectRecord {
  side_effect_id: string
  run_id: RunId
  node_id: NodeId
  kind: SideEffectKind
  target_type: string
  target_ref: string
  action: string
  args_summary: map<string, any>
  is_idempotent: boolean
  succeeded: boolean
  created_at: datetime
  metadata: map<string, any>
}
```

## 7. Workflow 规格

## 7.1 `WorkflowDefinition`

```text
WorkflowDefinition {
  workflow_id: WorkflowId
  name: string
  version: string
  entry_node_id: NodeId
  node_specs: NodeSpec[]
  edge_specs: EdgeSpec[]
  default_retry_policy: RetryPolicy | null
  default_timeout_policy: TimeoutPolicy | null
  allow_cycles: bool
  terminal_conditions: TerminalCondition[]
  metadata: map<string, any>
}
```

## 7.2 `NodeSpec`

```text
NodeSpec {
  node_id: NodeId
  node_type: NodeType
  executor_ref: string
  input_selector: InputSelector
  output_binding: OutputBinding | null
  retry_policy: RetryPolicy | null
  timeout_policy: TimeoutPolicy | null
  approval_policy: ApprovalPolicy | null
  join_policy: JoinPolicy | null
  config: map<string, any>
  metadata: map<string, any>
}
```

## 7.3 `EdgeSpec`

```text
EdgeSpec {
  edge_id: string
  from_node_id: NodeId
  to_node_id: NodeId
  condition: EdgeCondition | null
  metadata: map<string, any>
}
```

要求：

1. 工作流必须可编译成无歧义图结构。
2. `entry_node_id` 必须存在于 `node_specs` 中。
3. 所有 `edge_specs` 的节点引用必须合法。

## 7.4 Workflow 支撑类型

### `InputSelector`

用途：

1. 声明节点从哪里拿输入，而不是把取值逻辑写死在执行器里。

```text
InputSelector {
  sources: InputSource[]
  merge_strategy: replace | shallow_merge | deep_merge
}

InputSource {
  source_type: thread_state | run_state | artifact | literal | interrupt_resolution | memory_result
  source_ref: string
  required: boolean
  path: string | null
}
```

### `OutputBinding`

```text
OutputBinding {
  artifact_type: string
  write_to_thread_extensions: string[] | null
  write_to_run_extensions: string[] | null
}
```

### `RetryPolicy`

```text
RetryPolicy {
  max_attempts: int
  backoff_kind: none | fixed | exponential
  backoff_ms: int
  retryable_error_codes: string[]
  retry_scope: node_only | subgraph | replan_required
}
```

### `TimeoutPolicy`

```text
TimeoutPolicy {
  timeout_ms: int
  on_timeout: fail | retry | interrupt
}
```

### `ApprovalPolicy`

```text
ApprovalPolicy {
  required: boolean
  approver_type: human | service
  approval_reason_code: string
}
```

### `JoinPolicy`

```text
JoinPolicy {
  kind: all_success | any_success | all_done | quorum
  quorum: int | null
}
```

### `EdgeCondition`

```text
EdgeCondition {
  condition_type: always | result_field_equals | result_field_exists | policy_action | custom_ref
  operand_path: string | null
  expected_value: any | null
}
```

### `TerminalCondition`

```text
TerminalCondition {
  condition_type: all_terminal | explicit_node_completed | any_fatal_failure | custom_ref
  node_id: NodeId | null
  config: map<string, any>
}
```

## 7.5 Workflow 编译与校验规则

底层必须区分：

1. `WorkflowDefinition`
   面向配置和声明。
2. `CompiledWorkflow`
   面向 runtime 调度。

### `CompiledWorkflow`

```text
CompiledWorkflow {
  workflow_id: WorkflowId
  version: string
  entry_node_id: NodeId
  node_map: map<NodeId, NodeSpec>
  outgoing_edges: map<NodeId, EdgeSpec[]>
  incoming_edges: map<NodeId, EdgeSpec[]>
  allow_cycles: bool
  contains_cycles: bool
  terminal_conditions: TerminalCondition[]
}
```

编译后 `node_map` 中的 `NodeSpec` 必须已经完成默认策略物化：

1. 如果节点未显式声明 `retry_policy`，则应继承 `default_retry_policy`。
2. 如果节点未显式声明 `timeout_policy`，则应继承 `default_timeout_policy`。

### 编译阶段必须做的校验

1. `workflow_id`、`version` 不可为空。
2. `entry_node_id` 必须存在。
3. 节点 ID 必须唯一。
4. 边 ID 必须唯一。
5. 不能引用不存在的节点。
6. `merge` 节点必须有入边。
7. `human_gate` 节点必须配置 `ApprovalPolicy` 或等价中断配置。
8. `quorum` join policy 必须配置正整数 `quorum`。
9. 如果 `allow_cycles=false`，则必须拒绝检测到的有向环。
10. 如果存在环，必须同时满足 `allow_cycles=true` 且至少有一个显式终止条件。

### 编译结果缓存要求

1. `CompiledWorkflow` 可缓存。
2. cache key 必须包含 `workflow_id + version`。
3. runtime 不应在每次运行时重复做完整编译。

## 7.6 Merge 语义

`merge` 节点是并行安全的关键，因此必须先固定规则。

初期支持三类 merge 策略：

1. `collect_list`
   把多个上游 artifact 收集成列表。
2. `keyed_map`
   按上游节点 ID 或 artifact key 聚合成 map。
3. `custom_ref`
   调用自定义 merge 函数。

要求：

1. merge 节点只消费 artifact，不直接读取其他并行节点的可变中间状态。
2. merge 结果必须产出新的 artifact。
3. merge 失败时必须明确错误来自哪个上游 artifact。

## 8. 状态机规格

## 8.1 Thread 状态转移

允许：

```text
created -> active
active -> paused
active -> completed
active -> failed
paused -> active
completed -> archived
failed -> archived
```

禁止：

1. `archived -> active`
2. `completed -> active` 直接恢复原 run

## 8.2 Run 状态转移

允许：

```text
queued -> running
running -> waiting
running -> interrupted
running -> completed
running -> failed
waiting -> running
interrupted -> running
running -> cancelled
waiting -> cancelled
interrupted -> cancelled
```

约束：

1. `completed`、`failed`、`cancelled` 为终态。
2. 终态 run 不允许再生成新的节点状态更新。

## 8.3 Node 状态转移

允许：

```text
pending -> ready
ready -> running
running -> waiting
running -> blocked
running -> succeeded
running -> failed
waiting -> running
blocked -> ready
pending -> skipped
ready -> cancelled
running -> cancelled
```

约束：

1. `succeeded`、`failed`、`skipped`、`cancelled` 为节点终态。
2. 节点终态后不得再次执行，除非建立新的 attempt 记录并显式重试。

## 9. 事件模型规格

## 9.1 `RuntimeEvent`

```text
RuntimeEvent {
  event_id: EventId
  event_type: string
  thread_id: ThreadId
  run_id: RunId | null
  node_id: NodeId | null
  actor_type: string | null
  actor_ref: string | null
  trace_id: string | null
  span_id: string | null
  parent_span_id: string | null
  sequence_no: int
  timestamp: datetime
  payload: map<string, any>
  metadata: map<string, any>
}
```

补充说明：

1. `trace_id` 用于把同一次 run 内的 run/node/tool/policy 事件串成一条主线。
2. `span_id` 用于标识当前事件所属执行片段。
3. `parent_span_id` 用于表达父子执行关系，例如 `node -> tool`。
4. `metadata.trace_context` 可承载更完整的 trace 属性。

要求：

1. `sequence_no` 对同一 run 单调递增。
2. event 不可更新，只能追加。
3. 每次状态变更前后都必须能追溯到事件。

## 9.2 必须支持的事件类型

```text
thread.created
thread.updated
run.created
run.started
run.waiting
run.interrupted
run.resumed
run.completed
run.failed
run.cancelled
node.ready
node.started
node.waiting
node.blocked
node.succeeded
node.failed
node.skipped
artifact.created
policy.check.requested
policy.check.completed
interrupt.created
interrupt.resolved
side_effect.recorded
checkpoint.created
checkpoint.restored
```

## 9.3 事件载荷要求

每个事件的 payload 至少要包含：

1. 触发原因
2. 关键关联对象 ID
3. 影响摘要
4. 错误或结果摘要

示例：

```text
node.failed.payload = {
  "attempt": 2,
  "error_code": "TOOL_TIMEOUT",
  "error_message": "Tool call exceeded timeout",
  "retryable": true
}
```

## 9.4 `EventStore`

```text
interface EventStore {
  append(event: RuntimeEvent): void
  append_batch(events: RuntimeEvent[]): void
  get(event_id: EventId): RuntimeEvent | null
  list_by_run(run_id: RunId, after_sequence_no?: int, limit?: int): RuntimeEvent[]
  latest_for_run(run_id: RunId): RuntimeEvent | null
}
```

要求：

1. `append_batch` 要么全部成功，要么全部失败。
2. 同一 run 内 `sequence_no` 不允许重复。
3. 事件存储失败时，runtime 必须将当前执行视为失败并禁止继续推进。

## 9.5 Replay 语义

系统必须支持两种 replay：

1. `diagnostic replay`
   用于重建执行轨迹，不重新触发副作用。
2. `execution replay`
   从 checkpoint 恢复继续执行，遵守副作用与 policy 规则。

要求：

1. 默认 replay 模式为 `diagnostic replay`。
2. `execution replay` 不得自动重放未标记为幂等的 `external_write`。
3. replay 必须明确标注来源 checkpoint 和事件区间。

## 10. 执行控制流程

## 10.1 `start_run` 标准流程

```text
1. 校验 thread 是否存在且可启动新 run
2. 读取 workflow definition
3. 创建 RunRecord / RunState / 初始 NodeState 集合
   其中 entry 节点置为 `ready`，其余节点置为 `pending`
4. 写入初始事件:
   - run.created
   - node.ready(entry)
5. 创建初始 checkpoint
6. 调用 scheduler 执行
```

## 10.2 调度循环

建议使用如下伪代码语义：

```text
while run.status in [running, waiting]:
  ready_nodes = scheduler.select_ready_nodes(run_state, workflow)
  if ready_nodes is empty:
    if terminal_condition_met(run_state):
      mark_run_completed()
      break
    if has_unresolved_interrupts(run_state):
      mark_run_interrupted()
      break
    if has_waiting_nodes(run_state):
      mark_run_waiting()
      break
    mark_run_failed("NO_PROGRESS")
    break

  dispatch ready_nodes
  collect node results
  reduce state changes
  emit events
  maybe checkpoint
```

## 10.3 单节点执行流程

```text
1. load NodeSpec
2. build ExecutionContext
3. emit node.started
4. run policy precheck
5. if deny:
     persist decision
     mark node.failed or blocked
     emit events
     return
6. if require_approval:
     create interrupt
     mark node.blocked
     emit events
     checkpoint
     return
7. execute node executor
8. normalize result
9. persist artifact / side effects / node state
10. emit node.succeeded or node.failed
11. compute downstream node readiness
12. checkpoint if configured
```

## 10.4 `resume_run` 标准流程

```text
1. 校验 run 处于 interrupted 或 waiting
2. 读取 unresolved interrupt
3. 应用 resolution_payload
4. 更新 interrupt 状态为 resolved
5. 将对应 waiting / blocked 节点重新置回 ready
6. 恢复 run.status = running
7. 创建恢复事件和 checkpoint
8. 重新进入 scheduler
```

## 11. Scheduler 规格

## 11.1 调度职责

Scheduler 负责：

1. 计算 ready 节点。
2. 处理 join 条件。
3. 控制并行度。
4. 决定何时无进展失败。

Scheduler 不负责：

1. 具体节点逻辑执行。
2. 策略判断。
3. 工具协议转换。

## 11.2 就绪判断规则

节点进入 `ready` 的条件：

1. 自身当前状态为 `pending` 或 `blocked` 可恢复。
2. 所有前置依赖满足。
3. join policy 被满足。
4. 没有未解决的上游 fatal failure 阻断。

## 11.3 Join 策略

初期必须支持：

1. `all_success`
   所有上游成功才触发。
2. `any_success`
   任一上游成功即可触发。
3. `all_done`
   所有上游到终态即可触发。
4. `quorum`
   达到指定数量成功即可触发。

## 11.4 并行控制

配置项：

```text
SchedulerConfig {
  max_parallel_nodes: int
  node_queue_policy: fifo | priority
  deadlock_detection_enabled: boolean
  deadlock_timeout_ms: int
}
```

要求：

1. 并行节点只读共享快照。
2. 并行节点不得直接写同一共享字段。
3. 聚合必须通过 merge 节点或 reducer。

## 11.5 无进展检测

runtime 必须能识别“系统还活着，但实际上已经不再推进”的状态。

触发 `NO_PROGRESS` 的建议条件：

1. 当前没有 `ready` 节点。
2. 没有未解决 interrupt。
3. 没有合法 waiting 外部依赖。
4. terminal condition 不满足。

一旦触发：

1. 记录 `run.failed`
2. `failure_code = NO_PROGRESS`
3. 创建终态 checkpoint

## 12. Executor 契约

## 12.1 `ExecutionContext`

```text
ExecutionContext {
  thread_record: ThreadRecord
  run_record: RunRecord
  thread_state: ThreadState
  run_state: RunState
  node_state: NodeState
  workflow: WorkflowDefinition
  node_spec: NodeSpec
  selected_input: map<string, any>
  services: RuntimeServices
  trace_context: map<string, any>
}
```

## 12.2 `NodeExecutionResult`

```text
NodeExecutionResult {
  status: succeeded | failed | waiting | blocked
  output: map<string, any> | null
  artifact_type: string | null
  interrupts: InterruptRecord[]
  error_code: string | null
  error_message: string | null
  side_effects: SideEffectRecord[]
  next_hints: map<string, any>
  metadata: map<string, any>
}
```

要求：

1. 所有 executor 输出必须结构化。
2. 即使节点输出自然语言，也应包裹在结构化 `output` 内。
3. runtime 不依赖自由文本判断下一步流程。

## 12.3 `NodeExecutor`

```text
interface NodeExecutor {
  can_execute(node_type, executor_ref): boolean
  execute(context: ExecutionContext): NodeExecutionResult
}
```

初期建议实现：

1. `AgentNodeExecutor`
2. `ToolNodeExecutor`
3. `RouterNodeExecutor`
4. `ConditionNodeExecutor`
5. `MergeNodeExecutor`
6. `HumanGateNodeExecutor`

## 12.4 Executor 的输入输出约束

为方便生成稳定代码，执行器必须遵守下面规则：

1. 不得直接修改 `RunState` 或 `ThreadState` 对象。
2. 只能返回 `NodeExecutionResult`，由 reducer 负责真正落状态。
3. 不得在执行器内部静默吞掉错误；必须结构化返回或抛出统一异常。
4. 任何写操作都必须转成 `SideEffectRecord`。

## 12.5 `AgentNodeExecutor` 最小要求

1. 接收结构化输入。
2. 输出结构化 `output`。
3. 可选调用 `ToolInvoker` 和 `MemoryProvider`。
4. 不能直接依赖某个具体领域对象类型。

## 13. State Store 规格

## 13.1 需要的能力

```text
interface StateStore {
  get_thread_record(thread_id)
  save_thread_record(thread_record)
  get_run_record(run_id)
  save_run_record(run_record)
  get_thread_state(thread_id)
  save_thread_state(thread_state)
  get_run_state(run_id)
  save_run_state(run_state)
  get_node_state(run_id, node_id)
  save_node_state(node_state)
  list_node_states(run_id)
  save_artifact(artifact_record)
  list_artifacts(run_id)
  save_interrupt(interrupt_record)
  list_interrupts(run_id)
  save_policy_decision(record)
  save_side_effect(record)
}
```

## 13.2 一致性要求

初期实现可采用单进程事务模型，但必须预留版本字段。

要求：

1. 所有 state 保存都带 `version`。
2. 更新冲突时必须抛出显式并发错误。
3. reducer 负责把状态 patch 合并成新版本。

## 13.3 Reducer 与 Selector

为了避免业务逻辑散落在 runtime service 内，底层必须引入 reducer 和 selector。

### `StatePatch`

```text
StatePatch {
  thread_state_updates: map<string, any>
  run_state_updates: map<string, any>
  node_state_updates: map<string, any>
  artifacts_to_create: ArtifactRecord[]
  interrupts_to_create: InterruptRecord[]
  policy_decisions_to_create: PolicyDecisionRecord[]
  side_effects_to_create: SideEffectRecord[]
}
```

### `StateReducer`

```text
interface StateReducer {
  apply(current_snapshot, patch: StatePatch): ReducedSnapshot
}
```

### `StateSelector`

```text
interface StateSelector {
  select_node_input(snapshot, selector: InputSelector): map<string, any>
  select_ready_nodes(snapshot, workflow: CompiledWorkflow): NodeId[]
  terminal_condition_met(snapshot, workflow: CompiledWorkflow): bool
}
```

规则：

1. reducer 是唯一允许生成新状态版本的组件。
2. selector 是唯一允许解释 `InputSelector` 的组件。
3. runtime service 应尽量只编排，不直接拼状态读写细节。

## 13.4 推荐存储策略

MVP 阶段：

1. 元数据存 sqlite
2. 大产物文件存本地文件系统
3. `payload_ref` 指向本地路径

后续阶段：

1. 元数据可切到 postgres
2. 大产物可切到对象存储

## 14. Checkpoint 规格

## 14.1 `CheckpointRecord`

```text
CheckpointRecord {
  checkpoint_id: CheckpointId
  thread_id: ThreadId
  run_id: RunId
  sequence_no: int
  created_at: datetime
  reason: string
  schema_version: string
  snapshot_ref: string
  frontier_snapshot: NodeId[]
  event_cursor: EventId | null
  metadata: map<string, any>
}
```

## 14.2 `SnapshotPayload`

```text
SnapshotPayload {
  thread_record: ThreadRecord
  run_record: RunRecord
  thread_state: ThreadState
  run_state: RunState
  node_states: NodeState[]
  artifact_ids: ArtifactId[]
  interrupt_ids: InterruptId[]
  policy_decision_ids: PolicyDecisionId[]
  side_effect_ids: SideEffectId[]
  last_event_id: EventId | null
}
```

## 14.3 必须创建 checkpoint 的时机

1. run 初始化完成后
2. 节点成功持久化后
3. 进入中断前
4. run 结束前

可选：

1. 每次 policy 需要审批后
2. 每次 external_write 副作用前后

## 14.4 Checkpoint 恢复要求

恢复 checkpoint 时必须保证：

1. `RunState.version` 与 `NodeState.version` 一致回退到同一逻辑时间点。
2. `frontier`、`pending_interrupt_ids`、`active_nodes` 一并恢复。
3. 未完成的非幂等副作用不得自动标记为成功。
4. 必须发出 `checkpoint.restored` 事件。

## 15. Governance 集成点

治理逻辑不属于底层业务，但底层必须预留集成点。

## 15.1 `PolicyEngine`

```text
interface PolicyEngine {
  pre_node_execute(context): PolicyDecisionRecord
  pre_tool_invoke(descriptor, request, context): PolicyDecisionRecord
  pre_side_effect(context, side_effect): PolicyDecisionRecord
  post_node_execute(context, result): PolicyDecisionRecord | null
}
```

## 15.2 治理处理规则

1. `allow`
   继续执行。
2. `deny`
   节点失败或跳过，具体由 node spec 配置。
3. `require_approval`
   创建 interrupt，run 进入 interrupted。
4. `redact`
   修改输入或输出，再继续执行。
5. `degrade`
   降级到更安全的 executor 或简化流程。

## 16. Memory 集成点

底层不实现具体 memory，但需要提供统一接口。

```text
interface MemoryProvider {
  retrieve(query, scope, top_k): MemoryResult[]
  write(memory_item): string
  summarize(scope): map<string, any>
}
```

要求：

1. memory 读调用必须可审计。
2. 长期 memory 写入应在 finalize 阶段为主。
3. domain pack 可以扩展 scope 类型，但不能改接口骨架。

## 17. Tool 集成点

```text
interface ToolInvoker {
  invoke(tool_ref, tool_input, context): ToolInvocationResult
  get_descriptor(tool_ref): ToolDescriptor | null
  list_tools(query): ToolDescriptor[]
}

ToolInvocationResult {
  success: boolean
  output: map<string, any> | null
  error_code: string | null
  error_message: string | null
  policy_decisions: PolicyDecisionRecord[]
  side_effects: SideEffectRecord[]
  metadata: map<string, any>
}
```

要求：

1. runtime 只看结构化结果。
2. tool adapter 负责把外部协议映射成这个结果。
3. 任何外部写操作必须返回 side effect 记录。

## 18. 错误模型

必须定义统一错误分类，避免后面每个模块各抛一套错误。

## 18.1 错误分类

```text
CONFIG_ERROR
VALIDATION_ERROR
STATE_CONFLICT
WORKFLOW_COMPILE_ERROR
NODE_EXECUTION_ERROR
TOOL_TIMEOUT
TOOL_PROTOCOL_ERROR
POLICY_DENIED
INTERRUPTED
CHECKPOINT_ERROR
STORAGE_ERROR
NO_PROGRESS
UNSUPPORTED_OPERATION
```

## 18.2 重试规则

默认可重试：

1. `TOOL_TIMEOUT`
2. `STORAGE_ERROR`
3. `external_async_wait`

默认不可重试：

1. `WORKFLOW_COMPILE_ERROR`
2. `VALIDATION_ERROR`
3. `POLICY_DENIED`

## 18.3 错误传播规则

1. 节点错误优先写入 `NodeState.error_code / error_message`。
2. run 级失败必须带 `failure_code / failure_message`。
3. 如果错误由上游节点传播，必须在 metadata 中保留根因节点 ID。
4. 对用户展示的错误消息可以被治理层降敏，但内部事件必须保留结构化根因。

## 19. 配置模型

## 19.1 `RuntimeConfig`

```text
RuntimeConfig {
  state_backend: memory | sqlite | postgres
  checkpoint_backend: memory | sqlite | postgres
  artifact_backend: memory | filesystem | object_store
  event_backend: memory | sqlite | postgres
  max_parallel_nodes: int
  auto_checkpoint: boolean
  auto_replay_index: boolean
  default_node_timeout_ms: int
  default_retry_max_attempts: int
  enable_policy_hooks: boolean
  enable_metrics: boolean
}
```

## 19.2 性能与运行约束

虽然首版不追求极致性能，但仍建议固定最低运行约束：

1. 单个节点执行必须支持超时。
2. run 级总耗时必须可统计。
3. 事件和状态持久化不能无限堆在内存里再统一落盘。
4. 大 artifact 默认不内联进 sqlite。

## 20. 多领域适配规则

为了保证未来教育域、软件供应链域等能共用这套内核，必须遵守以下规则。

## 20.1 领域数据进入点

领域数据只允许进入：

1. `ThreadState.extensions`
2. `RunState.extensions`
3. `ArtifactRecord.payload_inline` 或 `payload_ref`
4. 领域自定义 `artifact_type`
5. 领域 workflow config

## 20.2 领域数据禁止进入点

不允许：

1. 扩充底层通用状态的核心必填字段
2. 改写通用状态机定义
3. 在 runtime 中写 if/else 分支判断具体领域

## 20.3 为什么这种规则能支持多领域

因为：

1. 领域差异主要体现在输入、产物和策略，不体现在执行语义本身。
2. 一旦底层对领域产生硬编码，新增行业就会反复侵入内核。

## 20.4 领域扩展命名规则

为了避免多领域长期并存时 `extensions` 混乱，建议采用命名空间：

```text
extensions = {
  "education": {...},
  "supply_chain": {...}
}
```

要求：

1. 领域扩展键必须按领域命名空间收纳。
2. runtime 不得假设任一命名空间存在。
3. artifact_type 建议采用 `domain/type` 风格，例如 `education/lesson_plan`。

## 20.5 领域接入 checklist

一个新领域若要接入底层内核，至少要回答：

1. 它的 thread 级长期上下文是什么。
2. 它的核心 artifact 类型是什么。
3. 它是否需要额外 policy hook。
4. 它的 workflow 是否需要 merge、approval、retry。
5. 它的非幂等副作用有哪些。

## 21. 代码生成建议

如果后面我们要让模型按本文档生成代码，推荐按以下顺序生成：

1. `models`
   先生成所有 record、state、event、policy、checkpoint 数据类。
2. `contracts`
   再生成 `Runtime`、`StateStore`、`CheckpointStore`、`EventStore`、`NodeExecutor`、`PolicyEngine`、`ToolInvoker`、`MemoryProvider` 接口。
3. `stores`
   实现内存版与 sqlite 版。
4. `scheduler`
   实现最小 frontier 调度器。
5. `runtime_service`
   实现 `start_run / resume_run / cancel_run / get_state`。
6. `executors`
   实现 `noop / condition / merge / human_gate`，再接 agent/tool executor。
7. `tests`
   为状态机、checkpoint、interrupt、parallel join 和 side effect logging 写测试。

## 21.1 建议先生成的文件

如果下一步开始正式落代码，建议先生成下面这些文件骨架：

```text
src/core/state/models.py
src/core/events/event_models.py
src/core/workflow/workflow_models.py
src/core/checkpoint/checkpoint_models.py
src/core/contracts/runtime.py
src/core/contracts/state_store.py
src/core/contracts/event_store.py
src/core/contracts/checkpoint_store.py
src/core/contracts/workflow_provider.py
src/core/contracts/node_executor.py
src/core/contracts/policy_engine.py
src/core/contracts/tool_invoker.py
src/core/contracts/memory_provider.py
src/core/runtime/scheduler.py
src/core/runtime/runtime_service.py
src/core/state/reducers.py
src/core/state/selectors.py
```

## 22. 验收标准

当底层内核完成时，至少应通过下面的验收场景：

1. 能运行一个单节点 workflow 并产出 artifact。
2. 能运行一个顺序三节点 workflow。
3. 能运行一个并行 fan-out + merge workflow。
4. 节点被策略拦截时，能生成 interrupt 并恢复。
5. 节点失败后，能按 retry policy 重试。
6. 节点完成后，能创建 checkpoint 并从 checkpoint 恢复。
7. 能完整输出 run 的事件流。
8. 不改 runtime 核心代码的前提下，能接入一个教育域 workflow 和一个供应链域 workflow。

## 23. MVP 边界

第一版底层内核只需要做到：

1. 单进程执行
2. sqlite + filesystem 持久化
3. frontier scheduler
4. checkpoint / resume
5. interrupt / approval
6. event log
7. basic policy hook
8. workflow compiler validation
9. reducer + selector

第一版不需要做到：

1. 分布式执行
2. actor mailbox
3. 动态工作流自修改
4. 自动长期学习
5. 跨租户复杂隔离

## 24. 实现底线

后续生成或编写代码时，必须遵守下面底线：

1. runtime service 不直接依赖任何领域包。
2. 所有控制流判断必须基于 typed state、node result 或 policy result，而不是解析自然语言。
3. 任何 interrupt 都必须有对应 record、event 和 checkpoint。
4. 任何 external write 都必须先经过 policy precheck。
5. 任何状态写入都必须有 version。
6. 任何 run 终态都必须可通过事件和快照回放出来。
7. workflow 必须先编译校验，再允许启动 run。
8. reducer 和 selector 不得被 runtime service 内联替代。

## 25. 关键方案辩论与决策记录

下面这部分不是展示原始思维草稿，而是把关键架构分歧、备选方案、评估标准和最终选择显式记录下来。这样后续我们继续迭代时，不会只记得结论而忘了为什么这样选。

评分维度：

1. 可扩展性
2. 工程可控性
3. 可观测性
4. 恢复与审计能力
5. 首版实现复杂度

评分方式：

1. `高`
2. `中`
3. `低`

## 25.1 执行模型：自由协作式 vs 监督者式 vs 图执行式

### 方案 A：自由协作式 swarm / group chat

特点：

1. agent 通过共享上下文自由协作。
2. 适合探索性任务和原型验证。

优点：

1. 灵活
2. 初始体验强

缺点：

1. 上下文污染严重
2. token 成本高
3. 很难做稳定恢复和审计
4. 对多领域隔离不友好

评分：

1. 可扩展性：中
2. 工程可控性：低
3. 可观测性：低
4. 恢复与审计能力：低
5. 首版实现复杂度：中

### 方案 B：单一 supervisor + specialists

特点：

1. 一个总控 agent 调度专家 agent。
2. 输出一致性较强。

优点：

1. 比 swarm 更可控
2. 统一策略和统一风格较容易

缺点：

1. supervisor 容易成为瓶颈
2. 状态和流程容易隐式埋在 manager prompt 中
3. 不够适合复杂 DAG 和精细化 checkpoint

评分：

1. 可扩展性：中
2. 工程可控性：中
3. 可观测性：中
4. 恢复与审计能力：中
5. 首版实现复杂度：高

### 方案 C：图执行式 runtime

特点：

1. workflow 是显式图结构。
2. 节点和状态机由 runtime 管控。

优点：

1. 最适合 checkpoint、resume、interrupt、parallel、merge
2. 与多领域复用天然兼容
3. 可以在局部节点中嵌入 agent 自主性，而不丢失整体控制

缺点：

1. 前期建模成本更高
2. 需要先定义一套清晰 contract

评分：

1. 可扩展性：高
2. 工程可控性：高
3. 可观测性：高
4. 恢复与审计能力：高
5. 首版实现复杂度：中

最终决策：

1. 选 `图执行式 runtime` 作为底层骨架。
2. 在节点级保留 `agent` 的自主推理，不采用纯死板流程机。

原因：

1. 它最符合我们“长期平台化、多领域扩展、可恢复、可审计”的目标。

## 25.2 状态策略：自由文本上下文 vs 宽松 JSON vs Typed State + Event

### 方案 A：主要依赖 prompt 和聊天记录

优点：

1. 实现最快

缺点：

1. 运行事实不可验证
2. 流程控制脆弱
3. 无法稳定恢复

结论：

1. 不可接受

### 方案 B：宽松 JSON 状态

优点：

1. 比纯文本强
2. 初期灵活

缺点：

1. 字段随项目生长会漂移
2. 上层代码和状态约定会变得脆弱

评分：

1. 可扩展性：中
2. 工程可控性：中
3. 可观测性：中
4. 恢复与审计能力：中
5. 首版实现复杂度：高

### 方案 C：Typed State + Event Log

优点：

1. 状态是事实源
2. 事件是过程源
3. 最适合恢复、回放、评测和多领域扩展

缺点：

1. 前期约束更强
2. 需要额外设计 reducer 和 selector

最终决策：

1. 选 `Typed State + Event Log`

原因：

1. 这是一套能支撑长期演化的底层事实模型。

## 25.3 恢复策略：只存状态 vs 纯事件溯源 vs 混合式

### 方案 A：只存当前状态

优点：

1. 简单

缺点：

1. 难以 replay
2. 难以审计过程

### 方案 B：纯事件溯源

优点：

1. 过程最完整

缺点：

1. 实现成本高
2. 首版恢复代价较大
3. 对开发体验不友好

### 方案 C：快照 + 事件混合式

优点：

1. 既能恢复，也能回放
2. 比纯事件溯源更适合首版平台

缺点：

1. 需要同时维护两套资产

最终决策：

1. 选 `Snapshot + Event` 混合式

原因：

1. 它在工程复杂度和恢复能力之间最均衡。

## 25.4 调度方式：Actor Mailbox vs Frontier Scheduler

### 方案 A：Actor / mailbox / event-driven 全异步模型

优点：

1. 很前沿
2. 适合大规模复杂系统

缺点：

1. 首版实现成本高
2. 容易过度设计

### 方案 B：Frontier-based graph scheduler

优点：

1. 顺序、并行、merge、join 都好表达
2. 容易测试
3. 容易对接 LangGraph 类思路

缺点：

1. 在超大规模分布式场景下不如 actor 模型自然

最终决策：

1. 首版选 `Frontier Scheduler`
2. 接口设计保留未来演进到 actor 模型的空间

原因：

1. 这是当前最适合“先做稳、再增强”的路径。

## 25.5 并行写入策略：共享可变状态 vs Artifact + Merge

### 方案 A：并行节点直接写共享状态

优点：

1. 看起来方便

缺点：

1. 数据竞争高
2. 很难解释最终结果
3. 不利于 replay

结论：

1. 不采用

### 方案 B：每个节点先产出 artifact，再由 merge 节点聚合

优点：

1. 边界清晰
2. 可审计
3. 可回放

缺点：

1. 需要多一个 merge 语义层

最终决策：

1. 选 `Artifact + Merge`

原因：

1. 它最符合多智能体协作里“先产出、再合并”的稳定模式。

## 25.6 多领域策略：领域侵入内核 vs Domain Pack 扩展

### 方案 A：每个领域直接改内核

优点：

1. 短期看起来快

缺点：

1. 新领域越来越难加
2. 内核迅速碎片化

结论：

1. 不采用

### 方案 B：领域通过 domain pack 扩展

优点：

1. 内核稳定
2. 多领域并行开发更容易
3. 测试边界清晰

缺点：

1. 需要提前设计好扩展入口

最终决策：

1. 选 `Domain Pack`

原因：

1. 这是唯一能长期支撑教育、供应链等多行业并存的方案。

## 25.7 为什么当前方案是“最优质”的

这里的“最优质”不是理论上最强，而是在我们的目标函数下最优：

目标函数：

1. 长期可扩展
2. 多领域复用
3. 可恢复可审计
4. 首版能落地
5. 后续能逐步增强

在这个目标函数下，当前组合方案是：

1. `Graph-oriented Runtime`
2. `Typed State + Event Log`
3. `Snapshot + Event` 恢复模型
4. `Frontier Scheduler`
5. `Artifact + Merge` 并行结果归并
6. `Domain Pack` 扩展策略

这套组合的优点是：

1. 不会为了首版速度牺牲结构。
2. 也不会为了未来规模化而在首版过度设计。
3. 既适合 agent 场景，也适合 workflow 场景。

## 25.8 当前代码落地映射

为了避免后续开发再次把“设计目标”和“已实现能力”混在一起，当前底层内核的代码落地状态明确映射如下：

1. 已实现模块
   - `src/core/state/models.py`
   - `src/core/events/event_models.py`
   - `src/core/workflow/workflow_models.py`
   - `src/core/checkpoint/checkpoint_models.py`
   - `src/core/contracts/*`
   - `src/core/state/reducers.py`
   - `src/core/state/selectors.py`
   - `src/core/workflow/compiler.py`
   - `src/core/workflow/registry.py`
   - `src/core/stores/*`
   - `src/core/runtime/scheduler.py`
   - `src/core/runtime/runtime_service.py`
   - `src/core/executors/basic.py`
   - `tests/e2e/test_runtime_e2e.py`

2. 已成立能力
   - typed state
   - event log
   - checkpoint
   - workflow compile
   - frontier scheduling
   - runtime lifecycle
   - built-in execution semantics
   - tool adapter / registry / MCP bridge skeleton
   - tool policy precheck skeleton
   - unified trace/event skeleton
   - baseline end-to-end regression tests
   - in-memory reference adapters

3. 尚未完成但已被文档正式保留的模块
   - `tool / memory / policy` 的真实实现
   - `sqlite / mysql / postgres` 存储适配器
   - `checkpoint restore -> execution replay` 级端到端回归测试

4. 当前阶段定义
   - 现在已经完成的是“Kernel Control Plane MVP”
   - 现在尚未完成的是“Execution Semantics MVP”

## 25.9 后续编码硬边界

从这一轮开始，后续所有编码都必须遵守下面这些硬边界。任何新模块如果破坏这些边界，应优先修正设计或实现，而不是继续堆功能。

1. `RuntimeService`
   只负责 orchestration，不负责 workflow 存储、状态 merge、selector 规则实现、工具协议适配。

2. `FrontierScheduler`
   只负责决策 `dispatch / complete / interrupt / wait / fail`，不直接执行节点，也不直接写 store。

3. `StateReducer`
   是唯一负责将 `StatePatch` 变成新 snapshot 的组件。运行时不得绕过 reducer 悄悄修改核心状态语义。

4. `StateSelector`
   只读状态，不写状态，不做持久化，不执行节点。

5. `WorkflowCompiler`
   只做 workflow 编译、校验、默认策略物化，不承担运行时调度责任。

6. `WorkflowProvider`
   只负责提供 `WorkflowDefinition`，不返回 runtime 私有对象，不参与执行。

7. `StateStore / EventStore / CheckpointStore`
   只负责持久化与读取，不负责业务判断，不负责补写运行语义。

8. `NodeExecutor`
   只消费 `ExecutionContext` 并返回 `NodeExecutionResult`，不直接修改全局状态，不直接推进下一节点。

9. 领域逻辑
   只能进入 domain packs、workflow definitions、executor implementations、tool adapters，不得进入 core runtime 的 typed models 和 contracts 骨架。

## 25.10 面向多领域扩展的实现约束

为了保证后面能同时支持教育、软件供应链以及未来其他领域，当前实现继续遵守以下扩展约束：

1. 领域特定输入
   通过 `WorkflowDefinition`、`InputSelector`、`artifact payload`、`extensions` 进入，不新增核心领域字段。

2. 领域特定流程
   通过 `WorkflowProvider` 注册或装载，不在 `RuntimeService` 中写死教育流、供应链流等分支。

3. 领域特定执行能力
   通过 `NodeExecutor` 的具体实现注入，而不是在 scheduler 或 reducer 中分领域判断。

4. 领域特定工具
   通过 `ToolInvoker` 和 tool adapters 接入，不让 runtime 直接认识外部协议。

5. 领域特定记忆
   通过 `MemoryProvider` 和 `extensions` 承载，不把 learner profile、SBOM、风险画像这类对象塞进内核模型。

6. 领域特定治理
   通过 `PolicyEngine` 和 `PolicyDecisionRecord` 扩展，不在内核里硬编码行业规则。

7. 新领域接入时的优先顺序
   - 先复用 core
   - 再增加 workflow
   - 再增加 executors / tools / policies
   - 最后才考虑是否真的需要扩 core schema

## 26. 结论

如果我们把本文档对应的底层内核真正实现出来，那么后续做教育多智能体、软件供应链多智能体，甚至再扩展到别的行业，都不需要重写底层执行骨架。我们只需要在上层增加新的 registry、workflow、tool adapter 和 domain pack。这就是这份规格书最核心的价值。
