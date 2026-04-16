# 平台总架构设计

更新时间：2026-04-10

这份文档定义我们要构建的多智能体平台的第一性架构。目标不是先做某个具体领域的 agent，而是先把一个可以长期演化、能够承载多个领域、多种编排模式和多类工具协议的内核设计清楚。

本文档只回答四类问题：

1. 平台要解决什么问题。
2. 平台由哪些层组成，每层负责什么。
3. 一次任务在平台里如何流转。
4. 后面要如何按模块实现，而不把系统写乱。

本文档暂不展开：

1. 单个 agent role 的 schema 细节。
2. 编排模式库的具体 DSL。
3. 领域包的具体实现。

配套主文档：

1. [README.md](./README.md)
   当前项目入口、文档索引与换会话交接说明。
2. [core-runtime-design-spec.md](./core-runtime-design-spec.md)
   最底层 `Runtime + Typed State Core` 的可编码规格。
3. [domain-pack-standard-structure.md](./domain-pack-standard-structure.md)
   领域包如何标准化进入平台。

## 1. 目标与约束

### 1.1 平台目标

我们要构建的不是一个“写死角色和 prompt 的 demo”，而是一个多智能体应用内核。这个内核需要满足：

1. 单 agent 能跑，多 agent 能扩。
2. 能支持确定性工作流和 agent 自主决策混合存在。
3. 能支持教育、软件供应链等多个行业领域复用同一套底座。
4. 能支持长期迭代，不因新增 agent、工具或领域能力而推倒重来。
5. 能支持生产级治理能力，包括权限、审计、恢复、评测和观测。

### 1.2 核心约束

我们后续所有设计都要受下面约束：

1. `state` 是头等公民，不能把系统状态散落在 prompt 和临时变量里。
2. `workflow` 是系统骨架，agent 只是工作单元，不是系统边界。
3. `tool protocol` 必须与 agent 逻辑解耦，避免外部系统接入时造成高耦合。
4. `domain capability` 必须通过扩展包接入，不能污染内核。
5. `human-in-the-loop` 必须是原生能力，不是后期补丁。
6. `observability` 和 `evaluation` 必须在架构层预留，而不是项目后期再补。

### 1.3 非目标

现阶段我们明确不追求：

1. 先做一个全能总 agent。
2. 先做无限自由的 swarm 群聊系统。
3. 先绑定某一家框架的全部上层抽象。
4. 先为某个行业写死业务逻辑。

## 2. 设计原则

### 2.1 混合式编排

平台必须支持两种控制逻辑共存：

1. 代码控制流
   适合顺序、并行、分支、超时、重试、审批、恢复。
2. LLM 控制流
   适合规划、选择专家、生成方案、评审和重规划。

我们的原则不是“让模型决定一切”，而是让模型只在高价值的不确定环节做判断。

### 2.2 可替换内核

平台的公共抽象要先于具体框架。换句话说，我们可以用 LangGraph、AutoGen、ADK 或自研 runtime 实现执行层，但业务层不应直接依赖某个框架的私有对象模型。

### 2.3 强边界

每个 agent、工具和领域扩展都必须有清晰边界：

1. 能看到什么上下文。
2. 能访问什么工具。
3. 能产出什么结构。
4. 能触发什么事件。
5. 出错后由谁接管。

### 2.4 先结构后能力

先把系统结构搭稳，再逐步增加 agent 数量、工具数量和领域复杂度。否则很容易得到一个表面很智能、内部却不可维护的系统。

## 3. 平台总览

平台采用分层架构：

```text
+-------------------------------------------------------------+
|                         Domain Packs                        |
|      education / supply-chain / future domain packs        |
+-------------------------------------------------------------+
|                Orchestration Pattern Library                |
|   router / handoff / planner-loop / parallel / approval    |
+-------------------------------------------------------------+
|                     Agent Registry Layer                    |
|       role metadata / capability contracts / policies       |
+-------------------------------------------------------------+
|                   Tool Adapter / MCP Layer                  |
|   local tools / http APIs / db / retrievers / MCP bridges  |
+-------------------------------------------------------------+
|                       Memory Services                       |
|  thread memory / task memory / long-term memory / retrieval|
+-------------------------------------------------------------+
|                   Guardrails & Governance                   |
| authz / approvals / content checks / policy / audit log    |
+-------------------------------------------------------------+
|                  Observability & Evaluation                 |
| traces / metrics / replay / datasets / regressions         |
+-------------------------------------------------------------+
|                   Runtime + Typed State Core                |
|   execution engine / state machine / checkpoint / resume   |
+-------------------------------------------------------------+
```

