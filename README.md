# AgentsRoles

更新时间：2026-04-11

这是一个面向多领域扩展的多智能体平台原型项目。

当前定位：

1. 适合本地自测与架构验证
2. 适合继续扩展新的 `domain pack`
3. 适合验证教育领域多智能体协作
4. 暂不以生产级部署为目标

## 当前项目状态

目前已经完成的主干能力：

1. `Runtime + Typed State Core`
2. `Agent Registry Layer`
3. `Tool Adapter / MCP-ready Layer`
4. `Memory Services`
5. `Observability & Evaluation`
6. `LLM Adapter / Provider Config Layer`
7. `Education Domain Pack`
8. `Web Console + 教育项目助手`

当前教育域已经具备：

1. 5 个教育 agent
2. 3 条教育 workflow
3. 4 个教育工具
4. 评估用例与评估套件
5. DeepSeek-first 的 LLM 调用策略

## 最该保留的设计文档

如果只看最核心的文档，按这个顺序读即可：

1. [ARCHITECTURE_LANDSCAPE.md](./docs/architecture/ARCHITECTURE_LANDSCAPE.md)
   平台路线与主流多智能体架构背景
2. [platform-architecture.md](./docs/architecture/platform-architecture.md)
   平台总分层与边界
3. [core-runtime-design-spec.md](./docs/architecture/core-runtime-design-spec.md)
   核心内核运行规格
4. [agent-registry-layer-design.md](./docs/architecture/agent-registry-layer-design.md)
   agent 注册、版本与查询模型
5. [memory-services-design.md](./docs/architecture/memory-services-design.md)
   memory 层设计
6. [evaluation-scaffold-design.md](./docs/architecture/evaluation-scaffold-design.md)
   evaluation scaffold 设计
7. [llm-adapter-provider-layer-design.md](./docs/architecture/llm-adapter-provider-layer-design.md)
   OpenAI / DeepSeek 接入层设计
8. [domain-pack-standard-structure.md](./docs/architecture/domain-pack-standard-structure.md)
   领域包标准结构
9. [education-domain-pack-architecture-brief.md](./docs/architecture/education-domain-pack-architecture-brief.md)
   当前教育域原型说明

## 当前推荐入口

### 0. 快速上手

```powershell
cd E:\大三下\need to learn\agentsRoles
py -3.13 -m venv .local\venv
$env:PIP_CACHE_DIR = "$PWD\\.local\\pip-cache"
& .\.local\venv\Scripts\python.exe -m pip install --upgrade pip
& .\.local\venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 1. 安装提交前钩子

当前仓库已经提供 `.pre-commit-config.yaml`，但**默认不会在 `git commit` 时自动运行**。
如果你希望每次提交前自动执行格式和基础检查，请手动安装 hook。

为了避免把 hook 缓存重复下载到用户目录，当前项目建议把本地开发缓存统一放到仓库根目录下的 `.local/` 中。
当前约定：

1. `.local/venv/`
2. `.local/pip-cache/`
3. `.local/pre-commit-cache/`

安装 hook：

```powershell
cd E:\大三下\need to learn\agentsRoles
$env:PRE_COMMIT_HOME = "$PWD\\.local\\pre-commit-cache"
& .\.local\venv\Scripts\pre-commit.exe install
```

安装后，`git commit` 会自动触发当前配置的 `pre-commit` 检查。

如果你想提前把 hook 环境准备好，也可以先执行一次：

```powershell
$env:PRE_COMMIT_HOME = "$PWD\\.local\\pre-commit-cache"
& .\.local\venv\Scripts\pre-commit.exe run --all-files
```

### 2. 配置环境变量

在项目根目录放置 `.env`，参考：

1. [`.env.example`](./.env.example)

当前推荐策略：

1. 教育域 agent 与教育项目助手默认优先使用 `DeepSeek`
2. 若 `DeepSeek` 不可用，再尝试 `OpenAI`

### 3. 启动 Web 控制台

```powershell
cd E:\大三下\need to learn\agentsRoles
& .\.local\venv\Scripts\python.exe -m agentsroles web
```

浏览器打开：

```text
http://127.0.0.1:8765
```

### 4. 其他常用运行命令

```powershell
& .\.local\venv\Scripts\python.exe .\run_dev.py
& .\.local\venv\Scripts\python.exe -m agentsroles dev
& .\.local\venv\Scripts\python.exe -m agentsroles backend
& .\.local\venv\Scripts\python.exe -m agentsroles web
& .\.local\venv\Scripts\python.exe -m agentsroles frontend
& .\.local\venv\Scripts\python.exe -m agentsroles smoke-tests
```

### 5. 推荐自测顺序

1. 先看页面右上角的 LLM 配置状态
2. 先运行 `education.diagnostic_plan`
3. 再运行 `education.practice_review`
4. 再运行 `education.remediation_loop`
5. 最后运行 `education.eval_suite.smoke`

### 6. 提交前检查

```powershell
cd E:\大三下\need to learn\agentsRoles
$env:PRE_COMMIT_HOME = "$PWD\\.local\\pre-commit-cache"
& .\.local\venv\Scripts\pre-commit.exe run --all-files
& .\.local\venv\Scripts\python.exe -m agentsroles smoke-tests
cd .\frontend\workspace
npm run build
```

## 代码结构摘要

```text
src/
  core/
    agents/
    contracts/
    checkpoint/
    evaluation/
    events/
    executors/
    llm/
    memory/
    observability/
    runtime/
    state/
    stores/
    tools/
    workflow/
  domain_packs/
    education/
  interfaces/
    web_console/
web/
  education-console/
tests/
```

## 当前边界原则

后续继续迭代时，默认遵守这些规则：

1. 领域逻辑不能反向污染 `core`
2. agent 不直接依赖 provider SDK，统一走 `llm_invoker`
3. agent 不绕开 tool / memory / evaluation 层
4. workflow 负责编排，agent 负责行为，runtime 负责执行
5. 新领域优先通过新的 `domain pack` 接入

## 换会话后的最短接力方式

如果下一次会话要快速接上，只要先告诉新会话：

1. 工作目录是 `agentsRoles`
2. 先阅读 [README.md](./README.md)
3. 再阅读 [platform-architecture.md](./docs/architecture/platform-architecture.md)
4. 然后根据需要进入 [education-domain-pack-architecture-brief.md](./docs/architecture/education-domain-pack-architecture-brief.md)
