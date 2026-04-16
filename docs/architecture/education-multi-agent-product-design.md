# Education Multi-Agent Product Design

更新时间：2026-04-11

这份文档定义当前教育域项目的下一阶段产品设计目标。

它回答四个问题：

1. 最终想做成什么样的教育领域多智能体协作系统
2. 当前项目距离这个目标还差什么
3. 后续应该如何演进，才能更体现多智能体协作
4. 如何在演进过程中保持 `core` 的高可拓展性，不让教育域反向污染平台内核

本文档是产品设计与架构边界文档，不直接替代：

1. `platform-architecture.md`
2. `core-runtime-design-spec.md`
3. `education-domain-pack-architecture-brief.md`

相反，它建立在这些文档之上，回答“教育域下一步应该怎么做”。

## 1. 设计立场

当前教育域项目不应继续朝“固定三条 workflow 的演示台”演进。

下一阶段更合理的定位是：

`一个面向全过程学习支持的教育多智能体协作工作台`

这个工作台要同时具备三种能力：

1. 单个 agent 可被单独控制、单独调试、单独对话
2. 多个 agent 可围绕同一个学习案例协作
3. 协作过程对教师或操作者是可见、可控、可干预的

这意味着教育域后续重点不再只是“再补几个 agent”，而是把以下能力补齐：

1. agent 独立入口
2. case 级共享上下文
3. artifact 驱动协作
4. 人机协同审批点
5. 多回合长期记忆
6. 协作过程可视化

## 2. 产品目标

## 2.1 总目标

构建一个可展示、可测试、可扩展的教育多智能体协作系统原型，覆盖学习支持的关键闭环：

1. 学情诊断
2. 学习规划
3. 内容与练习生成
4. 作答与评阅
5. 补救与追踪
6. 阶段总结与长期画像更新

## 2.2 产品级目标

这个系统最终应支持：

1. 教师直接与任一教育 agent 单独对话
2. 教师启动一条完整协作流，让多个 agent 围绕同一个 learner case 协作
3. 教师查看每个 agent 的输入、输出、工具调用和决策依据
4. 教师在关键节点插入人工判断，决定是否继续、回修、重规划或切换路径
5. 系统持续维护 learner case 的阶段性与长期状态

## 2.3 架构级目标

后续演进必须继续满足：

1. 教育域仍然是 `domain pack`
2. `core` 继续保持领域中立
3. 新增能力优先通过扩展点进入，不在 `RuntimeService` 中写教育分支
4. 前端增强不反向驱动 `core` 结构畸形演化

## 3. 为什么当前效果不理想

当前系统已经具备平台雏形，但从“产品体验”和“多智能体协作表现”看，存在几个明显问题。

## 3.1 当前更像 workflow demo，不像 agent workspace

目前用户主要通过预设 workflow 运行教育流程。

这会导致：

1. 用户不能单独和某个教育 agent 工作
2. agent 的职责边界只能在代码和文档里看到，不能在产品交互里感知
3. 所有协作都被压扁成一次 run 的最终结果

## 3.2 当前缺少统一的教育案例对象

现在的 workflow 输入主要来自 `thread_state.global_context`。

这足够支撑 demo，但不足以支撑真正的“全过程教育协作”，因为缺少一个稳定的、长期存在的协作对象，例如：

1. learner case
2. course case
3. study plan case

没有 case 概念时：

1. 单 agent 对话难以与 workflow 协作打通
2. 不同 agent 的产物难以围绕同一学习对象沉淀
3. 长期追踪会退化成散落在上下文里的自然语言

## 3.3 当前协作过程的可见性还不够强

虽然 runtime 已有 event、checkpoint、timeline 能力，但产品层对“协作”的表达仍然偏弱。

用户现在难以直观看到：

1. 哪个 agent 为什么被调用
2. 它基于哪些 artifact 做出结论
3. 它和其他 agent 的分工关系是什么
4. 为什么进入了补救分支

## 3.4 当前的人机协同点还不够自然

教育不是全自动流水线。

真实教育场景里，很多动作都需要教师确认，例如：

1. 是否接受学情画像
2. 是否采纳学习计划
3. 是否发布当前练习
4. 是否进入补救路径
5. 是否把建议同步给学生或家长

如果没有这些控制点，系统就更像内部测试器，而不像真实教育协同系统。