这不是“从上到下独立运行”的静态堆叠，而是一个以内核为中心、上层逐层受控扩展的体系。

## 4. 分层设计

## 4.1 Runtime Core

这是平台的心脏，负责一次任务如何真正被执行。

职责：

1. 启动线程或任务实例。
2. 维护执行状态机。
3. 调度节点执行。
4. 处理并行、等待、超时、重试、取消。
5. 提供 checkpoint、resume、replay。
6. 提供 human interrupt 和 human resume。

输出：

1. 统一的任务执行结果。
2. 中间状态快照。
3. 事件流与运行轨迹。

不负责：

1. 角色定义。
2. 工具具体实现。
3. 领域业务逻辑。

关键设计要求：

1. runtime 只依赖抽象接口，不直接写死具体 agent。
2. runtime 必须能跑顺序、并行、循环和中断节点。
3. runtime 必须能将所有副作用显式记录。

## 4.2 Typed State

state 是整个平台的事实来源。后续任何模块都不能绕开它偷偷保存关键运行信息。

建议至少拆成五类状态：

1. `ThreadState`
   表示一次完整会话或任务线程的总状态。
2. `TaskState`
   表示某个子任务或节点的执行状态。
3. `ArtifactState`
   表示计划、报告、草稿、分析结果、证据等产物。
4. `ReviewState`
   表示评审、审批、人工反馈和回修状态。
5. `MemoryState`
   表示短期上下文、长期记忆、检索命中和摘要缓存。

关键设计要求：

1. 状态结构化，优先 schema 化，不依赖自然语言解析。
2. 状态变更可追踪，所有更新都能知道是谁、何时、为何修改。
3. 状态支持版本化，为恢复、回放和迁移做准备。
4. 状态层不绑具体领域字段，领域数据通过扩展字段或领域子 schema 注入。

## 4.3 Agent Registry

agent registry 不是简单的“角色名单”，而是平台的能力注册中心。

每个 agent 在 registry 中至少要声明：

1. 标识信息
   名称、版本、所有者、描述。
2. 职责边界
   这个 agent 负责什么，不负责什么。
3. 输入输出契约
   输入 schema、输出 schema、错误 schema。
4. 可用工具
   可调用哪些工具、是否可写、是否需要审批。
5. 可访问上下文
   能读取哪些状态片段和历史窗口。
6. 安全策略
   是否允许外网、文件系统、代码修改、敏感信息访问。
7. 执行偏好
   模型、温度、预算、超时、重试策略。

registry 的价值在于让 agent 成为“可治理能力单元”，而不是一段难以管理的 prompt。

## 4.4 Orchestration Layer

这一层描述“如何组织 agent 协作”，而不是“agent 本身如何思考”。

平台初期只需要支持少量高价值模式：

1. Router / Handoff
2. Planner -> Executor -> Reviewer
3. Parallel Fan-out -> Merge
4. Approval Gate
5. Retry / Replan Loop

这一层应提供：

1. 模式抽象
2. 节点组合能力
3. 统一输入输出约定
4. 终止条件与异常传播规则

注意点：

1. 编排模式应尽量声明式，而不是把流程全埋在 prompt 里。
2. 编排层依赖 registry 和 state，不直接操作具体工具。

## 4.5 Tool Adapter Layer

这一层负责把外部世界接进来。

它要统一抽象以下能力源：

1. 本地函数
2. 命令行工具
3. HTTP API
4. 数据库
5. 检索器和知识库
6. 文件系统
7. MCP server

我们需要一个统一工具契约，至少包含：

1. 工具名称与描述
2. 输入输出 schema
3. 权限级别
4. 是否有副作用
5. 是否需要审批
6. 超时、重试、幂等性策略

关键原则：

1. agent 不直接感知工具底层协议。
2. 工具注册与权限策略分离。
3. MCP 是优先兼容方向，但不是唯一接入方式。

## 4.6 Memory Services

记忆层不能等同于“把聊天记录拼进去”。

我们要从一开始就区分：

1. 会话短期记忆
   当前线程内的上下文和摘要。
2. 任务记忆
   某类任务中间产物、阶段结论、缓存。
3. 用户或实体长期记忆
   例如教育中的 learner profile，供应链中的组件风险画像。
4. 领域知识记忆
   检索型知识库、规范库、规则库、案例库。

这一层提供：

1. 写入策略
2. 检索策略
3. 压缩与摘要策略
4. 生命周期和淘汰策略

