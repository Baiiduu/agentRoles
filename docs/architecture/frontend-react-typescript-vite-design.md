# Frontend React TypeScript Vite Design

更新时间：2026-04-12

这份文档单独定义教育工作台前端的技术栈迁移方案。

当前结论保持简单：

1. 前端采用 `React + TypeScript + Vite`
2. 前端与 Python 后端分离
3. 前端通过稳定 API / DTO 与后端交互
4. 前端不直接耦合 `core`

## 1. 迁移目标

前端后续目标是：

1. 从当前原生单页脚本迁移到独立前端工程
2. 更适合承载 `Dashboard`、`Agent Playground`、`Case Workspace`、`Workflow Studio`、`Teacher Console`
3. 保持与现有 Python 后端清晰分离

## 2. 推荐目录

建议新增独立前端工程目录：

```text
frontend/
  education-workspace/
    package.json
    vite.config.ts
    tsconfig.json
    index.html
    src/
      main.tsx
      App.tsx
      pages/
      components/
      services/
      types/
      styles/
```

## 3. 页面结构

前端工程默认承载：

1. `Dashboard`
2. `Agent Playground`
3. `Case Workspace`
4. `Workflow Studio`
5. `Teacher Console`

## 4. 与后端对接方式

前端统一通过 HTTP API 调用后端。

约定：

1. 后端继续由 Python 提供
2. 前端通过环境变量或配置读取 `apiBaseUrl`
3. 页面只消费稳定 DTO

## 5. 前端模块边界

前端内部建议拆成：

1. `pages/`
2. `components/`
3. `services/`
4. `types/`
5. `styles/`

其中：

1. `services/` 负责 API 请求
2. `types/` 负责前端 DTO 类型
3. `pages/` 负责编排页面
4. `components/` 负责复用 UI 组件

## 6. 迁移顺序

建议按下面顺序推进：

1. 先保留当前原生前端可运行
2. 新建 React + TypeScript + Vite 前端工程
3. 先迁移 `Agent Playground`
4. 再迁移 `Dashboard`
5. 后续再迁移其余页面

## 7. 当前约束

这份迁移方案必须继续遵守：

1. 不把前端状态模型塞回 `core`
2. 不让前端直接操作 education domain 内部对象
3. 不让前端直接持有 LLM provider 凭据

## 8. 当前收敛

前端技术栈迁移是独立议题，不并入总设计文档。

后续涉及前端工程化的设计与实现，都优先以本文件为准。

## 9. 当前代码落地状态

当前已经完成：

1. 独立前端工程目录 `frontend/education-workspace/`
2. `React + TypeScript + Vite` 基础骨架
3. `WorkspaceShell`
4. `Agent Playground` 首个迁移页面
5. 其余页面占位入口

后续页面继续按同一逻辑推进：

1. 页面独立
2. DTO 稳定
3. API 统一
4. 组件边界清晰
