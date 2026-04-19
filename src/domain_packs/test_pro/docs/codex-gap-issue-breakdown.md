# Test Pro Toward And Beyond Codex: Target Architecture And Issue Breakdown

更新时间：2026-04-19

## 目的

当前 `test_pro` 已经完成第一批单 agent 生产化收敛：

1. 产品定位从实验性 chat agent 收敛为单 agent coding assistant
2. 工具选择、防循环、修改前补上下文、修改后补验证建议已经落地
3. 核心单元测试已经覆盖主要行为

下一阶段不再先补零散能力，而是先从架构角度回答一个更关键的问题：

`如果目标不是“接近 Codex”，而是“在本地单 agent 架构上达到更强、更稳、更可演进，甚至超越 Codex”，那么 test_pro 的目标架构应该长什么样？`

这份文档先定义目标架构，再按层面拆出后续 issue，避免把所有问题都继续堆到 `TestProChatImplementation` 里。

## 架构优先原则

这里的“超越 Codex”不是指产品包装或模型能力本身，而是指我们在当前项目里，把单 agent 代码代理的系统结构做得更清晰、更稳、更可控：

1. `状态显式化`
   不让关键状态只藏在 prompt 和聊天历史里，而是把任务状态、工作记忆、验证计划、恢复点做成一等结构。
2. `上下文资源化`
   不把仓库理解建立在临时搜索结果拼接上，而是把 repo map、symbol graph、active context set、memory scope 做成 agent 可消费资源。
3. `动作流水线化`
   不把“读-改-验-汇报”混成一个平面循环，而是明确建模 phase、budget、准入条件、失败恢复路径。
4. `工具协议化`
   不让 agent 主要依赖通用 shell，而是提供更高层、更稳定、更可解释的 code-intelligence、edit、validation 工具。
5. `运行时可恢复`
   不把 checkpoint 和 trace 只留给框架内部，而是让 agent 任务可暂停、恢复、追踪、重放。
6. `agent 与 harness 边界清楚`
   agent 负责策略、取舍、开发者表达；harness 负责资源、执行、安全、观测、恢复。

## 可扩展性约束

要保证项目结构后续还能扩展，我们不仅要知道“做什么”，还要知道“哪些方式不能用”。

### 1. 不把能力继续硬编码进单一 implementation

禁止演化方向：

1. 把 memory、policy、validation、reporting 全部继续堆进 `TestProChatImplementation`
2. 用越来越长的 prompt 代替结构化状态
3. 用更多 if/else heuristics 代替 agent state 和 harness capability

要求：

1. `implementation` 负责任务推进，而不是吞掉所有系统职责
2. 通用能力要优先抽到 harness / policy / tool / runtime 层

### 2. 不让当前单 agent 方案堵死未来多 agent 路径

当前不做 orchestration，但架构上要保留演进空间。

要求：

1. task state 要结构化，可被别的 agent 或 orchestrator 接管
2. memory scope 要明确，避免和具体 agent 实现强耦合
3. tool output 和 validation plan 要可序列化、可移交
4. reporting 结果要能作为 handoff artifact

### 3. 不让 domain pack 污染 core，又不让核心能力永远停留在 domain pack

要求：

1. `test_pro` 私有的策略和 contract 可以先在 domain pack 落地
2. 一旦被证明是通用 coding-agent 能力，就应上提到 `core` 或 `operations`
3. `core` 只接收可复用的抽象，不接收 `test_pro` 特有语义

### 4. 不让工具层只暴露原始操作，不暴露更高层任务原语

要求：

1. 原始文件工具保留
2. 但必须逐步引入 symbol-aware、validation-aware、edit-aware 的高层原语
3. agent 优先依赖稳定原语，而不是自己拼底层动作

### 5. 不让状态只存在于运行时内部，不让恢复只靠用户描述

要求：

1. task state、working summary、validation state、checkpoint reference 都必须外显
2. 恢复路径要可以由系统驱动，不依赖用户重新解释上下文

## 超越 Codex 的目标定义

