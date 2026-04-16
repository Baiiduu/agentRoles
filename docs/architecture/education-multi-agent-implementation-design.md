# Education Multi-Agent Implementation Design

更新时间：2026-04-12

这份文档是 [education-multi-agent-product-design.md](./education-multi-agent-product-design.md) 的实施设计版。

它不再只停留在产品目标层，而是进一步收敛为三类可执行内容：

1. 页面结构
2. 数据流
3. 模块拆分

本文档的核心目标是：

`在不污染 core 的前提下，把当前教育域测试控制台逐步演进成教育多智能体协作工作台。`

## 1. 实施原则

在进入页面和模块拆分之前，先固定后续实施必须遵守的原则。

## 1.1 继续保护 core

后续所有新增能力，都优先落在下面两层：

1. `src/domain_packs/education/`
2. `src/interfaces/web_console/` 与 `web/education-console/`

不允许通过以下方式“图省事”：

1. 在 `core/runtime/runtime_service.py` 中增加教育专属分支
2. 在 `core/state/models.py` 中直接新增教育专属核心字段
3. 为页面展示方便改写 `core` 的 snapshot 结构

## 1.2 以 application service 隔离 UI 与 domain

前端页面不应直接拼接：

1. runtime 原始 snapshot
2. education 原始模型对象
3. 临时散落的数据结构

建议所有前端消费都通过 `interface service` 输出稳定 DTO。

也就是说：

1. `core`
   输出通用执行事实
2. `education domain pack`
   输出教育域对象与协作语义
3. `web_console service`
   输出页面友好的视图模型

## 1.3 先补交互层，再补更复杂协作层

当前最需要补的是：

1. 单 agent 可控
2. case 级协作对象
3. 协作过程可视化

而不是：

1. 再加更多 agent
2. 再堆更多 workflow
3. 再加更复杂 prompt

## 2. 当前系统现状

当前项目已经具备一个原型控制台：

1. `/api/overview`
2. `/api/workflows/run`
3. `/api/evals/run`
4. `/api/assistant/chat`

当前 UI 主要页面结构集中在 [index.html](/E:/大三下/need%20to%20learn/agentsRoles/web/education-console/index.html:1)，对应服务端组装在 [service.py](/E:/大三下/need%20to%20learn/agentsRoles/src/interfaces/web_console/service.py:1)。

它的优点是：

1. 能快速展示平台加载状态
2. 能运行 workflow 和 eval
3. 能看到基础 artifacts 和 timeline

它的不足是：

1. 没有单 agent 独立入口
2. 没有 learner case 主对象
3. 没有协作工作区概念
4. 没有人工审批与阶段状态的产品表达

## 2.1 当前项目其实已经有后端

虽然当前项目看起来更像“本地静态页面 + Python 启动脚本”，但它并不是纯前端页面。

当前已经存在一个轻量后端：

1. [server.py](/E:/大三下/need%20to%20learn/agentsRoles/src/interfaces/web_console/server.py:1)
   负责 HTTP 路由与静态文件服务
2. [service.py](/E:/大三下/need%20to%20learn/agentsRoles/src/interfaces/web_console/service.py:1)
   负责组装 runtime、education pack、tool、llm、eval 并向前端输出 JSON

换句话说，当前系统已经有：

1. 浏览器前端
2. Python HTTP 服务
3. 平台内核与教育域逻辑

只是现在这个后端还比较“薄”，更像 demo application service，而不是成体系的产品后端。

## 2.2 为什么仍然需要整体上的后端

即使后续仍然是本地单机原型，我们也仍然需要“整体上的后端层”，原因不是为了追求复杂，而是为了保护边界。

后端必须承担下面这些职责：

1. 持有 API keys 与 provider 配置
   前端不应直接接 OpenAI / DeepSeek
