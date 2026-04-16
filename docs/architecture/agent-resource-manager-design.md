# Agent Resource Manager Design

更新时间：2026-04-12

这份文档单独定义 `MCP / Skill / Workspace Manager`，不揉进总设计文档。

## 1. 目标

把资源管理拆成两个动作：

1. `注册`
   用户先把可用的 MCP server 和 Skill 注册进统一管理器
2. `分发`
   再把这些资源分发给具体 agent

同时，为每个 agent 提供项目内工作目录，方便后续文件系统操作。

## 2. 边界

当前版本不改 `core`。

资源管理层落在：

1. `domain_packs/education/resources`
2. `interfaces/web_console/agent_resource_manager_service.py`
3. React `Resource Manager` 页面

当前版本先解决：

1. 注册资源
2. 分发资源
3. 可视化查看是否分发成功
4. 创建和维护 agent 工作目录

当前版本暂不直接解决：

1. MCP 真正执行
2. Skill 真正执行
3. 自动化 agent tool negotiation

## 3. 数据对象

### 3.1 RegisteredMCPServer

字段：

1. `server_ref`
2. `name`
3. `description`
4. `tool_refs`
5. `enabled`
6. `notes`

### 3.2 RegisteredSkill

字段：

1. `skill_name`
2. `name`
3. `description`
4. `trigger_kinds`
5. `enabled`
6. `notes`

### 3.3 AgentWorkspaceRegistration

字段：

1. `agent_id`
2. `relative_path`
3. `enabled`
4. `notes`

## 4. 分发策略

分发仍然复用 `agent_capabilities.json`，不再新造一套 agent 绑定模型。

具体做法：

1. MCP 分发写入 `mcp_bindings`
2. Skill 分发写入 `skill_bindings`
3. Workspace 写入 capability `metadata.workspace`

这样后续 `Agent Capability` 和 `Agent Playground` 都可以看到相同的结果。

## 5. 页面结构

`Resource Manager` 页面分三块：

1. `ResourceManagerNavigator`
   查看每个 agent 当前分发状态
2. `ResourceRegistryPanel`
   注册 MCP server 和 Skill
3. `AgentResourceDistributionPanel`
   给当前选中的 agent 分发资源并维护工作目录

## 6. 工作目录

当前默认工作目录放在：

`runtime_data/education/agent_workspaces/{agent_id}`

要求：

1. 路径必须在项目目录内
2. 保存时自动创建目录
3. 前端可见绝对路径和目录是否存在

## 7. 当前版本结论

当前已经具备：

1. MCP 注册
2. Skill 注册
3. agent 资源分发
4. agent 工作目录创建
5. 前端可视化查看分发情况
6. `Agent Playground` session runtime 注入已分发资源

## 8. Runtime Injection

当前版本已经把资源分发结果注入到 `Agent Playground` 的 session runtime：

1. runtime descriptor 会合并 `config + capability + resource manager`
2. session `agent_binding.metadata` 中会带上 `runtime_resource_context`
3. session `selected_input` 中也会附带 `runtime_resource_context`
4. agent prompt 会收到本次可用的 MCP、Skill、workspace 信息
5. session 返回会显式输出 `resource_events`

这意味着：

1. 已分发资源不再只是配置页数据
2. 用户可以在 `Agent Playground` 直接看到本次生效的资源
3. 后续要继续推进时，可以在这个基础上再接 MCP / Skill 的真实执行

下一步如果继续往执行链推进，应该优先做：

1. 让 agent 根据 `skill execution mode` 区分 advisory / human_confirmed / auto
2. 为已注册 MCP server 接真实调用适配层
