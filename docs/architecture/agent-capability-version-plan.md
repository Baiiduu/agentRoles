# Agent Capability Version Plan

更新时间：2026-04-12

这份文档单独定义 `Agent Capability` 的版本推进策略。

## V1

目标：
1. capability 可声明
2. capability 可编辑
3. capability 可解析预览
4. capability 不强耦合执行链

交付：
1. capability models
2. capability repository
3. capability service
4. capability resolver
5. capability page
6. capability api

## V1.1

目标：
1. 在 `Agent Playground` 中显示 resolved capability
2. 在 `Case Workspace` 中显示 handoff / approval 相关 capability
3. 让人能在操作前看见 agent 当前能力边界

## V1.2

目标：
1. 将 `tool_refs / memory_scopes / policy_profiles` 通过 capability resolver 注入运行时解析结果
2. capability 正式进入单 agent session 运行链

## V2

目标：
1. MCP bindings 真正接入可执行工具路径
2. skills 进入 human-confirmed execution
3. capability 与 handoff / coordinator / workflow 形成统一能力语义

## 当前建议

当前阶段先把 V1 定义和实现打磨完整，不要直接跳 V2。