2. 组装 `core`、education domain、memory、tool、case repository
3. 把单 agent session、case run、approval 这些交互翻译为后端可执行语义
4. 输出页面友好的 DTO，而不是把底层对象直接暴露给浏览器
5. 未来承接持久化、审批、case 投影、权限和审计

如果没有这层整体后端，前端就会被迫直接承担：

1. 拼 runtime 输入
2. 组织 learner case
3. 理解 artifacts 和 timeline
4. 维护 provider 调用

这会导致 UI 与 domain/core 高度耦合，后续几乎不可维护。

## 2.3 这里的“后端”不是另起一套系统

这里说的后端，不是要推翻你当前项目再新建一个重型服务。

这里更准确的含义是：

`把现有 web_console 的 Python 服务，逐步演进成教育工作台的整体应用后端层。`

也就是说：

1. 继续复用现在的 Python 服务入口
2. 继续复用当前 runtime / llm / tool / eval 装配能力
3. 只是把接口、DTO、service、handler、domain orchestration 继续拆清楚

所以这不是“额外加一个后端”，而是把当前已经存在的后端层做成正确的整体后端。

## 2.4 当前已收敛的后端分离方式

为了让后续模块开发更清楚，当前项目已经可以按下面两种方式运行：

1. `run_web_console.py`
   兼容旧模式，一体化启动前端静态页与后端 API
2. `run_backend.py`
   单独启动后端 API
3. `run_frontend.py`
   单独启动前端静态页

这意味着当前项目已经从“页面和 API 混在一个启动入口里”演进到了：

1. 可继续兼容旧方式
2. 也支持前后端分离部署

这一步很重要，因为后续 `Agent Playground`、`Case Workspace`、`Teacher Console` 都应该建立在“整体应用后端 + 独立前端”的模式上。

## 2.5 当前前端工程设计已独立拆文档

前端技术栈迁移现在不再揉进总实施设计。

已经独立收敛为：

1. [frontend-react-typescript-vite-design.md](/E:/大三下/need%20to%20learn/agentsRoles/frontend-react-typescript-vite-design.md:1)

这样后续：

1. 整体实施设计
2. 模块设计
3. 前端工程设计

可以分别维护，避免互相缠绕。

所以本轮实施设计的本质，不是替换现有控制台，而是把它从：

`单页测试面板`

扩展为：

`多页面教育协作工作台`

## 3. 页面结构设计

## 3.1 页面总览

建议将当前前端演进为以下 5 个一级页面。

