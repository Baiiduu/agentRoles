# 多智能体编排架构学习基线

更新时间：2026-04-10

这份文档的目标不是收集“框架名词”，而是提炼当前主流与前沿 agent 系统已经收敛出的公共架构规律，作为我们后续构建可拓展多智能体平台的设计基线。

## 1. 先定一个总原则

不是所有复杂任务都需要多智能体。

从官方文档和一线系统设计里能看到一个共同结论：如果单智能体加工具已经能稳定解决问题，就不要过早上多智能体。真正适合多智能体的场景，通常至少满足下面一项：

1. 上下文太大，需要拆分不同角色各自持有局部上下文。
2. 任务天然可并行，需要多个子任务同时推进。
3. 需要强边界，要求不同角色拥有不同工具、权限或审计策略。
4. 需要不同专业能力长期演化，希望不同团队独立维护不同 agent。
5. 需要把“开放式智能决策”和“确定性流程控制”结合起来。

这意味着我们后续的目标不该是“为了多智能体而多智能体”，而应该是构建一个“单 agent 可跑，必要时自然升级为多 agent”的平台。

## 2. 当前主流的多智能体编排模式

### 模式 A：Router / Handoff

核心思想：先用一个分诊 agent 判断任务属于哪个专家，再把当前回合或后续流程切给对应 agent。

代表：

1. OpenAI Agents SDK 的 `handoffs`
2. Semantic Kernel 的 `Handoff Orchestration`
3. AutoGen 的 `Swarm`

适用场景：

1. 客服分流
2. 多领域问答
3. 一个入口，多个专家角色

优点：

1. 结构简单
2. 专家 prompt 清晰
3. 易于扩展新角色

缺点：

1. 跨角色共享状态容易混乱
2. 复杂任务容易退化成频繁切换
3. 不适合强依赖的长链路协作

### 模式 B：Supervisor / Manager + Specialists

核心思想：一个管理者 agent 保持全局控制权，专家 agent 作为工具或受控执行单元被调用。

代表：

1. OpenAI Agents SDK 的 `agents as tools`
2. LangGraph Supervisor
3. CrewAI 的 hierarchical process
4. Magentic-One 的 orchestrator 思路

适用场景：

1. 研究报告
2. 代码生成
3. 需要统一输出风格和统一安全策略的系统

优点：

1. 总控权集中
2. 容易做统一 guardrails
3. 最终输出一致性高

缺点：

1. manager 容易成为瓶颈
2. 过多子 agent 时调度复杂度上升
3. manager prompt 设计不好会导致“伪协作”

### 模式 C：Planner -> Executor -> Critic / Reviewer

核心思想：先规划，再执行，再评审，再按反馈回环。

代表：

1. OpenAI 官方文档里的 chained agents 和 evaluator loop
2. Google ADK 的 `SequentialAgent` 与 `LoopAgent`
3. 很多代码 agent、研究 agent 的默认内核

适用场景：

1. 写作
2. 代码修复
3. 安全审计
4. 方案设计

优点：

1. 容易解释
2. 容易加人工审核
3. 适合迭代优化

缺点：

1. 延迟较高
2. 容易形成无效循环
3. 需要明确终止条件

### 模式 D：Graph / Workflow DAG

核心思想：把 agent 看作图中的节点，把状态更新、分支、并行、汇合和循环显式建模。

代表：

1. LangGraph
2. AutoGen `GraphFlow`
3. CrewAI `Flows`
4. Google ADK `Sequential/Parallel/Loop` workflow agents
5. Semantic Kernel `Sequential/Concurrent/GroupChat/Handoff`

适用场景：

1. 长流程业务
2. 需要可恢复执行
3. 需要人机中断点
4. 需要状态持久化和审计

优点：

1. 可观测性强
2. 容易持久化
3. 更适合工程化和生产环境

缺点：

1. 抽象层更重
2. 图建模成本高
3. 如果每一步都用 LLM 决策，复杂度仍然会爆炸

### 模式 E：Group Chat / Swarm / Blackboard

核心思想：多个 agent 在共享上下文或共享消息空间中协作，由轮转器、selector 或 orchestrator 选下一个发言者。

代表：

1. AutoGen `RoundRobinGroupChat`
2. AutoGen `SelectorGroupChat`
3. Semantic Kernel `Group Chat`
4. Magentic-One 的 generalist team

适用场景：

1. 开放式问题求解
2. 头脑风暴
3. 多视角分析

优点：

1. 灵活
2. 适合开放任务
3. 容易快速试原型

缺点：

1. token 成本高
2. 共享上下文污染严重
3. 很难做严格 SLA 和确定性控制

### 模式 F：Event-Driven Runtime / Actor Model

核心思想：底层不是“提示词拼装器”，而是有状态 runtime。agent、工具、事件、消息、检查点、恢复、审批，都在统一 runtime 中流转。

代表：

1. LangGraph Pregel runtime
2. AutoGen Core / AgentChat runtime
3. Google ADK Runtime
4. Semantic Kernel runtime

