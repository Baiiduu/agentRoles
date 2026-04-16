# Agent Registry Layer Design

更新时间：2026-04-11

这份文档用于把 `Agent Registry Layer` 从平台总架构里单独展开，作为后续落代码前的直接依据。

当前我们的目标不是做一个“会存 prompt 的配置表”，而是做一层真正能支撑多领域扩展的 agent 注册层。

## 1. 先说结论

`Agent Registry Layer` 的职责是：

1. 统一描述 agent 是什么
2. 统一描述 agent 能做什么、依赖什么、受什么约束
3. 让 workflow、executor、tool、memory 不再直接写死 agent 细节
4. 为多版本、替换、评估、领域扩展提供稳定入口

一句话说：

`Agent Registry Layer 负责定义和装配 agent，Runtime 负责运行 agent。`

## 2. 为什么现在要做这一层

当前平台已经有：

1. workflow registry
2. tool registry
3. memory provider
4. runtime / selector / compiler / stores
5. observability / evaluation / memory

但还缺一层来回答这些问题：

1. 系统里到底有哪些 agent
2. 哪个 workflow 节点应该绑定哪个 agent
3. 一个 agent 允许使用哪些 tool
4. 一个 agent 允许访问哪些 memory scope
5. 一个 agent 的版本怎么切换
6. 后面怎么分析“哪个 agent 更有效”

如果没有这一层，后面做教育域、供应链域时，agent 信息很容易散落在：

1. workflow node config
2. executor_ref 命名
3. prompt 模板
4. tool 绑定代码
5. 领域脚本

这样会直接破坏可扩展性。

## 3. 这一层应该做到什么

当前这层完成后，最少应该能做到这些事：

### 3.1 统一注册 agent

每个 agent 都应该有稳定描述，而不是临时字符串。

至少包括：

1. `agent_id`
2. `name`
3. `version`
4. `role`
5. `description`
6. `status`
7. `domain`

### 3.2 描述 agent 能力边界

这一层要能表达：

1. agent 擅长什么任务
2. agent 不该做什么
3. agent 允许调用哪些 tool
4. agent 允许访问哪些 memory scope
5. agent 绑定哪些 policy profile
6. agent 默认使用什么 executor / implementation

### 3.3 为 workflow 提供稳定引用

后面 workflow 节点最好引用的是：

- `agent_ref`

而不是直接写死：

1. prompt 细节
2. tool 列表
3. memory 规则
4. 领域实现路径

### 3.4 支持版本化与替换

后面一定会出现：

1. `teacher_planner:v1`
2. `teacher_planner:v2`
3. `sbom_analyst:v1`

registry 必须支持：

1. 多版本并存
2. 默认版本选择
3. deprecated 标记
4. 平滑替换

### 3.5 成为评估与观测维度

后面我们需要看：

1. 哪个 agent 成功率更高
2. 哪个 agent 更依赖审批
3. 哪个 agent 更常触发某类 tool
4. 哪个 agent 在某领域表现变差

如果没有 registry，后面这些指标会非常散。

## 4. 这一层不应该做什么

这点同样重要。

`Agent Registry Layer` 不应该：

1. 执行 workflow
2. 存 runtime state
3. 直接调用 tool
4. 替代 tool registry
5. 替代 memory provider
6. 变成一个巨大的配置中心
7. 提前承载复杂 prompt orchestration

所以这一层是“定义与装配层”，不是“执行层”。

## 5. 推荐对象模型

当前我建议这层至少有下面这些对象。

### 5.1 AgentDescriptor

这是核心对象，表达一个注册后的 agent。

建议字段：

1. `agent_id`
2. `name`
3. `version`
4. `role`
5. `description`
6. `status`
7. `domain`
8. `tags`
9. `executor_ref`
10. `implementation_ref`
11. `tool_refs`
12. `memory_scopes`
13. `policy_profiles`
14. `capabilities`
15. `input_contract`
16. `output_contract`
17. `metadata`

### 5.2 AgentCapability

用于表达 agent 的能力标签，不直接等同于 tool。

比如：

1. `lesson_planning`
2. `exercise_generation`
3. `sbom_analysis`
4. `vulnerability_triage`

这样后面 orchestration 才能按能力查 agent，而不是按字符串猜。

### 5.3 AgentQuery