```text
Education Workspace
|- Dashboard
|- Agent Playground
|- Case Workspace
|- Workflow Studio
`- Teacher Console
```

建议保留当前“测试控制台”的部分能力，但将其收敛到：

1. Dashboard
2. Workflow Studio

## 3.2 Dashboard

目标：

1. 作为项目总入口
2. 展示平台与教育域当前状态
3. 提供后续页面跳转入口

### 结构

建议模块：

1. 顶部状态区
   - LLM 配置状态
   - 域包加载状态
   - 当前可用 workflows / agents / tools / evals 数量
2. 快捷入口区
   - 打开 Agent Playground
   - 打开某个 Learner Case
   - 启动某条 workflow
3. 最近活动区
   - 最近的 runs
   - 最近的 artifacts
   - 最近更新的 learner cases

### 价值

它让系统从“只有开发者知道下一步点哪里”，变成“产品入口清晰”。

## 3.3 Agent Playground

目标：

1. 让每个教育 agent 都能单独工作
2. 让用户能够明确感知 agent 的职责边界和差异

### 结构

建议分成左右布局：

1. 左侧：agent 列表与上下文配置
   - agent 选择器
   - agent 描述
   - capabilities
   - tools
   - memory scopes
   - case 绑定选择器
   - 临时上下文输入区
2. 右侧：对话与结果区
   - 对话消息流
   - 本次输出 artifact 卡片
   - tool usage 记录
   - memory usage 记录
   - 可选“写入 learner case”动作

### 页面状态

建议至少有这些状态：

1. `idle`
2. `sending`
3. `responded`
4. `failed`
5. `persisted_to_case`

### 关键交互

1. 选 agent
2. 选是否绑定某个 case
3. 输入问题或任务
4. 接收 agent 输出
5. 选择是否沉淀为 artifact

### 为什么它重要

这是解决“不能控制教育域每个 agent、不能和他们单独对话”的第一优先级页面。

## 3.4 Case Workspace

目标：

1. 围绕单个 learner case 展示全过程协作
2. 成为教育域的主工作空间

### 页面结构

建议拆成四个分区：

1. `Case Overview`
   - learner identity
   - goal
   - current stage
   - mastery summary
   - active plan
2. `Artifacts`
   - learner profile
   - study plan
   - exercise sets
   - review summaries
   - remediation guidance
3. `Collaboration Timeline`
   - runs
   - node transitions
   - branch decisions
   - human approvals
4. `Quick Actions`
   - 与某个 agent 继续工作
   - 启动某条 workflow
   - 审核当前建议

### 页面子视图建议

建议 Case Workspace 内部再分 4 个 tab：

1. `Summary`
2. `Artifacts`
3. `Timeline`
4. `Actions`

### 为什么它重要

没有这个页面，单 agent 对话和 workflow 协作还是两套割裂系统。

## 3.5 Workflow Studio

目标：

1. 保留当前控制台的 workflow 调试能力
2. 升级为真正的多 agent 协作编排观察器

### 页面结构

建议模块：

1. workflow 选择区
2. target case 绑定区
3. 输入上下文编辑区
4. 执行拓扑图区
5. 运行结果区
6. 分支与回修区

### 新增能力

相比当前工作流运行区，需要增强：

1. 节点图展示
2. 当前执行节点高亮
3. 并行节点组展示
4. 条件分支解释
5. interrupt / approval 节点处理入口

### 为什么它重要

这页直接承担“体现多智能体协作过程”的核心任务。

## 3.6 Teacher Console

目标：

1. 从“开发测试台”向“教师工作台”迈一步

### 页面结构

建议模块：

1. learner list
2. learner case summary
3. pending approvals
4. active interventions
5. publishable recommendations

### 第一阶段可收敛

Teacher Console 不需要一开始就做复杂班级管理。

第一版只需要：

1. 审核学习计划
2. 审核补救建议
3. 查看最近一次练习结果

## 3.7 页面演进顺序

建议按下面顺序落地：

1. Dashboard
2. Agent Playground
3. Case Workspace
4. Workflow Studio 升级
5. Teacher Console

## 4. 数据流设计

## 4.1 数据流总览

当前系统后续建议形成三条主数据流。

```text
A. Overview Flow
UI -> WebConsoleService -> Education pack + Runtime metadata -> DTO -> UI

B. Agent Session Flow
UI -> Agent Session API -> Education Agent Session Service -> Agent implementation
   -> LLM / Tools / Memory -> Artifact -> optional Case writeback -> DTO -> UI

C. Case Run Flow
UI -> Case Run API -> Education Case Orchestrator -> RuntimeService.start_run
   -> Workflow execution -> Artifacts / Events / Timeline -> Case projection -> DTO -> UI
