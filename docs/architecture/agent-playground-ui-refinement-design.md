# Agent Playground UI Refinement Design

更新时间：2026-04-12

这份文档单独定义 `Agent Playground` 的页面收敛方向。

当前重点不是继续堆功能，而是把页面做得：

1. 更干净
2. 更像产品工作台
3. 更方便后续迁移到 React

## 1. 当前问题

当前页面虽然已经能跑通最小闭环，但还偏“调试面板”。

主要问题：

1. `临时上下文 JSON` 对产品用户不友好
2. 模块边界还不够清楚
3. 页面信息层次还不够明显
4. 不适合作为 React 迁移前的稳定 UI 原型

## 2. 关于“临时上下文 JSON”

它当前存在的意义只是：

1. 方便快速调试 agent 输入
2. 便于本地验证 agent behavior

它不是最终产品交互形态。

后续应逐步收敛成：

1. `基础表单字段`
   - learner id
   - goal
   - current level
   - weak topics
   - preferences
   - recent signals
2. `高级输入`
   - 仅在调试模式下显示 JSON

也就是说：

`JSON 应该退到调试能力，不应该作为主交互。`

## 3. 页面结构收敛

Agent Playground 建议固定为三栏结构：

### 左栏：Agent Navigator

展示：

1. agent 列表
2. 当前选中 agent 的职责简介
3. capabilities
4. tools
5. memory scopes

### 中栏：Session Composer

展示：

1. learner case 选择
2. 结构化输入表单
3. 用户消息输入
4. 发送按钮

### 右栏：Session Result

展示：

1. agent 回复
2. artifact preview
3. tool usage
4. writeback status
5. recent session history

## 4. 视觉层级要求

页面应做到：

1. 一级区块明确
2. 二级信息折叠清楚
3. 调试信息不抢主信息

建议：

1. 把 agent 描述与职责放前
2. 把输入表单作为页面中心
3. 把 tool events、raw payload 放到次级区域
4. 把 JSON 调试输入收进“高级模式”

## 5. 当前到 React 的迁移要求

当前页面收敛必须服务于后续 React 迁移。

这意味着：

1. 页面应按模块拆思路来组织
2. 一个区块未来对应一个 React 组件
3. 数据接口保持稳定 DTO

推荐未来 React 组件映射：

1. `AgentNavigator`
2. `SessionComposer`
3. `SessionResultPanel`
4. `ArtifactPreviewCard`
5. `SessionHistoryList`

## 6. 当前实施结论

下一步前端不应继续围绕“临时 JSON 调试区”扩展。

而应开始收敛为：

1. 结构化输入优先
2. JSON 退居高级调试
3. 三栏布局清晰
4. 模块命名与 React 组件未来保持一致
