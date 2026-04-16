# Agent Capability Architecture

更新时间：2026-04-12

这份文档单独定义 `Agent Capability` 层，不揉进总设计文档。

## 目标

我们后续希望 agent 不只是一个“对话工具”，而是一个真正可配置、可扩展、可接能力源的 agent。

这里的 `capability` 指的是 agent 在运行时可用的能力绑定，而不只是 prompt。

当前目标：
1. 支持给 agent 绑定 MCP 能力
2. 支持给 agent 绑定 Skill 能力
3. 支持能力级的工具策略、记忆策略、handoff 策略
4. 支持后续替换 agent，而不是把能力写死在某个 agent 实现里

## 设计原则

1. 不污染 `core`
2. 不把 skill / MCP 语义硬塞进 `RuntimeService`
3. 把能力视为 agent 外部配置，而不是 agent 类内部常量
4. 让 agent descriptor 继续保持稳定，能力绑定在 education/application 层完成

## 分层

建议把 agent 相关内容拆成三层：

### 1. Agent Identity

这是 agent 是谁。

对应内容：
1. `agent_id`
2. `name`
3. `role`
4. `implementation_ref`
5. `input_contract`
6. `output_contract`

这层继续放在：
`core AgentDescriptor + education agent descriptors`

### 2. Agent Config

这是 agent 怎么说、怎么表现。

对应内容：
1. `llm_profile_ref`
2. `system_prompt`
3. `instruction_appendix`
4. `response_style`
5. `quality_bar`
6. `handoff_targets`

这层已经开始落地，当前文件是：
`runtime_data/education/agent_configs.json`

### 3. Agent Capability

这是 agent 能做什么、能接什么能力源。

对应内容：
1. 可访问的 MCP servers
2. 可访问的 MCP tools
3. 可声明的 Skills
4. 工具调用策略
5. 记忆读写策略
6. 人工审批策略
7. handoff 策略

这就是本设计文档的重点。

## 为什么单独做 Capability 层

如果把 MCP / Skill 直接塞进 agent 配置，会出现两个问题：

1. prompt 和 capability 混在一起
2. 更换 agent 或更换能力源时边界不清楚

所以后续应该形成：

`Agent Identity`
`Agent Config`
`Agent Capability`

三层结构。

## 当前底层可复用的挂点

当前 `core` 已经提供了足够的基础挂点：

1. `AgentDescriptor.tool_refs`
2. `AgentDescriptor.memory_scopes`
3. `AgentDescriptor.policy_profiles`
4. `ToolDescriptor.transport_kind`
5. `ToolTransportKind.MCP`
6. `MCPToolAdapter`
7. `MCPGateway`

这说明我们不需要改 `core` 模型，只要在 education/application 层增加能力绑定和解析逻辑。

## Capability 结构建议

建议新增一个独立运行时配置层：

```text
runtime_data/education/agent_capabilities.json
```

每个 agent 的 capability 建议包含：

1. `agent_id`
2. `enabled`
3. `tool_refs`
4. `memory_scopes`
5. `policy_profiles`
6. `mcp_servers`
7. `mcp_tool_refs`
8. `skills`
9. `skill_execution_mode`
10. `approval_requirements`
11. `handoff_policy`
12. `metadata`

## MCP 绑定设计

MCP 不应该直接在页面里硬写死，也不应该散落到单个实现类里。

建议能力层只做声明：

1. agent 可以访问哪些 MCP server
2. agent 可以访问这些 server 下哪些 tool
3. 这些 tool 对应哪些场景

### 数据对象建议

#### `AgentMCPBinding`

字段建议：
1. `server_ref`
2. `tool_refs`
3. `enabled`
4. `usage_notes`

### 运行时接入方式

建议通过 `Agent Capability Resolver` 把 capability 里的 MCP tools 合并进 descriptor 的 `tool_refs`，而不是改 agent implementation。

数据流：

```text
Agent Capability Config
-> capability resolver
-> resolved tool_refs
-> agent binding
-> runtime services tool invoker
```

## Skill 绑定设计

Skill 与 MCP 不同，它更像“高层行为脚本 / 专项操作知识”。

当前建议不要把 Skill 当作 prompt 附件，而是把它看作：

`agent 在某些任务下可声明使用的操作能力包`

### Skill 绑定对象建议

#### `AgentSkillBinding`

字段建议：
1. `skill_name`
2. `enabled`
3. `trigger_kinds`
4. `scope`
5. `usage_notes`

### 使用方式建议

初期不要让 agent 自动执行所有 skill。

建议支持三种模式：
1. `advisory`
   agent 可声明“建议切入某 skill”
2. `human_confirmed`
   需要人工确认后进入
3. `auto`
   后续成熟后再考虑

当前阶段建议默认：
`human_confirmed`

## Capability Resolver

建议在 education/application 层新增：

```text
src/domain_packs/education/capabilities/
  capability_models.py
  capability_repository.py
  capability_service.py
  capability_resolver.py
```

职责划分：

### `capability_models.py`

定义：
1. `EducationAgentCapability`
2. `AgentMCPBinding`
3. `AgentSkillBinding`
4. `AgentApprovalPolicy`
5. `AgentHandoffPolicy`

### `capability_repository.py`

负责：
1. 读取 capability config
2. 保存 capability config

### `capability_service.py`

负责：
1. 查询 agent capability
2. 修改 capability
3. 供 UI 使用

### `capability_resolver.py`

负责：
1. 把 capability 合并到 descriptor
2. 产出运行时可用的 `tool_refs / memory_scopes / policy_profiles`
3. 给后续 `Agent Playground / Case Workspace / Workflow Studio` 提供统一解析入口

## UI 设计建议

建议新增独立页面：

`Agent Capability`

不要和 `Agent Config` 混成一个大页面。

### 页面职责

1. 查看 agent 当前 capability
2. 查看绑定的 MCP servers / tools
3. 查看绑定的 skills
4. 配置 approval mode
5. 配置 handoff policy

### 页面模块

1. `Capability Navigator`
2. `MCP Binding Editor`
3. `Skill Binding Editor`
4. `Policy Editor`
5. `Resolved Capability Preview`

## 与当前产品功能的关系

### 对 `Agent Playground`

`Agent Playground` 后续不只是显示 prompt config，还要显示：
1. 当前 agent 可用的 MCP tools
2. 当前 agent 绑定的 skills
3. 当前审批策略

### 对 `Case Workspace`

`Case coordinator` 和 `manual handoff` 后续可以读取 capability 里的：
1. `handoff_policy`
2. `recommended skill route`
3. `approval requirements`

### 对 `Workflow Studio`

workflow 后续可以把 capability 当成“节点执行能力边界”，而不是把所有工具权限写死在 workflow 里。

## 当前建议的演进顺序

### Phase 1

先做 capability 配置层和只读展示：
1. 配置文件
2. repository
3. service
4. UI 页面

### Phase 2

把 capability resolver 接入 `Agent Playground`

### Phase 3

把 MCP tool binding 接入运行时可见行为

### Phase 4

引入 `human_confirmed skill execution`

## 当前结论

后续想让 agent 变成真正的 agent，核心不是继续调 prompt，而是建立：

`Identity + Config + Capability`

其中：
1. `Identity` 决定 agent 是谁
2. `Config` 决定 agent 怎么表达
3. `Capability` 决定 agent 真正能做什么

下一步最合理的是：
1. 实现 `agent capability` 运行时配置
2. 做独立 `Agent Capability` 页面
3. 先接 MCP binding，再考虑 skill execution