## 4. 最终产品能力蓝图

## 4.1 核心对象

下一阶段教育域建议围绕下面几个核心对象组织：

1. `LearnerCase`
   单个学习者的协作案例，作为多 agent 协作的主对象
2. `StudyPlan`
   阶段学习目标、路径、里程碑
3. `PracticeSession`
   某次练习、作答、批改、反馈的闭环记录
4. `InterventionTask`
   针对薄弱点的补救或教学干预任务
5. `TeachingArtifact`
   各 agent 产出的结构化中间物和最终物

这些对象不应成为 `core` 的通用模型字段，而应在教育域通过：

1. `artifact_type`
2. `extensions["education"]`
3. education memory scopes

来承载。

## 4.2 用户侧核心页面

下一阶段建议前端逐步形成四个核心页面。

### A. Agent Playground

目标：

1. 单独测试和使用每个教育 agent
2. 单独给 agent 注入上下文
3. 查看该 agent 的工具使用、输入输出和历史记录

应支持：

1. 选择 agent
2. 输入消息
3. 选择上下文来源
4. 选择是否写回 learner case
5. 展示该 agent 的 artifact 输出

### B. Case Workspace

目标：

1. 围绕一个 learner case 查看整个教育协作过程
2. 把所有 agent 的工作集中到同一个案例空间

应支持：

1. learner case 概览
2. 当前画像、当前计划、当前薄弱点
3. 关键 artifacts 列表
4. 当前 run 列表
5. 时间线与协作图

### C. Workflow Studio

目标：

1. 启动完整协作流
2. 观察 workflow 中各节点如何执行
3. 支持重跑、回修、人工干预和分支查看

应支持：

1. 选择 workflow
2. 指定 target learner case
3. 可视化节点状态
4. 展示分支和 merge
5. 展示当前执行到哪个 agent

### D. Teacher Console

目标：

1. 面向真实教师使用，而不是仅面向开发调试

应支持：

1. 查看班级或单学生概况
2. 审核画像与学习计划
3. 发布练习与查看结果
4. 审核补救建议
5. 输出面向学生或家长的说明

## 4.3 单 agent 能力蓝图

每个教育 agent 都应具备独立运行能力。

这意味着任何 agent 都至少要支持：

1. 单独接收消息和上下文
2. 返回结构化结果
3. 选择是否写入某个 learner case
4. 可查看最近一次执行产物

教育域当前 5 个 agent 可以先按下面方式定位：

1. `learner_profiler`
   输入学习者背景、历史表现、偏好，输出 learner profile artifact
2. `curriculum_planner`
   输入 learner profile 和教学目标，输出 study plan artifact
3. `exercise_designer`
   输入目标和薄弱点，输出 exercise set artifact
4. `reviewer_grader`
   输入作答与 rubric，输出 review artifact
5. `tutor_coach`
   输入 review 或 plan，输出 learner-facing guidance artifact

## 4.4 多 agent 协作能力蓝图

要体现“多智能体协作”，系统必须支持以下协作模式。

### 模式 1：线性接力

例如：

1. `learner_profiler`
2. `curriculum_planner`
3. `tutor_coach`

价值：

1. 适合学情诊断与初始规划

### 模式 2：并行协作

例如：

1. `curriculum_planner` 生成阶段计划
2. `exercise_designer` 检索练习模板
3. `tutor_coach` 准备面向学生的引导语
4. merge 成一个教学执行包

价值：

1. 更能体现角色分工
2. 更符合多 agent 的工程特征

### 模式 3：评审回环

例如：

1. `exercise_designer` 出题
2. `reviewer_grader` 评审作答
3. `learner_profiler` 更新学习状态
4. `curriculum_planner` 调整下一阶段计划

价值：

1. 更贴近真实教育闭环

### 模式 4：分支与补救

例如：

1. `reviewer_grader` 给出 mastery signal
2. condition node 判断是否需要补救
3. 若需要：
   `exercise_designer -> tutor_coach`
4. 若不需要：
   进入进阶路径

价值：

1. 体现多 agent 协作中的条件判断和自适应

### 模式 5：人工审核协作

例如：

1. `curriculum_planner` 给出计划
2. 教师审核
3. 审核通过后才允许 `exercise_designer` 进入发布阶段