```

## 4.2 Overview Flow

### 用途

1. 首页加载
2. 展示 agent / workflow / tool / eval 列表
3. 展示最近运行状态

### 建议 API

1. `GET /api/overview`
2. `GET /api/dashboard`

### 说明

可以先保留 `overview`，再新增更偏页面化的 `dashboard` DTO。

## 4.3 Agent Session Flow

这是新系统里最重要的一条新增数据流。

### 输入

1. `agent_id`
2. `case_id | null`
3. `message`
4. `ephemeral_context`
5. `persist_artifact`

### 处理链

1. 前端提交 agent session request
2. interface service 调用 education agent session service
3. session service 加载：
   - agent descriptor
   - implementation
   - optional learner case context
   - optional memory scope context
4. 调用该 agent 的实现
5. 收集：
   - output text
   - structured artifact
   - tool usage
   - llm usage
6. 若选择写回 case，则写入 case repository 或 memory scope
7. 返回页面 DTO

### 输出

建议统一返回：

1. `session`
2. `agent`
3. `messages`
4. `artifact_preview`
5. `tool_events`
6. `memory_events`
7. `writeback_status`

### 边界

这条流不要求进入 `RuntimeService.start_run()`。

它可以是 education domain 自己的 `single-agent session` 语义。

## 4.4 Case Run Flow

这是多 agent 正式协作的主流。

### 输入

1. `workflow_id`
2. `case_id`
3. `global_context overrides`
4. `run_mode`

### 处理链

1. UI 提交 case run request
2. interface service 加载 learner case
3. 将 case 信息映射为 workflow `global_context`
4. 调用 `RuntimeService.start_run()`
5. runtime 执行 workflow
6. 通过 query service 收集：
   - snapshot
   - timeline
   - artifacts
   - interrupts
7. 将结果投影回 learner case
8. 返回页面友好的 case run DTO

### 输出

建议统一返回：

1. `case`
2. `run`
3. `graph_view`
4. `artifacts`
5. `timeline`
6. `branch_explanations`
7. `approval_actions`

## 4.5 Approval Flow

这条流是后续体现人机协同的关键。

### 输入

1. `run_id`
2. `interrupt_id`
3. `teacher_decision`
4. `resolution_payload`

### 处理链

1. UI 读取 pending approvals
2. 教师在 Teacher Console 或 Workflow Studio 审核
3. 提交 approval resolution
4. interface service 调用 `RuntimeService.resume_run()`
5. runtime 继续执行
6. UI 更新 case timeline

### 价值

这条流不需要改 `core` 语义，因为 `core` 已有 interrupt / resume 能力。

## 4.6 Case Projection Flow

为了避免前端每次都自己聚合 artifacts，建议新增 case projection。

### 输入来源

1. agent session writeback
2. workflow artifacts
3. review results
4. intervention outputs

### 处理

education case projector 负责：

1. 更新 current mastery summary
2. 更新 active plan refs
3. 更新 recent artifact refs
4. 更新 current stage

### 输出

生成稳定的 `LearnerCaseView`

### 价值

它能避免把“页面如何理解 case”这件事塞回 runtime。

## 5. 模块拆分设计

## 5.1 总体目录建议

在保持现有结构不大动的前提下，建议新增或增强以下目录：

```text
src/
  domain_packs/
    education/
      agents/
      tools/
      workflows/
      evals/
      cases/
      memory/
      orchestration/
      ui_contracts/
  interfaces/
    web_console/
      service.py
      server.py
      dto.py
      routes.py
      presenters.py
web/
  education-console/
    index.html
    main.js
    styles.css
    pages/
    components/
```

## 5.2 education/cases

建议新增：

```text
src/domain_packs/education/cases/
  __init__.py
  models.py
  repository.py
  projector.py
  serializers.py
```

### 职责

1. `models.py`
   定义 `LearnerCase`、`PracticeSessionSummary`、`InterventionSummary`
2. `repository.py`
   管理 learner case 的读写
3. `projector.py`
   把 artifacts / run results 投影成 case 的最新视图
4. `serializers.py`
   提供 DTO-friendly 序列化

### 注意

这些都是教育域对象，不应进入 `core/state/models.py`。

## 5.3 education/memory

建议新增：

```text
src/domain_packs/education/memory/
  __init__.py
  scopes.py
  helpers.py
