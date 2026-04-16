# GitHub Collaboration Skeleton

这个目录用于承载 `agentsRoles` 的 GitHub 协作流程骨架。

## Current Structure

1. `ISSUE_TEMPLATE/`
   Issue Forms 与模板配置。
2. `pull_request_template.md`
   统一 PR 自检、验证、风险和 AI / Human Review 分工。
3. `CODEOWNERS`
   定义目录级 review owner。
4. `workflows/`
   GitHub Actions 工作流。

## Related Docs

1. `docs/github/github-collaboration-flow.md`
   从 Issue 到 Merge 的基础协作流程。
2. `docs/github/review-ownership-boundaries.md`
   各类 reviewer 的责任边界与 PR 路由规则。
3. `docs/github/github-repository-settings-checklist.md`
   GitHub 网页端需要手动完成的仓库设置清单。
4. `docs/github/ci-and-pre-commit.md`
   CI、pre-commit 与 required checks 建议。

## Maintenance Notes

1. 新增流程文件时，优先在对应目录补 `README.md`。
2. 如果修改模板、owner 或 review 策略，记得同步更新 `docs/` 下的说明文档。
3. `CODEOWNERS` 中的 owner 必须替换为真实 GitHub 团队或用户名后再启用强制规则。
4. 只有长期稳定的检查才应放入 `workflows/ci.yml` 并配置为 required。
