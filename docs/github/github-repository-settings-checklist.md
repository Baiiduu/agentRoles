# GitHub Repository Settings Checklist

这个文档用于指导 `agentsRoles` 在 GitHub 网页端完成仓库级配置。仓库内文件定义了流程骨架，但真正让这些规则生效，还需要在 GitHub 设置页完成以下步骤。

## Before You Start

先确认这几件事已经准备好：

1. 仓库已经推送到 GitHub。
2. 默认分支已确定，通常是 `main`。
3. `.github/CODEOWNERS` 中的占位 owner 已替换成真实团队或用户名。
4. 相关 owner 对仓库具有写权限。

## Recommended Merge Strategy

路径：

`Settings -> General -> Pull Requests`

建议：

1. 开启 `Allow squash merging`
2. 如无特殊需要，可关闭 `Allow merge commits`
3. 是否开启 `Allow rebase merging` 视团队习惯决定
4. 如果主干历史希望保持整洁，优先使用 `Squash merge`

## Recommended Ruleset For Default Branch

路径：

`Settings -> Rules -> Rulesets`

建议新建一个针对默认分支的 `Branch ruleset`，目标分支填写 `main` 或你的默认分支名。

建议开启这些规则：

1. `Restrict deletions`
2. `Block force pushes`
3. `Require a pull request before merging`
4. `Require approvals`
5. `Require review from code owners`
6. `Dismiss stale pull request approvals when new commits are pushed`
7. `Require conversation resolution before merging`
8. `Require status checks to pass`
9. `Require branches to be up to date before merging`

可选规则：

1. `Require linear history`
2. `Block branch creation` 或限制谁可以绕过规则
3. `Require deployments to succeed before merging`，适合后续接环境部署

## Status Checks Strategy

当 CI workflow 建好以后，在 ruleset 里把关键检查设为 required。

当前建议 required check 先覆盖：

1. `Pre-commit`
2. `Backend Smoke`
3. `Frontend Build`

说明：

1. 这三项已经有对应 workflow，可直接在 ruleset 中设置为 required。
2. `Extended Validation / Backend Full Suite` 目前不要设为 required。
3. 等全量后端测试稳定后，再升级 required checks。

## Code Owners

路径：

1. 仓库文件：`.github/CODEOWNERS`
2. GitHub 规则：`Require review from code owners`

注意：

1. `CODEOWNERS` 文件存在，不代表一定强制生效。
2. 只有在 ruleset 中勾选 `Require review from code owners` 后，才会变成强制门禁。
3. owner 必须是真实存在的团队或用户，并且具有仓库访问权限。

## AI Review

如果你计划使用 GitHub Copilot 做首轮 review，可以在 GitHub 中开启自动 review。

路径：

`Settings -> Code review` 或 Copilot 相关设置页面

建议：

1. 开启 `Automatically request Copilot code review`
2. 把 Copilot review 作为首轮筛查，而不是最终审批
3. 继续保留至少一位人工 reviewer 的强制审批

## Suggested Review Policy

推荐的最小闭环：

1. 所有代码通过 PR 合并
2. 至少 `1` 个 approval
3. 核心目录必须经过 `CODEOWNERS`
4. 所有 conversation 必须解决
5. 所有 required status checks 必须通过
6. AI review 作为前置筛查，人工 review 作为最终裁决

如果后续团队扩大，可以升级为：

1. 核心目录要求 `2` 个 approvals
2. `domain_packs` 变更要求 `domain + platform` 双审
3. 高风险改动要求 `qa` 参与

## Recommended Labels

路径：

`Issues -> Labels`

建议初始化一组基础标签：

1. `type:bug`
2. `type:feature`
3. `type:task`
4. `priority:p0`
5. `priority:p1`
6. `priority:p2`
7. `priority:p3`
8. `area:core`
9. `area:frontend`
10. `area:domain`
11. `area:infra`
12. `area:docs`

## Optional But Useful

如果后续要把治理做完整，可以再逐步加：

1. `Projects` 看板，把 issue 和 PR 关联起来
2. `Discussions`，用于非实施类讨论
3. `Dependabot alerts`
4. `Dependabot security updates`
5. `Code scanning`

## Rollout Order

建议按这个顺序配置，最稳：

1. 上传仓库并确认默认分支
2. 替换 `CODEOWNERS` 占位符
3. 开启 merge strategy
4. 建 ruleset
5. 开 AI review
6. 最后把 `Pre-commit`、`Backend Smoke`、`Frontend Build` 设为 required