```

### 职责

1. `scopes.py`
   统一定义：
   - `domain:education`
   - `learner:{learner_id}`
   - `case:{case_id}`
   - `plan:{case_id}`
   - `session:{thread_id}`
2. `helpers.py`
   提供读取 learner profile、最近练习历史、当前学习计划等 helper

### 价值

避免 memory scope 字符串散落在 agent 实现和 service 里。

## 5.4 education/orchestration

建议新增：

```text
src/domain_packs/education/orchestration/
  __init__.py
  agent_session_service.py
  case_run_service.py
  approval_service.py
  context_builder.py
```

### 职责

1. `agent_session_service.py`
   单 agent 对话执行入口
2. `case_run_service.py`
   基于 case 启动 workflow run
3. `approval_service.py`
   处理审批恢复
4. `context_builder.py`
   把 learner case 投影成 workflow / agent 可消费的上下文

### 价值

这是本轮设计最关键的隔离层。

它把：

1. UI 交互
2. education 语义
3. runtime 调用

隔离开，避免都挤进 `web_console/service.py`。

## 5.5 education/ui_contracts

建议新增：

```text
src/domain_packs/education/ui_contracts/
  __init__.py
  dto.py
  mappers.py
```

### 职责

1. `dto.py`
   定义：
   - `AgentPlaygroundView`
   - `LearnerCaseView`
   - `CaseRunView`
   - `ApprovalQueueView`
2. `mappers.py`
   把 domain object / runtime observation 映射成页面 DTO

### 价值

避免前端直接依赖 runtime 原始 snapshot 形状。

## 5.6 interfaces/web_console

建议从当前单文件 service 继续拆出下面几个模块：

```text
src/interfaces/web_console/
  service.py
  server.py
  dto.py
  presenters.py
  handlers/
    __init__.py
    dashboard.py
    agent_playground.py
    case_workspace.py
    workflow_studio.py
    teacher_console.py