如果只说“更像 Codex”，容易落回 prompt 模仿。这里把目标重新定义为六个更硬的架构目标：

1. `比 Codex 更显式的任务状态`
   当前任务处于理解、探索、编辑、验证还是收尾阶段，应该是可见状态，而不是隐含在模型输出里。
2. `比 Codex 更强的本地仓库上下文面`
   agent 不只是能搜文件，而是能消费 repo map、symbol 索引、已读上下文集合、变更候选集合。
3. `比 Codex 更可控的编辑安全性`
   每次 mutation 都有 edit-readiness contract、patch precheck、post-change validation plan。
4. `比 Codex 更强的恢复性`
   任务中断后能从 checkpoint + working memory + validation state 继续，而不是靠用户重新描述。
5. `比 Codex 更模块化的 harness`
   prompt、policy、memory、tooling、validation、reporting 彼此解耦，可分别演进。
6. `比 Codex 更适合后续多 agent 扩展`
   虽然当前不做 orchestration，但今天的单 agent 架构不能把将来的多 agent 路堵死。

## 目标架构蓝图

### Layer 0. Interaction Layer

职责：

1. 接收用户任务
2. 维护 thread / run / node 生命周期
3. 把 playground、console、API 请求统一映射成标准输入契约

当前评价：

1. 现有运行时基础已经够用
2. 但对 coding task 的 session 语义还比较薄

### Layer 1. Task Kernel

这是最核心的一层，应该成为单 agent 的“认知内核”。

目标状态：

1. 显式 task goal
2. 显式 acceptance criteria
3. 显式 current phase
4. 显式 working summary
5. 显式 pending questions
6. 显式 validation plan

理想上，LLM 每一步不是从零开始判断，而是在这个 task kernel 上推进状态。

### Layer 2. Context And Memory Plane

目标状态：

1. `session memory`
   保存当前任务已确认事实、用户偏好、已探索文件、未完成验证项。
2. `working memory`
   保存本轮高频更新状态，适合压缩上下文。
3. `repository context cache`
   保存当前任务相关的目录、文件、symbol、diff、候选改动点。
4. `retrieval contract`
   明确何时检索 memory，何时使用最新工具结果，何时做摘要压缩。

如果这一层做不好，agent 就永远只能靠“再搜一遍、再读一遍”工作。

### Layer 3. Repository Intelligence Plane

目标状态：

1. 文件树理解
2. symbol 索引
3. definition / references / import graph
4. changed files / impacted files 推断
5. 针对当前任务的 active context set

这层是“代码代理”和“文件工具聊天机器人”的分水岭。

### Layer 4. Action And Tooling Plane

目标状态：

1. 高层工具优先，低层工具兜底
2. shell 是最后手段，而不是默认动作
3. 工具分成：
   - read/search/navigation
   - edit/refactor
   - git/diff
   - validate/build/test
   - external MCP
4. 工具输出结构应稳定、可摘要、可进入 working memory

### Layer 5. Mutation And Validation Plane

目标状态：

1. 进入编辑前先满足 edit-readiness contract
2. 编辑后自动产出 validation plan
3. 运行可执行的最小验证
4. 验证失败时进入 repair loop
5. 最终输出时带上 validation status 和 residual risks

这层决定 agent 是“会写 patch”，还是“会交付可用改动”。

### Layer 6. Runtime, Recovery, And Observability Plane

目标状态：

1. checkpoint 不只是 runtime 内部快照，也能服务 agent 恢复
2. tool trace 不只是调试日志，也能成为后续阶段的输入
3. memory、trace、checkpoint、final report 之间有统一引用关系
4. 中断任务可恢复
5. 失败任务可重放

### Layer 7. Reporting And Developer Handoff Plane

目标状态：

1. touched files
2. key evidence
3. changes made
4. validation status
5. unresolved risks
6. next recommended action

最终交付不应只是“我做完了”，而应像高质量工程协作 handoff。

## 当前判断

当前 `test_pro` 的强项是：

1. 已经有清晰的单 agent coding contract
2. 已经有基础的 decision loop
3. 已经有本地文件 / 搜索 / patch / shell / git 工具接入
4. 已经开始体现 Codex 风格的工具纪律与验证意识

