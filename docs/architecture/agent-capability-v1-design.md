# Agent Capability V1 Design

更新时间：2026-04-12

这份文档单独定义 `Agent Capability V1`，先把 capability 本身设计完整，再考虑继续集成到项目执行链。

## 1. 目标

`Agent Capability` 要解决的不是“agent 会不会说”，而是：

1. agent 在运行时到底能做什么
2. agent 能接入哪些外部能力源
3. agent 在什么条件下可以调用这些能力
4. agent 的能力如何被人工看见、审核、调整、版本化

V1 先追求：
1. 能力可声明
2. 能力可查看
3. 能力可编辑
4. 能力可预览解析结果
5. 能力可版本化收敛

V1 暂不追求：
1. 自动 skill 执行
2. 自动 MCP 编排
3. 自动 multi-agent capability negotiation

## 2. 范围

V1 capability 先覆盖 6 类内容：

1. `local tools`
2. `memory scopes`
3. `policy profiles`
4. `MCP bindings`
5. `skill bindings`
6. `approval / handoff policies`

## 3. 分层模型

后续稳定结构定义为：

### 3.1 Identity

回答“这个 agent 是谁”

包含：
1. `agent_id`
2. `name`
3. `role`
4. `implementation_ref`
5. `input_contract`
6. `output_contract`

### 3.2 Config

回答“这个 agent 怎么表达”

包含：
1. `llm_profile_ref`
2. `system_prompt`
3. `instruction_appendix`
4. `response_style`
5. `quality_bar`
6. `handoff_targets`

### 3.3 Capability

回答“这个 agent 真正能做什么”

包含：
1. `tool_refs`
2. `memory_scopes`
3. `policy_profiles`
4. `mcp_bindings`
5. `skill_bindings`
6. `approval_policy`
7. `handoff_policy`

## 4. V1 功能需求

### 4.1 Capability Registry

系统需要有一个独立 capability registry，用来保存 agent 的能力声明。

V1 要求：
1. 每个 agent 有一份 capability 记录
2. capability 独立于 agent implementation
3. capability 可单独读写
4. capability 文件化存储

### 4.2 MCP Binding

V1 中 MCP 先做“声明式绑定”，不立刻做自动执行。

每个 agent 可以配置：
1. 能访问哪些 MCP server
2. 在该 server 下能访问哪些 tool
3. 这些绑定是否启用
4. 使用说明是什么

### 4.3 Skill Binding

V1 中 Skill 也先做“声明式绑定”。

每个 agent 可以配置：
1. 可关联哪些 skill
2. 这些 skill 在什么场景触发
3. 作用域是什么
4. 执行模式是什么
5. 说明是什么

### 4.4 Approval Policy

V1 中每个 agent 需要有最小审批策略。

支持：
1. `none`
2. `human_review`
3. `required`

审批策略应可声明：
1. 哪些场景必须人工确认
2. 哪些目标对象属于高风险
3. 附加说明

### 4.5 Handoff Policy

V1 中 handoff 仍然以人工控制为主。

每个 agent capability 应能声明：
1. handoff mode
2. allowed targets
3. 说明

### 4.6 Resolved Preview

这是 V1 非常重要的能力。

系统必须能让人看到：
1. 最终解析出的 tool refs
2. 最终解析出的 memory scopes
3. 最终解析出的 policy profiles
4. 当前启用的 MCP servers
5. 当前启用的 skills
6. 当前 approval / handoff policy

也就是说：

`Capability 不只是存起来，还必须能被解析和可视化。`

## 5. 数据模型

### 5.1 EducationAgentCapability

字段：
1. `agent_id`
2. `enabled`
3. `tool_refs`
4. `memory_scopes`
5. `policy_profiles`
6. `mcp_bindings`
7. `skill_bindings`
8. `approval_policy`
9. `handoff_policy`
10. `metadata`

### 5.2 AgentMCPBinding

字段：
1. `server_ref`
2. `tool_refs`
3. `enabled`
4. `usage_notes`

### 5.3 AgentSkillBinding

字段：
1. `skill_name`
2. `enabled`
3. `trigger_kinds`
4. `scope`
5. `execution_mode`
6. `usage_notes`

### 5.4 AgentApprovalPolicy

字段：
1. `mode`
2. `required_targets`
3. `notes`

### 5.5 AgentHandoffPolicy

字段：
1. `mode`
2. `allowed_targets`
3. `notes`

## 6. V1 页面设计

`Agent Capability` 页面建议固定成三栏，不和 `Agent Config` 混在一起。

### 左栏：Capability Navigator

功能：
1. 选择 agent
2. 查看启用状态
3. 查看 role
4. 查看 capability 是否已配置

### 中栏：Capability Editor

分区：
1. base capability
2. mcp bindings
3. skill bindings
4. approval policy
5. handoff policy

### 右栏：Resolved Preview

功能：
1. 展示 capability resolver 的结果
2. 帮助人工检查“最终 agent 会拥有什么能力”

## 7. 版本策略

Capability 不能只有“当前状态”，后续必须支持版本概念。

V1 先定义版本策略，不一定全部实现。

### 7.1 配置版本

每份 capability 后续应支持：
1. `version`
2. `updated_at`
3. `updated_by`
4. `change_note`

### 7.2 解析版本

resolved preview 后续应能看出：
1. 本次解析使用了哪个 capability version
2. 本次解析使用了哪个 config version
3. 本次解析基于哪个 agent identity version

## 8. 集成边界

在 capability 完整设计稳住之前，先不要大面积接进执行链。

V1 集成原则：
1. capability 先作为独立配置系统存在
2. 先支持读取、编辑、预览
3. 解析器先输出 preview，不急着全部改运行逻辑

## 9. 集成顺序

### Phase A

先完成 capability 自身：
1. models
2. repository
3. service
4. resolver
5. page
6. api

### Phase B

把 capability preview 接到：
1. `Agent Playground`
2. `Case Workspace`

### Phase C

把 capability 的 `tool_refs / memory_scopes / policy_profiles` 接进运行时解析

### Phase D

再考虑：
1. MCP 真正执行
2. human-confirmed skill entry

## 10. V1 完整度标准

只有满足下面这些条件，才算 capability V1 设计完成，可以继续深入集成：

1. capability 数据模型稳定
2. capability 页面结构稳定
3. preview 解析逻辑稳定
4. MCP/Skill 的声明方式稳定
5. approval / handoff policy 表达稳定
6. 版本策略已经定义清楚

## 11. 当前结论

我们现在的正确顺序不是“继续往 agent 里塞能力”，而是：

1. 先把 capability 做成独立、稳定、可演进的一层
2. 再把它迭代成一个真正的版本
3. 最后再把这个版本接回项目运行链

也就是说：

`先做 Capability 产品，再做 Capability 集成。`
## 12. Current V1 Refinement

The current V1 implementation is now refined in two practical directions:

1. `resolved preview` is no longer only a raw field dump
2. `Case Workspace` can surface agent capability summaries for handoff decisions

### 12.1 Resolved Preview Additions

Resolved preview should expose business-readable summaries in addition to structural fields:

1. `operational_summary`
2. `collaboration_summary`
3. `usage_guidance`
4. `attention_points`

These fields help an operator judge whether an agent is ready for live case work, whether human review is expected, and whether handoff is constrained.

### 12.2 Case Visibility

Capability data should not stay isolated inside the configuration page.
For V1 practical use, `Case Workspace` should show a compact capability summary per available agent, especially:

1. enabled or disabled state
2. approval mode
3. handoff mode
4. enabled MCP servers
5. enabled skills
6. attention points

This keeps manual handoff human-controlled, but better informed.
