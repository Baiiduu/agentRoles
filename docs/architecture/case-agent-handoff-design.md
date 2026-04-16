# Case Agent Handoff Design

更新时间：2026-04-12

这份文档单独定义 `Case 内的 agent handoff`，不揉进总设计文档。

## 目标

当前 handoff 先采用人工控制，不做自动流转。

产品目标：
1. 在 `Case Workspace` 中显式选择下一个 agent
2. 记录 handoff 的理由和来源
3. 把 handoff 作为 case 级语义保存
4. 由人工确认后再进入 `Agent Playground`

## 边界

handoff 当前不进入：
1. `RuntimeService`
2. `core/state`
3. workflow compiler

handoff 当前落在：
1. `domain_packs/education/orchestration`
2. `interfaces/web_console`
3. React `Case Workspace`

## 数据对象

后端模型：
1. `CaseHandoffRequest`
2. `CaseHandoffRecord`
3. `CaseSessionFeedItem`

前端 DTO：
1. `CaseHandoffRecordDto`
2. `CaseHandoffResponseDto`

## 数据流

```text
Case Workspace
-> operator selects next agent
-> operator writes handoff reason
-> POST /api/cases/{case_id}/handoffs
-> case handoff record is stored
-> frontend navigates to Agent Playground with case_id + agent_id
```

## 代码结构

后端：
```text
src/domain_packs/education/orchestration/
  handoff_models.py
  handoff_service.py

src/interfaces/web_console/
  case_workspace_service.py
```

前端：
```text
frontend/education-workspace/src/
  components/HandoffPanel.tsx
  types/caseHandoff.ts
```

## 当前实现状态

已完成：
1. `CaseHandoffService` 已实现
2. `CaseWorkspaceFacade.create_handoff()` 已实现
3. `POST /api/cases/{case_id}/handoffs` 已接入
4. `HandoffPanel` 已加入 `Case Workspace`
5. handoff 创建后会跳转到对应 agent 的 `Agent Playground`

暂未完成：
1. handoff 审批流
2. handoff 撤回
3. handoff resolved session 自动回写
4. handoff 持久化存储
## Current Practical Refinement

Manual handoff remains the control model, but the operator should not make handoff decisions blind.

The current refinement adds capability-aware handoff support:

1. show target agent capability summary inside `Case Workspace`
2. expose approval and handoff modes before handoff is created
3. block obvious invalid targets when an agent capability is disabled or handoff mode is `blocked`

This improves usability without turning handoff into automatic orchestration.
