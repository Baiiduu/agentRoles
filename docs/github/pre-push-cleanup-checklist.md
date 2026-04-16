# Pre-push Cleanup Checklist

这个清单用于在首次推送到 GitHub 前，快速确认哪些内容应该提交，哪些属于本地产物。

## Should Stay Out Of Git

以下内容不建议提交：

1. `.venv/`
2. `.pip-cache/`
3. `frontend/workspace/node_modules/`
4. `frontend/workspace/dist/`
5. `frontend/workspace/*.tsbuildinfo`
6. `__pycache__/`
7. `*.pyc`
8. `*.egg-info/`
9. `.env`
10. `runtime_data/`
11. `agentworkspace/`
12. `*.log`

## Likely Safe To Commit

通常应该保留：

1. `src/`
2. `tests/`
3. `frontend/workspace/src/`
4. `frontend/workspace/package.json`
5. `frontend/workspace/package-lock.json`
6. `.github/`
7. `docs/`
8. `README.md`
9. `pyproject.toml`
10. `.pre-commit-config.yaml`
11. `.gitignore`

## Current Local Artifacts Found In This Workspace

本地扫描已确认当前目录里存在这些不该提交的产物：

1. `.venv/`
2. `src/agentsroles.egg-info/`
3. `frontend/workspace/node_modules/`
4. `frontend/workspace/dist/`
5. `frontend/workspace/*.tsbuildinfo`
6. 多处 `__pycache__/`

## Before First Push

建议在首次提交前确认：

1. `CODEOWNERS` 占位 owner 已替换
2. `.env` 没有被提交
3. 本地产物目录已被 Git 忽略
4. 只提交源码、配置、文档和工作流文件
