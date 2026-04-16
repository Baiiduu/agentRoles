# Case Coordinator Design

更新时间：2026-04-12

这份文档单独定义 `Case coordinator`，不揉进总设计文档。

## 定位

当前 coordinator 是：

`advisor, not controller`

也就是：
1. 可以给出下一步建议
2. 不能替用户自动执行 handoff
3. 不能替代 workflow
4. 不能替代单 agent session

## 输出

当前 recommendation 统一输出：
1. `recommended_mode`
2. `recommended_agent_id`
3. `recommended_workflow_id`
4. `reason_summary`
5. `supporting_signals`

## 输入

coordinator 当前只读取 case 级投影：
1. case stage
2. artifact types
3. session feed summaries
4. handoff count

## 规则

当前先使用规则化建议，不直接做 LLM 协调层。

初版规则：
1. 缺 learner profile 时先建议 `learner_profiler`
2. 缺 study plan 时先建议 `curriculum_planner`
3. 处于 practice 阶段且缺 review summary 时建议正式 workflow
4. 最近 session feed 出现补救信号时建议人工 review
5. 默认建议 `tutor_coach`

## 代码结构

后端：
```text
src/domain_packs/education/orchestration/
  coordinator_models.py
  case_coordinator_service.py

src/interfaces/web_console/
  case_workspace_service.py
```

前端：
```text
frontend/education-workspace/src/
  components/CaseCoordinatorCard.tsx
  types/caseCoordinator.ts
```

## 当前实现状态

已完成：
1. `CaseCoordinatorService` 已实现
2. recommendation 已并入 `GET /api/cases/{case_id}`
3. `CaseCoordinatorCard` 已加入 `Case Workspace`
4. 推荐 agent 可直接进入 `Agent Playground`

暂未完成：
1. workflow recommendation 的直接执行入口
2. human review checkpoint 页面
3. 更复杂的 case projection
4. coordinator explanation trace