当前 `test_pro` 离上面的目标架构还有三类主要差距：

1. `agent 内逻辑还偏薄`
   现在更像“受约束的工具决策循环”，还不是“有工作记忆、有任务状态、有阶段意识的代码代理”。
2. `harness 暴露给 agent 的上下文资源还不够强`
   运行时虽然已有 `memory_provider`、checkpoint、policy、tool observability 等能力，但 `test_pro` 还没有真正用起来。
3. `工具层还偏文件级`
   适合基础仓库操作，但距离更高质量代码代理所需的 symbol 级、变更级、验证级工具还差一层。

## 从目标架构反推的分层 Issue 清单

### L1. Agent Session And Memory

#### Issue A1. 让 `test_pro` 真正读写 memory，而不是只声明 memory scope

层级：agent + harness 接缝
优先级：P0

现状：

1. descriptor 里已经声明了 `memory_scopes`
2. 但 `metadata.writes_memory=False`
3. implementation 也没有调用 `memory_provider.retrieve/write/summarize`

缺口：

1. 跨轮对话无法沉淀“当前任务目标、已读文件、已确认事实、未决问题”
2. agent 每轮都更像一次性请求，容易重复搜索、重复读文件、重复总结

建议拆分：

1. 先补 `test_pro` 的 session memory contract
2. 明确哪些内容可以写入 memory：
   - task goal
   - accepted assumptions
   - explored files
   - pending validation items
   - final outcome summary
3. 明确哪些内容只应作为短期工作记忆，不进入长期 memory

建议 issue 标题：

- `test_pro: add session memory read/write contract for coding tasks`

#### Issue A2. 引入工作记忆摘要，而不是只靠 execution_trace 回填上下文

层级：agent 实现
优先级：P0

现状：

1. 当前循环依赖 `execution_trace` 和 `tool_context`
2. trace 适合调试，不适合长任务中的“压缩上下文”

缺口：

1. loop step 一多，LLM 看到的是越来越长的历史 JSON
2. 缺少“当前已知事实摘要”和“下一步待解问题”这类更高密度状态

建议拆分：

1. 增加 `working_summary`
2. 每次工具调用后增量更新：
   - what we know
   - what changed
   - what remains
3. 决策 prompt 优先喂摘要，trace 只保留最近窗口

建议 issue 标题：

- `test_pro: add working-summary state for long coding turns`

#### Issue A3. 为仓库探索建立可复用的局部上下文缓存

层级：harness 能力向 agent 暴露
优先级：P1

现状：

1. agent 会读文件、搜文件、列目录
2. 但没有“已探索仓库局部地图”的缓存对象

缺口：

1. 同一任务中重复扫描目录和重复 repo-wide search 的成本较高
2. 无法把“当前相关文件集合”当作一等上下文资源

建议 issue 标题：

- `harness: expose reusable repository context cache for coding agents`

### L2. Tooling Depth

#### Issue B1. 从文件级工具升级到 symbol 级代码导航工具

层级：harness/tool layer
优先级：P0

现状：

1. 现在主要是 `list/read/search/patch/git/shell`
2. 这足够做基础任务，但对中大型代码库仍然粗糙

缺口：

1. 缺少 definition / references / symbol outline / caller-callee 视角
2. agent 很难稳定做“跨文件但局部精确”的修改

建议拆分：

1. 增加 symbol search
2. 增加 definition lookup
3. 增加 references lookup
4. 增加 file outline / exported API summary

建议 issue 标题：

- `operations: add symbol-aware navigation tools for coding agents`

#### Issue B2. 增加结构化编辑工具，降低纯文本 patch 风险

层级：harness/tool layer
优先级：P0

现状：

1. 当前主要靠 `apply_patch`
2. 适合小改动，但对批量重构、导入调整、函数签名变更不够稳

缺口：

1. 纯文本 patch 对上下文窗口和格式敏感
2. 缺少 edit precheck / postcheck

建议拆分：

