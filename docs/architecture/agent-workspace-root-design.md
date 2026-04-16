# Agent Workspace Root Design

更新时间：2026-04-13

这份文档单独定义教育域中的“总工作目录”能力。

## 1. 目标

在 `Resource Manager` 中增加一个用户可选的总工作目录：

1. 用户先选择一个总工作目录
2. 在未确认创建之前，只保存配置，不创建真实文件
3. 用户点击创建后，才在该根目录下为每个 agent 创建工作目录
4. 每个子目录名称直接使用 agent 的名字，方便后续做 MCP 文件系统测试

## 2. 行为约束

当前版本分成两个动作：

1. `Save Root Only`
   只保存总工作目录配置
2. `Create Agent Workspaces`
   真正创建根目录和每个 agent 子目录

这意味着：

1. 未选择根目录时，不会自动创建任何新目录
2. 仅保存根目录时，不会自动创建任何新目录
3. 只有明确点击创建后，才会落盘

## 3. 命名规则

在创建模式下，agent 子目录命名为各自的 agent 名称。

例如：

1. `Learner Profiler`
2. `Curriculum Planner`
3. `Exercise Designer`
4. `Reviewer Grader`
5. `Tutor Coach`

如果名称包含文件系统非法字符，则仅做最小安全替换。

## 4. 落点

后端：

1. `domain_packs/education/resources`
2. `interfaces/web_console/agent_resource_manager_service.py`

前端：

1. `WorkspaceRootPanel`
2. `AgentResourceManagerPage`

## 5. 当前结论

现在总工作目录已经成为资源管理层的一部分：

1. 可以单独保存
2. 可以单独创建
3. 创建后会同步回每个 agent 的 workspace 配置
4. `Agent Playground` 后续会继续读这些 workspace 信息
