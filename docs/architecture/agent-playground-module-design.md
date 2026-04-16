# Agent Playground Module Design

更新时间：2026-04-12

这份文档定义教育工作台的第一个模块：

`Agent Playground`

它是整个后续产品改造的第一步，因为它直接解决当前最明显的问题：

1. 不能单独控制每个教育 agent
2. 不能和某个 agent 单独对话
3. 不能在产品交互里直观看到 agent 的职责、工具和产物

本文档重点回答：

1. 这个模块在整体系统中的位置
2. 为什么它需要整体后端配合
3. 页面结构和交互
4. 数据流
5. 模块拆分
6. 对当前代码的接入方式

## 1. 模块目标

Agent Playground 的目标不是做一个通用聊天框。

它的目标是：

`把每个教育 agent 变成一个可独立操控、可独立观察、可独立沉淀产物的专业工作单元。`

这个模块需要让用户能够：

1. 选择一个教育 agent
2. 理解该 agent 的职责边界
3. 向该 agent 发送消息或任务
4. 绑定一个 learner case 或使用临时上下文
5. 查看 agent 的输出 artifact
6. 查看 agent 在本次交互中使用了哪些工具和上下文
7. 选择是否把结果写回 learner case

## 2. 它在整体系统里的位置

Agent Playground 是“教育工作台层”的第一个独立模块。

它位于：

1. `web UI`
2. `web_console interface`
3. `education domain orchestration`
4. `core services`

之间的中间位置。

它不应直接跨过中间层去调用：

1. `RuntimeService`
2. `LLM adapter`
3. `ToolInvoker`
4. `MemoryProvider`

正确的调用路径应是：

```text
UI
-> web_console handler
-> web_console service façade
-> education.agent_session_service
-> education agent implementation
-> llm / tools / memory
-> result artifact
-> optional case writeback
-> presenter / DTO
-> UI
```

## 3. 为什么这里需要后端

这个问题非常关键。

## 3.1 当前项目已经有后端，只是还比较薄

当前项目并不是纯前端。

目前已经有一个轻量 Python 后端：

1. [server.py](/E:/大三下/need%20to%20learn/agentsRoles/src/interfaces/web_console/server.py:1)
2. [service.py](/E:/大三下/need%20to%20learn/agentsRoles/src/interfaces/web_console/service.py:1)

所以 Agent Playground 不是“为了它新增一个后端”，而是：

`在已有后端基础上，增加一个新的整体应用模块。`

当前这个后端层现在已经支持两种运行方式：

1. 一体化启动
2. 前后端分离启动

因此 Agent Playground 后续默认应按“前后端分离模式”设计，而不是继续依赖后端顺便托管静态页。

## 3.2 为什么不能只靠前端做

如果把 Agent Playground 做成纯前端直接调用各种底层能力，会立刻出现几个问题。

### 问题 1：前端不该持有模型与工具调用能力

前端不应该直接处理：

1. API key
2. provider routing
3. tool invocation
4. memory access

### 问题 2：前端不应理解 domain 与 core 细节

前端不应该自己拼：

1. agent descriptor
2. case context
3. artifact writeback
4. education memory scopes

### 问题 3：后续 case、审批、持久化都需要统一入口

Agent Playground 后面一定会和这些能力打通：

1. learner case
2. artifact repository
3. case timeline
4. approval flow

这些都必须由一个整体后端协调，而不是让浏览器自己组织。

## 3.3 这里的后端负责什么

Agent Playground 需要的后端职责主要有 5 类。

1. `Agent metadata assembly`
   读取并返回每个教育 agent 的职责、tools、memory scopes、capabilities。
2. `Session execution`
   负责执行单 agent session。
3. `Context injection`
   把 case context、临时上下文和 memory scope 组织好，再交给 agent。
4. `Artifact shaping`
   把 agent 输出转换成可展示、可写回的 artifact DTO。
5. `Writeback orchestration`
   当用户选择写回 learner case 时，由后端统一完成。

## 3.4 这里说的“整体后端”意味着什么

这里必须强调：