```

### 拆分建议

1. `service.py`
   保持为 façade，负责组合依赖
2. `presenters.py`
   负责把 domain DTO 转成前端 JSON
3. `handlers/*`
   分页面处理请求

### 价值

避免未来所有页面逻辑都继续堆在一个 `EducationConsoleService` 里。

## 5.7 前端模块

当前前端基本是单页脚本，后续建议最少做轻量模块化。

建议结构：

```text
web/education-console/
  index.html
  styles.css
  main.js
  pages/
    dashboard.js
    agent-playground.js
    case-workspace.js
    workflow-studio.js
    teacher-console.js
  components/
    api.js
    state.js
    cards.js
    timeline.js
    graph.js
    forms.js
```

### 说明

这里不要求立刻引入前端框架。

先通过模块化 JS 把页面逻辑拆清楚，已经能显著改善后续可维护性。

## 6. API 设计建议

## 6.1 保留现有 API

现有接口建议保留：

1. `GET /api/overview`
2. `POST /api/workflows/run`
3. `POST /api/evals/run`
4. `POST /api/assistant/chat`

这样现有控制台功能不会被破坏。

## 6.2 新增 API

建议新增以下接口。

### Dashboard

1. `GET /api/dashboard`

### Agent Playground

1. `GET /api/agents`
2. `GET /api/agents/{agent_id}`
3. `POST /api/agent-sessions/message`

### Learner Cases

1. `GET /api/cases`
2. `POST /api/cases`
3. `GET /api/cases/{case_id}`
4. `GET /api/cases/{case_id}/artifacts`
5. `GET /api/cases/{case_id}/timeline`

### Case Runs

1. `POST /api/case-runs/start`
2. `GET /api/case-runs/{run_id}`
3. `POST /api/case-runs/{run_id}/resume`

### Teacher Console

1. `GET /api/approvals/pending`
2. `POST /api/approvals/{interrupt_id}/resolve`

## 6.3 DTO 建议

建议每类页面使用稳定 DTO，而不是直接返回底层模型。

例如：

1. `DashboardDto`
2. `AgentPlaygroundDto`
3. `LearnerCaseDto`
4. `CaseRunDto`
5. `PendingApprovalDto`

## 7. 实施阶段拆分

## 7.1 Phase 1：页面与接口底座

目标：

1. 先把信息架构搭起来
2. 不急着做复杂持久化

实施项：

1. 增加 Dashboard 页面结构
2. 增加 Agent Playground 页面结构
3. 在 `web_console` 中拆 handler / presenter / dto
4. 新增 `agent-sessions/message` API

## 7.2 Phase 2：LearnerCase 主对象

目标：

1. 让单 agent 与 workflow 协作围绕同一 case 展开

实施项：

1. 新增 `education/cases/*`
2. 实现 in-memory case repository
3. 新增 `GET/POST /api/cases*`
4. 增加 Case Workspace 页面

当前最小实现已经开始落地：

1. `Case Workspace` React 页面已建立
2. `GET /api/cases`
3. `GET /api/cases/{case_id}`
4. sample learner cases 已作为统一主对象入口出现

当前这一版的定位是：

1. 先把单 agent 与多 agent 协作围绕 case 串起来
2. 先提供 case overview / artifacts / timeline / quick actions
3. 暂时还未进入完整 case repository 与完整投影持久化

当前又进一步补上：

1. `Case Workspace -> Agent Playground` 带 case 上下文跳转
2. `Agent Playground -> Case Workspace` 的本地 session feed 回流

这意味着当前前端工作台已经具备最小的：

1. case 入口
2. agent 连续工作入口
3. case 内协作回流视图

## 7.3 Phase 3：Workflow Studio 升级

目标：

1. 让协作结构真正被看见

实施项：

1. graph DTO
2. branch explanation DTO
3. interrupt / resume 入口
4. 运行拓扑图和时间线视图

## 7.4 Phase 4：Teacher Console

目标：

1. 引入教师审核与干预能力

实施项：

1. pending approvals API
2. resolve approval API
3. Teacher Console 页面
4. case timeline 中显示人工审核记录

## 8. 辩证判断与风险

## 8.1 这轮设计最值得坚持的地方

这轮设计最值得坚持的，不是页面数量，而是下面这个分层关系：

1. `core`
   继续保持运行时中立
2. `education domain`
   增加 case、memory、orchestration、ui contracts
3. `interface/web_console`
   负责页面聚合和 API 暴露
4. `web UI`
   负责可视化和交互

这个方向能最大限度保住平台高可拓展性。

## 8.2 这轮设计最大的风险

### 风险 1：把 case 做成伪 core 对象

如果后面为了方便，把 `LearnerCase` 强行塞进 `core/state/models.py`，会直接破坏多领域扩展性。

### 风险 2：把 agent session 混进 runtime

单 agent 对话不一定需要 runtime graph 语义。

如果为了复用而把它强塞进 `RuntimeService`，会让 core 被 UI 需求反向塑形。

### 风险 3：让 web_console service 继续膨胀

如果后续所有逻辑都继续堆在 `src/interfaces/web_console/service.py`，那它会很快变成新的“大泥球”。

### 风险 4：前端直接依赖底层快照

如果页面直接使用 runtime 原始快照结构，后续任何底层字段变动都会牵动 UI，造成不必要耦合。

## 8.3 这轮设计的取舍

这份实施设计有一个明确取舍：

1. 不追求一步到位的完整教育产品
2. 先把“单 agent 可控 + case 协作 + workflow 可见”这三件事做实

这是当前最能提升项目质量、又最不破坏平台边界的路径。

## 9. 最终收敛

后续实施时，建议把当前项目理解为两层演进：

1. `平台层`
   继续稳定 `core`
2. `教育工作台层`
   通过 education domain pack 与 interface 层逐步长出真正的协作体验

如果用一句话概括本文件的实施结论，就是：

`新增页面、新增 case、新增单 agent session、新增页面 DTO，但不要把教育域产品需求倒灌进 core。`
