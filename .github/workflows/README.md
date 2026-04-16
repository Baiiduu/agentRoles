# Workflow Notes

这个目录存放 GitHub Actions workflow。

当前工作流：

1. `ci.yml`
   面向 PR 和 `main` 的稳定质量门，包含：
   - `Pre-commit`
   - `Backend Smoke`
   - `Frontend Build`
2. `extended-validation.yml`
   手动触发的扩展校验，目前用于跑全量后端测试。

维护建议：

1. 只有稳定、可长期通过的检查，才放进 `ci.yml` 并设为 required。
2. 仍在修复中的检查，先放到扩展校验或非阻断流程。
3. 当全量后端测试稳定后，再把它升级为默认 CI 或 required status check。
4. Python 相关 workflow 默认先执行 `pip install -e .` 或 `pip install -e ".[dev]"`，保持本地和 CI 的入口一致。