这是当前真正偏“前沿工程化”的方向。很多人以为前沿在 prompt，其实真正决定系统是否能长期演化的，往往是 runtime。

## 3. 当前前沿系统真正重视什么

### 3.1 OpenAI Agents SDK：少而稳的原语

OpenAI 现在的路线很清楚：不要堆太多花哨概念，而是把最关键的原语压缩到少数几个：

1. Agent
2. Tools
3. Handoffs
4. Guardrails
5. Tracing

它强调两个世界并存：

1. LLM 决策编排
2. 代码确定性编排

这个思想非常重要。因为真正好的系统不是“全靠模型自己决定”，而是让模型在该智能的地方智能，在该确定的地方确定。

### 3.2 Claude Code：上下文隔离 + 子代理 + 工具协议化

Claude Code 给我们的启发非常强，尤其适合做工程类多 agent：

1. subagents 有独立上下文窗口，避免主上下文被污染
2. 每个 subagent 可以配置不同工具权限
3. hooks 可以在关键生命周期插入治理逻辑
4. MCP 把“接工具”从项目私有适配提升为通用协议层

这说明一个高扩展平台不应只关心“角色之间怎么说话”，还要关心：

1. 角色能看到什么
2. 角色能做什么
3. 角色做完后如何被审计和拦截

### 3.3 LangGraph：把 agent 当作长期运行的有状态图

LangGraph 的价值不只是在“多 agent”，而是在：

1. checkpoint
2. thread
3. interrupt / human-in-the-loop
4. 并行 superstep
5. 长期状态和跨线程记忆

如果我们后面要做教育域或供应链域，多回合长期任务是大概率需求，所以“状态是头等公民”必须提前进入架构。

### 3.4 AutoGen / Magentic-One：开放任务中的动态协作

Magentic-One 的价值在于它证明了一件事：开放任务下，多 agent 的核心不是“大家一起聊”，而是要有一个持续做计划、跟踪进度、出错后重规划的 orchestrator。

而且 Microsoft 明确强调了它的一个重要优点：模块化设计允许团队添加或删除 agent，而无需重新调 prompt 或训练系统。这一点和我们的目标高度一致。

### 3.5 Google ADK / CrewAI / Semantic Kernel：确定性工作流重新回归中心

这些框架都在强化同一件事：

1. 顺序
2. 并行
3. 循环
4. 状态
5. 恢复
6. runtime

也就是说，行业正在从“让 agent 自由发挥”回到“用软件工程把 agent 组织起来”。

### 3.6 MCP：工具生态的协议层正在成为基础设施

MCP 的意义非常大。它不仅仅是“多接几个工具”，而是在尝试把工具接入抽象成标准 host-client-server 架构。

这对我们后续平台设计的意义是：

1. 工具层要协议化，不要把外部系统耦死在 agent 内部
2. agent 能力描述要与工具注册机制解耦
3. 以后接教育系统、知识库、供应链数据库、审计系统时，可以统一走 adapter / MCP bridge 层

## 4. 从这些系统抽出来的统一结论

截至 2026-04-10，我认为当前“多数系统的共识”已经很明显：

1. 多智能体不等于很多聊天机器人，而是任务拆分、上下文隔离、权限隔离和状态流转。
2. 真正可落地的系统，都会把“LLM 决策”和“代码控制流”混合使用。
3. 真正可扩展的系统，都会把 agent、tool、memory、workflow、guardrail、trace 拆成独立层。
4. 真正能进生产的系统，都会有 checkpoint、resume、approval、observability、evaluation。
5. 前沿方向不是单纯增加 agent 数量，而是增强 runtime、协议标准化和长期演化能力。

## 5. 我们项目应该采用什么路线

我建议我们的平台路线是：

## 路线：Graph Runtime + Typed State + Agent Registry + Tool Protocol + Domain Packs

这是一个“混合式多智能体平台”：

1. 底层是确定性 runtime 和状态图
2. 图中的节点可以是 agent、tool、router、reviewer、human gate
3. agent 内部保留一定的自主规划能力
4. 跨域能力通过 domain pack 扩展，不改核心 runtime

### 5.1 核心分层

建议平台最少拆成下面几层：

1. Runtime 层
   负责工作流执行、并行、暂停、恢复、超时、重试、checkpoint。

2. State 层
   统一定义 thread state、task state、artifact state、review state、memory state。

3. Agent Registry 层
   每个 agent 只暴露清晰的元数据：名称、职责、输入输出 schema、可用工具、权限、可订阅事件。

4. Workflow / Orchestration 层
   定义 router、planner、parallel fan-out、critic loop、approval gate 等可复用编排模式。

5. Tool Adapter 层
   把本地工具、HTTP API、数据库、MCP server、检索系统统一抽象成能力接口。

6. Memory 层
   区分短期会话记忆、任务级记忆、跨任务长期记忆、领域知识记忆。

7. Guardrail / Governance 层
   处理权限、风险动作审批、输入输出校验、敏感数据策略、审计日志。

