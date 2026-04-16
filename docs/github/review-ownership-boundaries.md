# Review Ownership Boundaries

这个文档解释 `CODEOWNERS` 之外的另一半规则：不仅要知道“谁来审”，还要知道“重点审什么”。

## Review Layers

### Platform Reviewers

适用范围：

1. `src/core/`
2. `src/application/`
3. `src/infrastructure/`
4. `src/interfaces/`
5. 运行入口脚本与仓库治理配置

重点关注：

1. 架构边界是否被破坏
2. 抽象层次是否清晰
3. 运行时行为、状态流转、持久化、MCP/LLM 接入是否稳定
4. 是否引入了不必要的耦合

### Frontend Reviewers

适用范围：

1. `frontend/workspace/`
2. 前端相关启动脚本

重点关注：

1. 页面与组件结构是否清晰
2. 状态和接口调用是否合理
3. 交互、可维护性和类型定义是否一致
4. 是否影响现有页面行为

### Domain Reviewers

适用范围：

1. `src/domain_packs/`

重点关注：

1. 领域行为是否符合业务目标
2. agent、workflow、tool 组合是否合理
3. 是否错误侵入 `core` 或破坏通用层
4. domain pack 元数据和实现是否一致

### QA Reviewers

适用范围：

1. `tests/`
2. 高风险改动对应的测试策略

重点关注：

1. 是否补到了正确层级的测试
2. 测试是否真正覆盖风险点，而不是只覆盖 happy path
3. 是否存在脆弱测试或无效断言

### Docs Reviewers

适用范围：

1. `docs/`
2. `.github/`
3. 设计说明与流程文档

重点关注：

1. 文档是否与实现一致
2. 流程是否可执行，而不只是概念描述
3. 新同学是否能据此快速上手

## PR Routing Rules

1. 纯文档或流程调整：至少需要 `docs/platform` 相关 owner 审核。
2. 只改前端页面与样式：需要 `frontend` owner 审核。
3. 改 `src/core` 或跨层架构：必须有 `platform` owner 审核。
4. 改 `domain_packs`：建议 `domain + platform` 双审。
5. 涉及测试策略变化：建议 `qa` 参与。
6. 跨前后端或跨多模块改动：至少保证每个受影响边界都有对应 owner 参与。

## AI And Human Split

AI Review 负责首轮筛查：

1. 低级 bug
2. 边界条件遗漏
3. 重复代码
4. 测试建议

Human Review 负责最终判断：

1. 业务正确性
2. 架构取舍
3. 风险接受
4. 是否允许进入主干

## Directory README Convention

后续新增目录时，建议同层补一个 `README.md`，至少回答这三个问题：

1. 这个目录负责什么
2. 主要入口文件是什么
3. 变更这个目录时 reviewer 应重点看什么

这样目录结构、Review 责任和协作流程会一直保持一致。
