# CI And Pre-commit

这个文档说明 `agentsRoles` 当前采用的自动检查策略，以及为什么这样分层。

## Goals

目标不是把所有检查一口气都塞进门禁，而是先建立稳定、可信、可长期执行的质量门。

当前分成两层：

1. `pre-commit`
   本地快速阻断低价值问题。
2. GitHub Actions CI
   在 PR 和主干上做稳定校验。

## Current Pre-commit Strategy

文件：`.pre-commit-config.yaml`

当前只放“快、稳定、确定性强”的检查：

1. 行尾空格清理
2. 文件末尾换行修复
3. YAML / JSON / TOML 基础格式校验
4. merge conflict 标记检测
5. 行结束符统一
6. 大文件拦截
7. 私钥检测

这样做的原因：

1. 本地提交不应该被慢检查拖垮
2. 当前仓库还没稳定到适合把全量测试塞进 hook
3. `pre-commit` 适合处理机械性问题，不适合承担完整回归责任

## Current CI Strategy

文件：`.github/workflows/ci.yml`

当前 PR / `main` 默认跑三类检查：

1. `Pre-commit`
2. `Backend Smoke`
3. `Frontend Build`

### Pre-commit

保证基础仓库卫生与配置文件质量。

### Backend Smoke

当前跑两部分：

1. `python -m compileall ...`
2. 一组稳定通过的后端 smoke tests

当前纳入 smoke 的测试：

1. `tests.unit.test_agent_registry`
2. `tests.unit.test_memory_services`
3. `tests.unit.test_tool_layer`
4. `tests.unit.test_observability_queries`
5. `tests.unit.test_domain_agent_executor`

### Frontend Build

执行：

1. `npm ci`
2. `npm run build`

## Extended Validation

文件：`.github/workflows/extended-validation.yml`

这个工作流当前只支持手动触发，用来跑全量后端测试：

`python -m unittest discover -s tests -p "test_*.py"`

之所以暂时不放进默认 required CI，是因为我在本地验证时确认，全量测试当前存在现有失败，主要包括：

1. `runtime_data/education/cases.json` 缺失导致的导入失败
2. 多个 education agent/workflow 测试因 `agent system_prompt config is missing` 失败
3. `interfaces.web_console` 导入路径问题
4. eval suite 当前结果与断言不一致

这意味着当前更合理的做法是：

1. 先把稳定检查设为 required
2. 把全量测试作为修复中的扩展校验
3. 待失败项修复后，再升级为默认 CI

## Recommended Local Commands

建议开发时按下面顺序自检：

1. `py -3.13 -m venv .local\venv`
2. `set PRE_COMMIT_HOME=%CD%\.local\pre-commit-cache` 或在 PowerShell 中设置 `$env:PRE_COMMIT_HOME`
3. `.\.local\venv\Scripts\python.exe -m pip install -e ".[dev]"`
4. `.\.local\venv\Scripts\pre-commit.exe run --all-files`
5. `.\.local\venv\Scripts\python.exe -m agentsroles smoke-tests`
5. `cd frontend/workspace && npm run build`

## Recommended Required Checks

在 GitHub ruleset 中，当前建议先勾成 required 的是：

1. `Pre-commit`
2. `Backend Smoke`
3. `Frontend Build`

暂时不要把 `Extended Validation / Backend Full Suite` 设为 required，直到现有失败项修复完成。