1. 增加 patch dry-run / applicability check
2. 增加 structured replace
3. 增加 import-aware edit helpers
4. 增加 changed-region summary

建议 issue 标题：

- `operations: add safer structured editing primitives beyond raw patch`

#### Issue B3. 把验证工具从“通用 shell”升级为“面向开发任务的验证动作”

层级：tool layer + harness abstraction
优先级：P1

现状：

1. 当前验证主要还是建议 `git diff`、`git status`、`shell_run`
2. agent 还不知道怎样稳定挑选最合适的测试或构建命令

缺口：

1. 对 Python/Node/通用仓库缺少统一验证动作抽象
2. shell 太自由，成功率和可解释性都不够稳定

建议拆分：

1. 引入 `validate.targeted_tests`
2. 引入 `validate.changed_files`
3. 引入 `validate.command_profile`

建议 issue 标题：

- `operations: add task-oriented validation tools for coding workflows`

### L3. Decision Loop And Task State

#### Issue C1. 从“单步决策循环”升级到“阶段化任务状态机”

层级：agent 实现
优先级：P0

现状：

1. 当前 loop 的核心是“每一步判断 respond 还是 tool_call”
2. 这已经可用，但还比较平

缺口：

1. 缺少明确阶段：
   - understand
   - explore
   - edit
   - validate
   - report
2. LLM 每一步都重新判断，容易局部最优

建议拆分：

1. 在输出中显式维护 task phase
2. 为不同 phase 设不同工具预算与退出条件
3. 对 edit phase 强制要求最小上下文条件满足后才能进入

建议 issue 标题：

- `test_pro: introduce phased coding-task state machine`

#### Issue C2. 把工具偏好与防循环策略从 agent 私有逻辑上提到可复用 policy

层级：harness/policy layer
优先级：P1

现状：

1. 当前很多好规则写在 `TestProChatImplementation` 内部
2. 例如 shell 降级、重复工具抑制、编辑前先读上下文

缺口：

1. 这些规则未来很可能不只 `test_pro` 一个 agent 需要
2. 规则继续堆在 implementation 里会导致 agent 越来越重

建议拆分：

1. 提炼为 coding-agent policy profile
2. 让 runtime/tool policy 能感知：
   - shell downgrade
   - repeated broad exploration
   - edit prerequisites

建议 issue 标题：

- `core/policy: extract reusable coding-agent tool policies`

#### Issue C3. 为长任务引入预算管理，而不是只靠固定 `max_steps=4`

层级：agent 实现
优先级：P1

现状：

1. 当前固定 `max_steps=4`
2. 简单问题够用，复杂问题很容易被截断

缺口：

1. 没有区分不同任务复杂度
2. 没有读预算、改预算、验证预算

建议 issue 标题：

- `test_pro: add phase-aware step budgets for coding tasks`

### L4. Edit Safety And Verification

#### Issue D1. 补“修改前检查清单”，而不只是偏好先读文件

层级：agent 实现
优先级：P0

现状：

1. 当前已经会在编辑前尽量补上下文
2. 但还没有显式的 edit readiness contract

缺口：

1. 没有强约束说明“在什么条件下才允许 patch”
2. 例如目标文件已读、相关调用点已知、验收标准已知

建议 issue 标题：

- `test_pro: enforce edit-readiness checks before file mutation`

#### Issue D2. 让修改后验证从“建议”升级为“可执行计划”

层级：agent + tool layer
优先级：P0

现状：

1. 当前会补验证建议
2. 但尚未形成结构化验证计划

缺口：

1. agent 不会把验证步骤变成显式的可执行清单
2. 也不会基于改动类型选择验证策略

建议拆分：

1. 先产出 `validation_plan`
2. 再决定：
   - 自动执行
   - 请求用户确认
   - 留作手工验证

建议 issue 标题：

- `test_pro: generate structured validation plans after code changes`

#### Issue D3. 增加失败后恢复路径

层级：agent 实现 + harness checkpoint
优先级：P1

现状：

1. runtime 已有 checkpoint
2. 但 `test_pro` 还没有把“验证失败后的恢复策略”建模进去