8. Observability / Evals 层
   处理 tracing、运行指标、轨迹回放、基准样例、回归评测。

9. Domain Pack 层
   教育域、软件供应链域、医疗域等都在这层扩展，不污染核心内核。

### 5.2 我建议暂时不要做的事

1. 不要先做一个全能总 agent
2. 不要先做复杂群聊式 swarm
3. 不要把工具调用、状态结构和角色 prompt 写死在一起
4. 不要一开始就深度绑定某一家框架的高层抽象

## 6. 面向领域落地的推荐模式

### 教育领域

更适合：

1. Planner -> Tutor -> Exercise Generator -> Reviewer -> Human Teacher Gate
2. 重点要有 learner profile、课程目标、错误知识点跟踪、评测记录
3. 很多节点需要强结构化输出，不应只输出自然语言

### 软件供应链领域

更适合：

1. Intake / Triage -> SBOM / Dependency Analyzer -> Vulnerability Analyst -> Policy Reviewer -> Fix Planner -> Human Approval
2. 重点要有证据链、规则引擎、风险分级、审计日志
3. 这类领域对可追溯性和审批要求很高，必须优先做 runtime、state、policy

## 7. 我们的第一阶段实施建议

为了后面能反复迭代，我建议按下面顺序推进：

1. 先做平台内核，不做具体领域逻辑
2. 先做 typed state 和 runtime contracts
3. 先做 agent registry 和 role schema
4. 先做 3 个最基础编排模式：
   1. router / handoff
   2. sequential planner-executor-reviewer
   3. parallel fan-out + merge
5. 先做本地工具适配接口，再接 MCP
6. 先做 tracing / checkpoint / resume，再做更花哨的协作
7. 最后再接教育域或供应链域 domain pack

## 8. 这轮学习后，我给出的项目判断

如果我们的目标是“长期可拓展的行业多智能体平台”，那最重要的不是先选哪个框架，而是先固定下面这几个设计原则：

1. agent 是能力单元，不是系统边界
2. workflow 才是系统骨架
3. state 才是长期演化的基础设施
4. tool protocol 决定集成能力上限
5. evals 和 tracing 决定系统能否持续优化
6. domain pack 决定我们如何把同一内核复用到教育、供应链等领域

## 9. 推荐我们下一步直接落地的内容

下一步最值得做的不是代码细节，而是先把平台骨架约定清楚。我建议我们紧接着产出三份内容：

1. `platform-architecture.md`
   定义分层、模块边界、运行时生命周期。

2. `agent-role-schema.md`
   定义一个 agent role 的标准描述格式。

3. `orchestration-patterns.md`
   固化 router、sequential loop、parallel merge 三种基础模式。

这样后面无论接教育域还是供应链域，我们都不会推倒重来。

## 参考资料

以下是本轮学习优先使用的官方资料与一手资料：

1. OpenAI Agents SDK
   https://platform.openai.com/docs/guides/agents-sdk/
2. OpenAI Agents SDK - Agent orchestration
   https://openai.github.io/openai-agents-python/multi_agent/
3. OpenAI Agents SDK - Tracing
   https://openai.github.io/openai-agents-python/tracing/
4. OpenAI Agents SDK - Guardrails
   https://openai.github.io/openai-agents-python/guardrails/
5. Anthropic Claude Code - Subagents
   https://docs.anthropic.com/en/docs/claude-code/sub-agents
6. Anthropic Claude Code - Hooks
   https://docs.anthropic.com/en/docs/claude-code/hooks
7. Anthropic Claude Code - MCP
   https://docs.anthropic.com/en/docs/claude-code/mcp
8. Anthropic - How we built our multi-agent research system
   https://www.anthropic.com/engineering/built-multi-agent-research-system
9. Anthropic - Claude Code product page
   https://www.anthropic.com/product/claude-code
10. LangChain Docs - Multi-agent
   https://docs.langchain.com/oss/python/langchain/multi-agent/index
11. LangGraph.js Reference
   https://langchain-ai.github.io/langgraphjs/reference/modules/langgraph.html
12. LangGraph Human-in-the-loop
   https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/review-tool-calls/
13. AutoGen AgentChat
   https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html
14. AutoGen Teams
   https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html
15. AutoGen Magentic-One
   https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html
16. Microsoft Research - Magentic-One technical report
   https://www.microsoft.com/en-us/research/publication/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/
17. CrewAI Introduction
   https://docs.crewai.com/en/introduction
18. CrewAI Flows
   https://docs.crewai.com/en/concepts/flows
19. Google ADK Overview
   https://google.github.io/adk-docs/get-started/about/
20. Google ADK Workflow Agents
   https://google.github.io/adk-docs/agents/workflow-agents/
21. Google ADK Multi-agent systems
   https://google.github.io/adk-docs/agents/multi-agents/
22. Semantic Kernel Agent Orchestration
   https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/
23. Model Context Protocol - Introduction
   https://modelcontextprotocol.io/schema/v1
24. Model Context Protocol - Specification
   https://modelcontextprotocol.io/specification/2025-06-18