价值：

1. 教育产品更真实
2. 体现 runtime 的 interrupt / resume 能力

## 5. 新的教育域产品结构建议

## 5.1 保持 core 不变的前提

以下能力原则上都应通过 education domain pack 和 interface 层实现：

1. agent 单聊入口
2. learner case 组织方式
3. case 级 memory scope
4. 教师控制台与案例工作台
5. agent 协作可视化 UI

不应通过下面方式实现：

1. 在 `RuntimeService` 里写教育专用 case 逻辑
2. 在 `core/state/models.py` 里加入 `learner_id`、`course_id` 等教育专属核心字段
3. 在 `core` 中加入教育专用 workflow 分支判断

## 5.2 建议新增的 education 层模块

建议在 `src/domain_packs/education/` 下继续长出下面这些模块：

```text
src/domain_packs/education/
  cases/
    __init__.py
    models.py
    repository.py
    serializers.py
  memory/
    __init__.py
    scopes.py
    helpers.py
  orchestration/
    __init__.py
    presets.py
    session_builder.py
  ui_contracts/
    __init__.py
    dto.py
```

职责建议：

1. `cases/`
   定义 learner case 的教育域对象模型与序列化方式
2. `memory/`
   统一教育域 memory scopes 和 memory helper
3. `orchestration/`
   定义教育域里的高层协作入口，例如“单 agent 对话”和“case workflow run”
4. `ui_contracts/`
   给前端提供教育域视图 DTO，避免前端直接耦合 runtime 原始快照结构

## 6. 建议的交互模型

## 6.1 单 agent 对话

建议新增一种教育域交互：

`Agent Session`

它表示：

1. 选择一个 agent
2. 绑定一个 case 或临时上下文
3. 与该 agent 连续对话
4. 根据需要把结果沉淀为 artifact

这个能力不要求修改 runtime 核心语义。

实现方式应优先是：

1. education domain executor + education application service
2. 重用已有 llm/tool/memory services
3. 单 agent 对话结果按 artifact 形式可选落入 case

## 6.2 协作案例

建议新增一种教育域主对象：

`LearnerCase`

建议至少包含：

1. case_id
2. learner_identity
3. learning_goal
4. current_stage
5. current_mastery_summary
6. active_plan_refs
7. recent_artifact_refs
8. domain metadata

注意：

1. 这是 education 层对象，不是 core 对象
2. 可以存于 memory backend、文件或未来的持久化存储中
3. 不要求进入 `core` 的通用 typed state 主骨架

## 6.3 协作运行

建议区分两种运行方式：

1. `Agent Session`
   单 agent 工作
2. `Case Run`
   多 agent 围绕 learner case 的正式协作 run

两者都可写入 artifact，但只有 `Case Run` 必须进入完整 workflow timeline。

这可以同时满足：

1. 调试
2. 演示
3. 真实协作

## 7. 如何更体现多智能体协作

如果只是让多个 agent 顺序运行，多智能体价值仍然不强。

真正更能体现协作的，是下面这些设计。

## 7.1 让每个 agent 都有“可见的专业边界”

前端必须让用户能看见：

1. 这个 agent 负责什么
2. 它不负责什么
3. 它能用哪些工具
4. 它读哪些 memory scopes

## 7.2 让 agent 之间通过 artifact 协作，而不是通过模糊文本协作

例如：

1. `education.learner_profile`
2. `education.study_plan`
3. `education.exercise_set`
4. `education.review_summary`
5. `education.remediation_guidance`

前端应能展示这些 artifact 的生成链。

## 7.3 让分支和并行成为一等体验

当前最值得强化的是：

1. parallel fan-out
2. condition branch
3. review loop
4. approval gate

如果页面上能清楚展示这些结构，系统的“多 agent 协作感”会显著增强。

## 7.4 允许“争议”与“重规划”

后续可以逐步加入：

1. planner 给出推进建议
2. reviewer 给出风险判断
3. teacher 选择继续推进还是进入补救

这会比单一路径更能体现多 agent 的价值。

## 8. 保持高可拓展性的硬边界

这是本设计最关键的约束。

## 8.1 不允许的演进方式

后续教育域迭代中，不允许：