Agent Playground 使用的后端，不应该是一个“只为某个页面临时服务的小接口拼接层”。

它必须是整体教育工作台的后端组成部分。

也就是说：

1. 它和未来的 Case Workspace 共用 case repository
2. 它和未来的 Workflow Studio 共用 education orchestration 层
3. 它和未来的 Teacher Console 共用 approval / writeback 语义

因此本模块的后端设计必须从第一天就按“整体后端的一部分”来设计。

## 4. 页面结构

## 4.1 页面布局

建议采用三段式布局：

```text
Agent Playground
|- Left Sidebar
|  |- Agent list
|  |- Agent details
|  `- Context controls
|- Main Panel
|  |- Conversation thread
|  |- Input composer
|  `- Artifact preview
`- Right Panel
   |- Tool usage
   |- Memory usage
   `- Writeback actions
```

## 4.2 左侧区域

### Agent List

展示：

1. agent name
2. role
3. short description
4. status

作用：

1. 快速切换 agent
2. 强化“每个 agent 是独立专业角色”的感知

### Agent Detail

展示：

1. capabilities
2. tool refs
3. memory scopes
4. implementation notes
5. recommended input shape

作用：

1. 让用户明确知道这个 agent 能干什么、不能干什么

### Context Controls

提供：

1. `case_id` 选择器
2. 临时上下文 JSON 编辑区
3. 是否启用 case context
4. 是否允许写回 case

## 4.3 中间区域

### Conversation Thread

展示：

1. 用户输入
2. agent 输出
3. 系统事件提示
4. artifact summary

### Input Composer

提供：

1. 文本输入框
2. 发送按钮
3. 可选任务模板按钮

### Artifact Preview

展示：

1. artifact type
2. summary
3. payload preview
4. 是否已写回 case

## 4.4 右侧区域

### Tool Usage

展示：

1. tool_ref
2. 调用时机
3. 输入摘要
4. 输出摘要

### Memory Usage

展示：

1. 使用了哪些 scopes
2. 读了什么摘要
3. 是否写入长期记忆

### Writeback Actions

提供：

1. 写回 learner case
2. 作为某类 artifact 保存
3. 取消写回

## 5. 用户交互流程

## 5.1 Happy Path

1. 用户进入 Agent Playground
2. 页面加载 agent 列表
3. 用户选择 `curriculum_planner`
4. 页面显示该 agent 的职责、tools、memory scopes
5. 用户选择一个 learner case 或输入临时上下文
6. 用户发送消息
7. 页面展示 agent 输出
8. 页面展示 artifact preview
9. 用户选择写回 learner case

## 5.2 无 case 临时使用

1. 用户不绑定 case
2. 只输入临时上下文
3. agent 执行并返回结果
4. 结果只显示，不写回 case

这条路径适合：

1. 调试
2. prompt 和角色理解验证
3. 单点能力试验

## 5.3 带 case 的连续协作

1. 用户绑定一个 learner case
2. 多次与同一个 agent 对话
3. 多次产物可逐步沉淀到 case

这条路径后续会成为：

1. 单 agent 连续工作
2. 与 Case Workspace 联动

## 6. 数据流设计

## 6.1 页面初始化流

```text
GET /api/agent-playground/bootstrap
-> web_console handler
-> service façade
-> education pack metadata + optional case list
-> AgentPlaygroundBootstrapDto
-> UI
```

### 输出建议

1. `agents`
2. `available_cases`
3. `default_agent_id`
4. `supported_artifact_types`

## 6.2 读取单个 agent 详情

```text
GET /api/agents/{agent_id}
-> handler
-> service façade
-> education agent descriptor lookup
-> AgentDescriptorView
-> UI
```

### 输出建议

1. `agent_id`
2. `name`
3. `role`
4. `description`
5. `capabilities`
6. `tool_refs`
7. `memory_scopes`
8. `recommended_context_fields`

## 6.3 发送消息主流程

```text
POST /api/agent-sessions/message
payload:
  agent_id
  case_id
  message
  ephemeral_context
  persist_artifact

-> handler
-> web_console service façade
-> education.agent_session_service
-> load agent implementation
-> build session context
-> invoke agent
-> collect tool/memory usage
-> optional writeback
-> map to AgentSessionResponseDto
-> UI
```

