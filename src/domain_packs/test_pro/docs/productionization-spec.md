# Test Pro Single-Agent Productionization Spec

更新时间：2026-04-19

## 背景

当前 `domain_packs/test_pro` 已经有一个可运行的实验型代码 agent：

1. 提供 `test_pro_chat` descriptor 与 implementation
2. 支持基于 LLM 的结构化决策循环
3. 能调用文件、搜索、git、patch、shell 等 operations 工具
4. 已接入 playground，会话与历史记录也能工作

但它现在更像“实验沙盒 agent”，还不是一个生产级代码代理：

1. `metadata.maturity` 仍是 `prototype`
2. 产品定位仍偏“prompt testing / sandbox”
3. 缺少面向代码任务的明确质量标准
4. 缺少针对单 agent 编码能力的专门测试与回归资产
5. 缺少与 `Codex-like coding agent` 对齐的能力分层

## 本阶段目标

本阶段先不做编排，不做多 agent，不做 workflow-first 设计。

唯一主目标是：

`把 test_pro 单 agent 提升为一个更聪明、更通用、更稳定的代码代理，让它在当前平台里尽可能接近 Codex 的单 agent 体验。`

这里的“接近 Codex”在本项目中的含义是：

1. 更强的仓库理解能力
2. 更稳的工具选择能力
3. 更好的代码修改与验证习惯
4. 更清晰的最终汇报能力
5. 更少的无效循环、误用 shell、重复读取和拍脑袋回答

## 非目标

本阶段明确不做：

1. 多 agent 编排
2. 新 workflow 体系作为主要交付物
3. GitHub review 自动化集成到 domain pack
4. 云端沙箱、资源调度、权限系统重做
5. 完整复制 OpenAI Codex 的所有产品能力

## 问题陈述

当前 `test_pro` 距离生产级单 agent 代码代理还有以下差距：

1. descriptor 文案和 metadata 仍然偏实验性质
2. agent loop 已可用，但“代码任务”能力模型还不够明确
3. 缺少专门针对 coding agent 的行为测试
4. 缺少回归评估资产，无法稳定比较改造前后效果
5. 对“什么叫一个好代码代理输出”还没有统一标准

## 目标能力

第一阶段的 `test_pro` 单 agent 应稳定具备：

1. 仓库与目录理解
2. 精准搜索与按需读取
3. 在修改前主动补上下文
4. 优先使用专用工具，而不是过早退化到 shell
5. 修改后给出基础验证建议，必要时执行验证
6. 在最终回答中总结：
   - 做了什么
   - 依据是什么
   - 改了什么
   - 风险和剩余不确定性是什么

## 生产级质量条

在当前项目里，“生产级单 agent”定义为：

1. 有清晰产品定位
2. 行为边界可解释
3. 工具使用可预测
4. 有回归测试与评估支撑
5. 接入现有 playground 时表现稳定

不要求：

1. 对外 SLA
2. 完整安全隔离
3. 全面自动审查或云执行

## 设计假设

当前先采用这些假设：

1. 主要交互入口仍是 `Agent Playground + HTTP Console`
2. 主要任务类型是本地仓库内的代码理解、修改、验证、总结
3. 继续复用现有 operations tool layer
4. 优先增强 `TestProChatImplementation`，而不是平行再造一个新 agent

## 改造方向

### 1. 产品定位收敛

把 `test_pro_chat` 从“实验聊天 agent”收敛为“代码任务 agent”：

1. 更明确的 role
2. 更明确的 system prompt
3. 更明确的输入输出契约
4. 更明确的最终结果结构

### 2. 决策循环增强

重点提升：

1. 仓库探索顺序
2. 工具优先级策略
3. 重复调用抑制
4. shell 使用约束
5. 编辑前上下文补足
6. 编辑后验证意识

### 3. 结果表达增强

一个更像 Codex 的单 agent，不能只是“调用了工具”，还要能给出开发者友好的完成报告：

1. 结论简洁
2. 证据充分
3. 风险明确
4. 不夸大能力

### 4. 验证资产补齐

新增单 agent 级别的：

1. domain pack 测试
2. implementation 行为测试
3. eval cases / suites

## 第一批交付范围

本批只做这几个垂直结果：

1. 更新 `test_pro` 文档与产品定位
2. 收敛 `descriptor` 与 `metadata`
3. 强化 `TestProChatImplementation`
4. 增加单 agent 测试
5. 增加单 agent eval 资产

## 当前不作为主目标的内容

以下内容允许以后做，但本批不作为主线：

1. `workflows/`
2. 编排节点
3. 多 agent handoff
4. 人工审批流

## 成功标准

本阶段完成后，应满足：

1. `test_pro` 文档完整且放在相关目录内
2. `test_pro_chat` 的定位明确变成代码代理
3. 单 agent 的代码理解、修改、验证、总结能力明显增强
4. 新增测试能证明关键行为
5. 新增 eval 能作为后续回归基线