1. 为了 learner case 直接修改 `core` 的通用 record 结构
2. 为了单 agent 对话在 `RuntimeService` 中加入教育专用分支
3. 为了教师控制台把前端状态模型硬塞回 `core`
4. 为了展示方便，把 education-specific 字段加进所有通用 snapshot 类型

## 8.2 允许的演进方式

优先通过以下方式扩展：

1. 新增 education-specific artifact types
2. 在 `ThreadState.extensions["education"]` 或 `RunState.extensions["education"]` 中承载教育域扩展信息
3. 新增 education memory scopes
4. 新增 education application service / interface service
5. 新增 education case repository
6. 新增 education UI DTO 与 orchestrator helper

## 8.3 判断是否污染 core 的标准

新增一个能力时，先问三个问题：

1. 这个能力是否只对教育域有意义
2. 这个能力是否能通过 artifact、extensions、memory scope 或 interface 层表达
3. 这个能力是否会迫使别的领域也接受教育域假设

如果答案是：

1. 只对教育域有意义
2. 可以通过 domain pack 扩展点实现
3. 会迫使其他领域接受教育域假设

那么它就不应该进入 `core`。

## 9. 对当前项目的辩证判断

## 9.1 当前项目做对了什么

当前项目的底层方向是对的，尤其是：

1. `runtime + typed state + workflow + registry` 的骨架已经成立
2. 教育域已经作为 `domain pack` 进入，而不是直接写进 `core`
3. LLM、tool、memory、evaluation 已经具备分层
4. 补救循环 workflow 已经开始体现真实教育闭环

这些都是高质量底座，不应轻易推倒。

## 9.2 当前项目不够好的地方

从产品视角看，目前的问题也很明确：

1. 用户对 agent 的控制力度不足
2. 案例级协作对象不明显
3. 协作可视化表达不够强
4. 人工审核点不够自然
5. “多智能体”更多体现在代码结构，而不是产品体验

## 9.3 这不是推倒重来，而是补上上层产品层

当前更合理的路径不是重写 runtime，而是补齐：

1. education case layer
2. single-agent session layer
3. collaboration workspace layer
4. teacher-facing interaction layer

也就是说：

`底层内核大方向继续保留，上层教育产品体验需要重做。`

## 10. 建议的分阶段实施

## Phase 1：让 agent 真正“可控”

目标：

1. 每个教育 agent 都能单独对话
2. 可以选择上下文来源
3. 可以查看输出 artifact

交付：

1. Agent Playground
2. education agent session service
3. 基础 case 选择器

## Phase 2：让协作真正“围绕案例”

目标：

1. 引入 learner case
2. workflow 围绕 case 运行
3. 结果沉淀到 case timeline

交付：

1. LearnerCase 模型
2. Case Workspace
3. case-level artifact index

## Phase 3：让多智能体协作真正“可见”

目标：

1. 展示 agent 分工
2. 展示 artifact 接力
3. 展示分支、补救、回环和审批

交付：

1. workflow visualization
2. artifact lineage view
3. timeline + branch explanation

## Phase 4：让系统更接近真实教育工作流

目标：

1. 引入教师审核
2. 引入更稳定的长期记忆
3. 强化 agent-tool integration

交付：

1. teacher approval flow
2. learner progress memory scopes
3. richer education tools

## 11. MVP 收敛建议

如果下一阶段只能优先做少量高价值工作，我建议优先级如下：

1. `Agent Playground`
   解决“不能单独控制 agent”的核心痛点
2. `LearnerCase`
   解决“全过程协作缺少主对象”的问题
3. `Case Workspace`
   解决“协作不可见”的问题
4. `teacher approval checkpoints`
   解决“真实教育场景缺少人工判断”的问题

不建议当前优先做：

1. 再新增很多教育 agent
2. 为了演示而堆更复杂 prompt
3. 在 `core` 中增加教育专属状态字段
4. 为了短期 UI 便利破坏平台边界

## 12. 结论

下一阶段教育域项目的关键，不是继续把现有 workflow 做得更长，而是把系统从：

`固定流程演示台`

升级成：

`可单聊、可协作、可干预、可追踪的教育多智能体工作台`

而且这个升级必须建立在当前平台骨架之上，通过：

1. education domain pack 扩展
2. interface/application service 扩展
3. artifact / memory / case 模型扩展

来完成，而不是通过污染 `core` 完成。