## 6.4 写回 learner case 流程

写回动作建议有两种实现方式：

1. `inline writeback`
   发送消息时同时决定写回
2. `explicit writeback`
   收到结果后再点“写回 case”

第一阶段建议先做：

1. `inline writeback`

原因：

1. 状态更简单
2. DTO 更容易收敛

## 7. 模块拆分

## 7.1 education/orchestration 层

建议新增：

```text
src/domain_packs/education/orchestration/
  agent_session_service.py
  session_models.py
  context_builder.py
```

### `agent_session_service.py`

职责：

1. 接收 session request
2. 解析 case context 与临时上下文
3. 调用目标 agent implementation
4. 收集 tool / memory usage
5. 可选写回 case
6. 返回 domain 级 session result

### `session_models.py`

建议定义：

1. `AgentSessionRequest`
2. `AgentSessionResult`
3. `AgentMessageRecord`
4. `AgentArtifactPreview`
5. `AgentWritebackResult`

### `context_builder.py`

职责：

1. 根据 `case_id` 构建 agent 可消费上下文
2. 合并临时上下文
3. 输出稳定的 execution input

## 7.2 education/cases 层

第一阶段虽然不一定完整落地 case repository，但要预留：

```text
src/domain_packs/education/cases/
  models.py
  repository.py
```

### 第一阶段最小职责

1. 读取 case 列表
2. 读取单个 case 简要摘要
3. 写入一条 artifact 引用

## 7.3 education/ui_contracts 层

建议新增：

```text
src/domain_packs/education/ui_contracts/
  dto.py
  mappers.py
```

### DTO 建议

1. `AgentPlaygroundBootstrapDto`
2. `AgentDescriptorDto`
3. `AgentSessionResponseDto`
4. `AgentArtifactPreviewDto`

### Mapper 职责

1. 把 session result 转成 UI JSON
2. 不让前端直接接触 domain 原始对象

## 7.4 interface/web_console 层

建议新增：

```text
src/interfaces/web_console/handlers/
  agent_playground.py

src/interfaces/web_console/
  presenters.py
  dto.py
```

### handler 职责

1. 处理 HTTP 输入
2. 调用 façade service
3. 返回 JSON

### façade service 职责

1. 组合 education agent session service
2. 组合 case repository
3. 调用 presenter

### presenter 职责

1. 统一 JSON 输出格式
2. 统一错误输出格式

## 7.5 前端模块

建议新增：

```text
web/education-console/pages/
  agent-playground.js

web/education-console/components/
  api.js
  agent-list.js
  conversation-thread.js
  artifact-preview.js
  context-form.js
```

### 第一阶段前端职责

1. 加载 bootstrap 数据
2. 切换 agent
3. 提交消息
4. 展示结果
5. 展示 artifact preview

不需要第一阶段就做：

1. 复杂会话历史持久化
2. 富文本编辑器
3. 多 case 并行工作

## 8. API 设计

## 8.1 第一阶段建议新增接口

1. `GET /api/agent-playground/bootstrap`
2. `GET /api/agents/{agent_id}`
3. `POST /api/agent-sessions/message`

这些接口应由独立后端提供，前端通过配置化 `apiBaseUrl` 调用。

## 8.2 请求与响应建议

### `POST /api/agent-sessions/message`

请求：

```json
{
  "agent_id": "curriculum_planner",
  "case_id": null,
  "message": "请根据这位学生的情况设计两周学习计划",
  "ephemeral_context": {
    "learner_name": "小林",
    "grade_level": "初二",
    "target_subject": "数学",
    "weak_topics": ["一元二次方程", "函数图像"]
  },
  "persist_artifact": false
}
```

响应：