缺口：

1. 改动失败后只能在后续提示里靠 LLM 自行兜底
2. 没有“复查 diff -> 定位失败点 -> 小步修复”的标准路径

建议 issue 标题：

- `test_pro: add repair loop for failed validation after edits`

### L5. Harness Resource Exposure

#### Issue E1. 规范 `runtime_resource_context`，让 agent 真正拿到稳定资源目录

层级：harness/runtime layer
优先级：P1

现状：

1. `runtime_resource_context` 已经存在
2. 但现在更像松散透传的 metadata 容器

缺口：

1. agent 能依赖哪些资源、资源结构是否稳定，还不够清晰
2. 例如 workspace、MCP servers、skills、tool groups 缺少统一 schema

建议 issue 标题：

- `core/runtime: formalize runtime resource context for agent implementations`

#### Issue E2. 把 checkpoint / event / tool trace 转成 agent 可消费的恢复资源

层级：harness/runtime layer
优先级：P1

现状：

1. runtime 已有 checkpoint 和 observability
2. 但这些信息主要是给系统层，不是给 agent 自己恢复任务用

缺口：

1. agent 无法优雅接续中断任务
2. 无法基于历史 run 总结“上次停在什么地方”

建议 issue 标题：

- `core/runtime: expose resumable agent-task state from checkpoints and traces`

### L6. Developer UX And Reporting

#### Issue F1. 最终回答补齐“开发者交付格式”

层级：agent 实现
优先级：P1

现状：

1. 当前已经会总结、给验证建议、提示风险
2. 但离更稳定的 developer handoff 还有差距

缺口：

1. 缺少固定的高价值字段：
   - touched files
   - key evidence
   - validation status
   - unresolved risks
2. 不同路径下输出风格仍然可能漂移

建议 issue 标题：

- `test_pro: standardize developer-facing completion report`

## 推荐的下一批实施顺序

如果目标是尽快把 `test_pro` 做得更像 Codex，而不是先铺大而全平台，建议顺序是：

1. `A1` 让 memory 真正接入
2. `A2` 补 working summary
3. `C1` 引入阶段化任务状态机
4. `D1` 补 edit-readiness contract
5. `D2` 补结构化 validation plan
6. `B1` 增加 symbol-aware navigation
7. `B2` 增加更安全的结构化编辑工具
8. `C2` 把通用 coding-agent 策略上提到 harness policy

## 更硬的分层路线图

这一版路线图的目标不是“列出所有想法”，而是把接下来真正要推进的事项按归属和优先级排成执行序列。

### Phase R0. 架构定盘

目标：

1. 把单 agent 目标架构定为项目约束
2. 明确 agent / harness / operations / core 的职责边界
3. 明确哪些能力允许先放在 `test_pro`，哪些必须上提

交付：

1. 当前这份架构文档
2. 后续 issue 分层标准

归属：

1. `agent`: 无
2. `harness`: 无
3. `docs/architecture`: P0

### Phase R1. P0 Agent Kernel

目标：

1. 让 `test_pro` 从“规则增强的 loop”升级为“有状态的 coding task kernel”

P0 issues：

1. `A1` `test_pro: add session memory read/write contract for coding tasks`
   归属：`agent` 主导，`harness` 配合
2. `A2` `test_pro: add working-summary state for long coding turns`
   归属：`agent`
3. `C1` `test_pro: introduce phased coding-task state machine`
   归属：`agent`
4. `D1` `test_pro: enforce edit-readiness checks before file mutation`
   归属：`agent`
5. `D2` `test_pro: generate structured validation plans after code changes`
   归属：`agent` 主导，`tooling` 配合

阶段完成标志：

1. task goal / phase / working summary / validation plan 成为输出中的显式状态
2. patch 前后不再只靠 prompt 约束

### Phase R2. P0 Harness And Tool Depth

目标：

1. 给 agent 提供比当前文件级工具更高质量的上下文和动作原语

P0 issues：

1. `B1` `operations: add symbol-aware navigation tools for coding agents`
   归属：`harness/tooling`