## 4.7 Guardrails & Governance

如果没有治理层，多智能体系统在真实环境里很快会失控。

这一层至少处理：

1. 输入校验
2. 输出校验
3. 权限控制
4. 高风险动作审批
5. 敏感信息治理
6. 审计日志
7. 策略拒绝与降级处理

典型高风险动作包括：

1. 修改代码
2. 删除文件
3. 写入数据库
4. 对外发送消息
5. 调用高成本外部 API
6. 输出高风险业务建议

这一层必须与 runtime 深度集成，而不是作为外围装饰。

## 4.8 Observability & Evaluation

多智能体系统如果不可观测，就无法稳定迭代。

这一层至少需要：

1. Trace
   看见任务如何拆分、路由、调用工具和回环。
2. Metrics
   看见时延、成本、成功率、重试率、中断率。
3. Replay
   能复盘一次失败流程。
4. Evaluation
   能用固定数据集回归测试任务表现。

这层的意义是把“感觉 agent 变好了”变成“可验证地知道哪里变好了”。

## 4.9 Domain Packs

领域包是平台的上层扩展单元。

一个领域包应只包含：

1. 领域 agent 定义
2. 领域工作流组合
3. 领域状态扩展
4. 领域工具适配
5. 领域评测样例
6. 领域策略规则

不应包含：

1. 对 runtime 的侵入式修改
2. 通用工具层的私有改造
3. 核心状态模型的破坏性改写

领域包的存在意义是让平台具备“行业化”，但不丢失“平台化”。

## 5. 核心对象模型

为了让后面代码清晰，我们需要尽早统一对象视角。

平台里至少存在以下一级对象：

1. `Thread`
   一次完整任务线程。
2. `Run`
   某次实际执行实例。
3. `Workflow`
   编排定义。
4. `Node`
   工作流中的执行单元。
5. `AgentRole`
   一种注册后的 agent 能力。
6. `Tool`
   一种可调用能力。
7. `Artifact`
   任意中间或最终产物。
8. `Review`
   自动或人工评审记录。
9. `Checkpoint`
   可恢复的执行快照。
10. `PolicyDecision`
   某次治理决策结果。

它们之间的建议关系：

1. `Thread` 包含多个 `Run`
2. `Run` 绑定一个 `Workflow`
3. `Workflow` 由多个 `Node` 组成
4. `Node` 可执行一个 `AgentRole`、`Tool` 或控制动作
5. `Run` 产生多个 `Artifact`
6. `Review` 和 `PolicyDecision` 挂接在 `Run` 与 `Artifact` 上
7. `Checkpoint` 绑定 `Run` 的阶段状态

## 6. 执行生命周期

一次任务建议走下面的标准生命周期：

1. Intake
   接收输入，创建 thread/run，做基础校验。
2. Normalize
   标准化输入，补齐上下文，加载基础记忆。
3. Plan
   生成任务计划或选择合适工作流。
4. Dispatch
   根据工作流调度 agent、tool 或人工节点。
5. Execute
   执行具体节点，记录状态变更和副作用。
6. Review
   自动评审、规则评审或人工评审。
7. Revise
   必要时回修、重试或重规划。
8. Finalize
   产出最终结果，写入长期记忆和审计记录。
9. Close
   完成线程、归档指标和轨迹。

这个生命周期不是所有流程都必须经过全部阶段，但平台必须原生支持这些阶段。

## 7. 扩展策略

为了保证可拓展性，我们的扩展必须分层进行。

### 7.1 扩展一个新 agent

只应影响：

1. agent registry
2. 可选的 workflow 组合
3. 可选的 eval case

不应影响：

1. runtime core
2. 其他 agent 的实现
3. 工具基础协议

### 7.2 扩展一个新工具

只应影响：

1. tool adapter 注册
2. 权限策略
3. 可选的 agent capability 绑定

### 7.3 扩展一个新领域

只应影响：

1. 新的 domain pack
2. 领域状态 schema
3. 领域 workflow
4. 领域工具
5. 领域评测集

### 7.4 更换底层执行框架

如果后面要从一个 runtime 切到另一个 runtime，理论上只应影响：

1. runtime adapter
2. workflow compiler 或 binding 层

业务层对象不应大面积变化。这是我们保持长期技术自由度的关键。

## 8. 推荐代码结构

虽然现在还没开始正式编码，但我建议从一开始就按平台分层组织目录，而不是按脚本堆文件。

推荐骨架如下：