```json
{
  "session": {
    "session_id": "agent_session_xxx",
    "agent_id": "curriculum_planner",
    "status": "responded"
  },
  "agent": {
    "agent_id": "curriculum_planner",
    "name": "Curriculum Planner"
  },
  "messages": [
    {
      "role": "user",
      "content": "请根据这位学生的情况设计两周学习计划"
    },
    {
      "role": "agent",
      "content": "..."
    }
  ],
  "artifact_preview": {
    "artifact_type": "education.study_plan",
    "summary": "...",
    "payload": {}
  },
  "tool_events": [],
  "memory_events": [],
  "writeback_status": {
    "persisted": false,
    "case_id": null
  }
}
```

## 9. 与当前代码的接入策略

## 9.1 当前最值得复用的部分

当前可以直接复用：

1. `EducationDomainPack.get_agent_descriptors()`
2. `EducationDomainPack.get_agent_implementations()`
3. `_build_llm_invoker()`
4. `build_education_function_tool_adapter()`
5. 现有 `InMemoryAgentRegistry`

## 9.2 当前不应直接复用的部分

不建议直接把新能力继续塞进：

1. `EducationConsoleService` 的单个大类
2. `chat_with_project_agent()`
3. workflow run DTO 拼装逻辑

原因：

1. 这些逻辑是当前 demo 控制台的 façade
2. 再继续往里堆会迅速变成新的大泥球

## 9.3 推荐接入方式

建议按下面顺序接入：

1. 新增 education `agent_session_service`
2. 新增 web_console `agent_playground handler`
3. 再让现有 `EducationConsoleService` 作为 façade 去组合它

换句话说：

`先长出独立模块，再由旧 façade 暂时托管入口，而不是先把新逻辑塞进旧 façade。`

## 10. 风险与辩证判断

## 10.1 最容易犯的错误

### 错误 1：为了快，把 Agent Playground 直接做成 assistant chat 的变体

这会导致：

1. agent 专业边界不清楚
2. tool / memory / artifact 结构表达不清楚
3. 后续很难和 case writeback 打通

### 错误 2：把单 agent session 强行复用 workflow run

这会导致：

1. runtime 被过度承担 UI 语义
2. 单 agent 交互变重
3. 核心边界被前端需求拖坏

### 错误 3：先做漂亮 UI，再补后端结构

这会导致：

1. 前端和底层耦合
2. DTO 反复改
3. 后续 Case Workspace 接不顺

## 10.2 最应坚持的方向

这个模块最该坚持的是：

1. 让“agent 是独立专业单元”真正可见
2. 让“单 agent session”成为独立 domain 语义
3. 让“后端是整体应用后端的一部分”而不是页面临时拼装层

## 11. 模块收敛结论

Agent Playground 的正确落地方向是：

1. 前端新增独立页面
2. 后端新增独立 handler + service
3. education 层新增独立 `agent_session_service`
4. case 写回能力先做最小版

并且整个模块必须建立在以下共识上：

`这里不是因为页面需要而临时加一个后端，而是把当前已有的 Python 服务，继续演进成教育工作台的整体应用后端。`

## 12. 当前代码落地状态

当前第一批代码骨架已经开始落地：

1. education 层已新增 `orchestration/agent_session_service.py`
2. education 层已新增 `orchestration/session_models.py`
3. web_console 层已新增 `agent_playground_service.py`
4. API 已新增：
   - `GET /api/agent-playground/bootstrap`
   - `GET /api/agents/{agent_id}`
   - `POST /api/agent-sessions/message`

当前这批代码的定位是：

1. 先打通单 agent session 的后端骨架
2. 先把模块边界立住
3. 暂时还没有完整 case repository 与完整前端页面

也就是说，当前阶段已经进入实现，但仍然处于：

`后端骨架先行，前端页面后续接入`

## 13. 当前已补上的交互能力

在第一批骨架之后，当前模块又补上了最小交互闭环：

1. `case_id` 选择入口
2. `persist_artifact` 写回开关
3. 页面内简单对话历史
4. bootstrap 中的 sample learner cases
5. 对应的 unit tests

当前这些能力的定位是：

1. 让 Agent Playground 更接近真实工作台
2. 但仍然不引入完整 case repository
3. 写回语义先保留为占位状态，而不把实现硬塞进不成熟模块