2. `B2` `operations: add safer structured editing primitives beyond raw patch`
   归属：`harness/tooling`

阶段完成标志：

1. agent 能用 symbol 级导航而不只是 grep + read
2. agent 能做更安全的结构化编辑而不只依赖原始 patch

### Phase R3. P1 Reusable Harness Policies

目标：

1. 把已经证明有效的 coding-agent 规则从 `test_pro` 私有逻辑上提

P1 issues：

1. `C2` `core/policy: extract reusable coding-agent tool policies`
   归属：`harness/policy`
2. `E1` `core/runtime: formalize runtime resource context for agent implementations`
   归属：`harness/runtime`
3. `A3` `harness: expose reusable repository context cache for coding agents`
   归属：`harness/runtime`

阶段完成标志：

1. shell downgrade、重复 broad exploration 抑制、edit prerequisites 不再是 `test_pro` 私货
2. repo context cache 和 runtime resource schema 开始稳定

### Phase R4. P1 Recovery And Long-Running Task Quality

目标：

1. 让 agent 能更可靠地处理中长任务、失败任务、恢复任务

P1 issues：

1. `C3` `test_pro: add phase-aware step budgets for coding tasks`
   归属：`agent`
2. `D3` `test_pro: add repair loop for failed validation after edits`
   归属：`agent` 主导，`harness` 配合
3. `E2` `core/runtime: expose resumable agent-task state from checkpoints and traces`
   归属：`harness/runtime`
4. `B3` `operations: add task-oriented validation tools for coding workflows`
   归属：`harness/tooling`

阶段完成标志：

1. 复杂任务不会轻易被固定步数截断
2. 验证失败后存在标准恢复路径
3. run 中断后可恢复

### Phase R5. P1 Developer Delivery Quality

目标：

1. 把最终输出提升为稳定的 developer handoff artifact

P1 issues：

1. `F1` `test_pro: standardize developer-facing completion report`
   归属：`agent`

阶段完成标志：

1. completion report 可稳定提供 touched files、evidence、validation status、risks、next action

## 归属矩阵

为了避免推进时反复争论，先给一个简化归属判断：

### 优先归属 `agent`

满足以下任一条件：

1. 主要是在改任务状态推进方式
2. 主要是在改输出契约、回复结构、阶段控制
3. 主要是在改 edit-readiness 或 validation planning 逻辑

### 优先归属 `harness/runtime`

满足以下任一条件：

1. 主要是在暴露可复用资源给多个 agent
2. 主要是在做 checkpoint、trace、resource schema、memory access contract
3. 主要是在做跨 agent 可共享的恢复能力

### 优先归属 `operations/tooling`

满足以下任一条件：

1. 主要是在增加新的高层工具原语
2. 主要是在让 edit / navigation / validation 更稳定
3. 主要是在把自由 shell 行为替换成结构化工具

## 推荐先推进的最小可行批次

如果我们现在要“准备推进”，我建议先抓一个最小但架构价值最高的批次：

1. `A1` session memory contract
2. `A2` working summary state
3. `C1` phased task state machine
4. `D1` edit-readiness contract

这四项的共同价值是：

1. 它们直接决定 `test_pro` 还是不是“prompt 很重的 loop”
2. 它们能把后续 symbol 工具、validation 工具、恢复能力接进来
3. 它们不会先把我们拖进大规模 tool/platform 重构

## 推进建议

建议接下来按这个顺序走：

1. 先把这份文档作为后续 issue 拆分基线
2. 先开 `Phase R1` 的 P0 issue
3. 逐个落地时，始终检查是否违反上面的可扩展性约束
4. 只有当某项能力已经明显通用时，才从 `test_pro` 上提到 `core` 或 `operations`

## 一个重要判断

下一阶段最应该避免的事情是：

`继续只在 prompt 上加规则，而不把 memory、task state、tool depth、validation contract 这些一等能力补进来。`

如果继续只加 prompt 和局部 heuristics，`test_pro` 会越来越像“规则很多的聊天代理”，而不是“真正有状态、有工具深度、有恢复能力的单 agent 代码代理”。