```text
agentsRoles/
  docs/
    platform-architecture.md
    architecture-landscape.md
  src/
    core/
      runtime/
      state/
      workflow/
      events/
      checkpoint/
    registry/
      agents/
      tools/
      policies/
    services/
      memory/
      governance/
      observability/
      evaluation/
    adapters/
      llm/
      tools/
      mcp/
      storage/
    domain_packs/
      education/
      supply_chain/
    app/
      bootstrap/
      config/
      api/
  tests/
    unit/
    integration/
    evals/
```

目录名后面可以再精修，但“按平台层次组织，而不是按实验脚本组织”的原则最好从第一天就确定。

## 9. 第一阶段实现顺序

为了把第一块真正做到稳，我建议实现顺序严格遵守下面顺序：

1. 定义核心对象和 typed state
2. 定义 runtime interface 和 checkpoint interface
3. 定义 agent registry 和 tool registry 抽象
4. 定义 workflow node 抽象和最小编排图
5. 加入 governance hook 和 trace hook
6. 做一个最小 end-to-end 流程
7. 最后才接入第一个领域包

这样做的好处是，后面每一层都建立在清晰契约上，而不是不断返工。

## 10. 我们当前的架构决策

基于目前目标，我建议先固定以下决策：

1. 平台内核采用 `graph-oriented runtime` 思路。
2. 平台状态采用 `typed state + versioned snapshots`。
3. agent 通过 `registry + contracts` 注册，不直接散落在业务代码里。
4. 工具层采用 `adapter + protocol` 模式，优先兼容 MCP。
5. 平台默认支持 `interrupt / resume / approval / replay`。
6. 领域能力以 `domain pack` 方式扩展。

这些决策不是为了限制后续实现，而是为了防止后面在扩展时失去结构。

## 11. 架构风险

下面这些风险要从现在就警惕：

1. 把 prompt 当作架构
   结果是系统不可维护、不可测试、不可复用。
2. 让 agent 直接持有太多工具
   结果是选择混乱、权限边界失控。
3. 把领域逻辑写进 runtime
   结果是后面每扩一个行业都要改内核。
4. 没有统一状态模型
   结果是恢复、追踪和评测都做不稳。
5. 没有评测和回放
   结果是每次改动都只能“凭感觉”判断好坏。

## 12. 下一步边界

在这份文档之后，我们只应该继续推进两类内容之一：

1. 把 `AgentRole` 的标准 schema 设计清楚。
2. 把基础编排模式库设计清楚。

在那之前，不建议开始大量写具体业务 agent。

## 12.1 当前平台阶段判断

结合当前已经落地的代码，平台现在处于一个很关键的中间阶段：

1. 平台总架构已经不再停留在纯概念层。
2. `Runtime + Typed State Core` 已经形成最小可运行主干。
3. 平台现在最缺的不是再补一个新分层，而是把执行语义和端到端验证补齐。

当前已经具备的底层平台能力：

1. typed models
2. stable contracts
3. reducer / selector
4. workflow compiler
5. in-memory stores
6. runtime service
7. frontier scheduler

当前仍然属于下一阶段重点的内容：

1. `basic executors`
2. `policy / tool / memory` 的真实 adapter
3. `sqlite / mysql / postgres` 持久化实现
4. 面向领域场景的 end-to-end regression tests

结论：

1. 现在的工作重点应该从“继续画更多层”转到“沿当前分层把缺失模块补齐”。
2. 后续如果继续改设计，优先是收敛边界，不是增加抽象层数。

## 12.2 后续推进顺序建议

为了兼顾高扩展性和实际落地效率，后续建议严格按下面顺序推进：

1. `basic executors`
   先把 `noop / condition / merge / human_gate` 补齐。

2. `end-to-end runtime tests`
   覆盖 completed / waiting / interrupted / resume / merge / failure / checkpoint restore。

3. `persistent stores`
   在内存版稳定之后再接 `sqlite`，之后再考虑 `mysql/postgres`。

4. `tool / memory / policy adapters`
   让 runtime 真正和外部能力形成可替换集成。

5. `domain packs`
   先做教育或软件供应链中的一个，验证“核心不被污染”的前提下是否能平滑接入。

## 13. 一句话总结

我们要做的不是“一个会聊天的多 agent demo”，而是一套以 `runtime + state + contracts + governance + domain packs` 为核心的多智能体平台内核。只有先把这个骨架搭稳，后面教育领域、软件供应链领域这些真实项目才能持续迭代，而且不会越做越乱。
