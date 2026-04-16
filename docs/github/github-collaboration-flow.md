# GitHub Collaboration Flow

这个文档定义 `agentsRoles` 仓库的基础协作流程，目标是让 Issue、PR、AI Review、人工 Review 有统一入口。

## Baseline Flow

1. 先创建 Issue，再开始开发。
2. 从 Issue 派生分支，推荐命名：
   - `feat/<issue-id>-short-name`
   - `fix/<issue-id>-short-name`
   - `chore/<issue-id>-short-name`
3. 开发过程中先做本地自检，再创建 `Draft PR`。
4. `Draft PR` 阶段先接入 AI Review，优先发现明显缺陷、边界条件、测试遗漏和风格问题。
5. 作者处理完 AI 的有效反馈后，将 PR 切换为 `Ready for review`。
6. 进入人工 Review，重点关注业务正确性、架构边界、影响范围和风险接受。
7. PR 需要通过当前 required checks：`Pre-commit`、`Backend Smoke`、`Frontend Build`。
8. CI 通过、人工审批完成、评论全部解决后，才能合并。

## Review Responsibilities

### AI Review

适合 AI 优先处理的事项：

1. 明显 bug 和空值/边界问题
2. 重复逻辑、低质量代码和风格不一致
3. 测试遗漏提示
4. 可读性和命名建议

AI Review 不承担最终批准职责，不能代替人工审批。

### Human Review

人工 reviewer 重点关注：

1. 需求是否真的被正确实现
2. 模块边界是否被破坏
3. 设计是否值得接受
4. 风险、兼容性和回滚成本是否可控

## Current Module Scope

当前已经落地：

1. `.github/ISSUE_TEMPLATE/`
2. `.github/pull_request_template.md`

下一步建议：

1. 增加 `CODEOWNERS`
2. 增加 CI workflow
3. 增加 Copilot 或其他 AI review 的仓库级说明
4. 在 GitHub 仓库设置中启用分支保护 / ruleset