用于 registry 检索。

建议支持：

1. `domain`
2. `role`
3. `tags`
4. `capabilities`
5. `tool_ref`
6. `memory_scope`
7. `status`

### 5.4 AgentBinding

如果后面要把 workflow 节点和 agent 分离得更干净，建议预留一个轻量 binding 对象。

它表达的是：

1. workflow 节点需要哪类 agent
2. 最终绑定到哪个 `agent_ref`
3. 是否允许 fallback

MVP 阶段可以不先实现独立类，但设计上应预留。

## 6. 推荐 contracts

这层后面代码实现时，我建议对齐我们现有 registry 风格，先做一个简单清晰的 contract：

### 6.1 AgentRegistry

建议首版方法：

1. `register(descriptor) -> AgentDescriptor`
2. `get(agent_id, version=None) -> AgentDescriptor | None`
3. `get_default(agent_id) -> AgentDescriptor | None`
4. `list(query=None) -> list[AgentDescriptor]`
5. `resolve(agent_ref) -> AgentDescriptor | None`

其中：

- `agent_id` 是稳定标识
- `agent_ref` 可以是 `agent_id` 或 `agent_id:version`

### 6.2 为什么先不做更多方法

当前不建议一开始就加入：

1. `update`
2. `delete`
3. `bulk import`
4. `activation policy routing`
5. `compatibility matrix`

因为这些都会把 MVP 拉重。

## 7. 与现有层的关系

### 7.1 与 Workflow 的关系

workflow 节点后面应通过 `agent_ref` 指向 registry，而不是自己带完整 agent 配置。

理想关系是：

1. workflow 定义“需要什么角色的节点”
2. registry 提供“具体是哪一个 agent”

### 7.2 与 Executor 的关系

`Agent Registry Layer` 不负责执行 agent。

它只告诉 executor：

1. 这个 agent 的 `executor_ref`
2. 这个 agent 的实现引用
3. 这个 agent 允许的 tool / memory / policy 约束

### 7.3 与 Tool Registry 的关系

tool registry 仍然只管理 tool。

agent registry 只管理：

1. agent 能调用哪些 tool
2. agent 的能力组合

所以两层是组合关系，不是替代关系。

### 7.4 与 Memory Services 的关系

agent registry 不直接存 memory。

它只表达：

1. agent 允许使用哪些 scope
2. 默认偏好的 memory usage profile

真正存取还是通过 `MemoryProvider`。

### 7.5 与 Guardrails / Governance 的关系

registry 不做治理执行，但可以承载治理绑定信息，例如：

1. `policy_profiles`
2. `approval_mode`
3. `risk_level`

这样后面治理层可以按 agent profile 生效。

### 7.6 与 Evaluation 的关系

后面 evaluation 可以按 `agent_id / version / role / domain` 聚合结果。

这意味着 registry 也会成为评估维度层。

## 8. 推荐数据流

后面比较理想的数据流是：

1. workflow 节点声明 `agent_ref` 或 `required_capabilities`
2. orchestration / binding 层从 registry 解析目标 agent
3. executor 根据 agent descriptor 拿到：
   - `executor_ref`
   - `implementation_ref`
   - `tool_refs`
   - `memory_scopes`
   - `policy_profiles`
4. 执行结果仍然回到 runtime / reducer / observability

这个数据流里，registry 是“装配入口”，不是“执行中心”。

## 9. MVP 建议范围

为了兼顾尽快落地和高扩展性，第一版建议只做到：

1. `AgentDescriptor`
2. `AgentQuery`
3. `AgentRegistry` contract
4. `InMemoryAgentRegistry`
5. 默认版本解析
6. capability / tool_ref / memory_scope 查询

先不要做：

1. 动态 agent 选择器
2. registry 驱动的自动 workflow 生成
3. 多租户复杂权限
4. agent marketplace
5. prompt 模板托管系统

## 10. 为什么它现在值

当前做这一层最大的价值不是“让平台看起来更完整”，而是：

后面第一个 domain pack 进入时，我们能新增的是：

1. 教育域 agent 描述
2. 供应链域 agent 描述
3. agent 与 tool/memory/policy 的绑定

而不是继续往 workflow 节点和 executor 里塞领域细节。

这就是它当前最关键的工程意义。
