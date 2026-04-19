# Test Pro Single-Agent Implementation Plan

更新时间：2026-04-19

## 总体目标

先把 `test_pro` 做成一个更像 Codex 的单 agent 代码代理，不先做编排。

## Phase 1. 定位与契约收敛

1. 更新 `metadata.py` 的 maturity 与 summary
2. 更新 `agents/descriptors.py`，让 `test_pro_chat` 明确成为 coding agent
3. 收敛输入输出契约与 metadata 命名

## Phase 2. 单 Agent 行为增强

1. 审视 `TestProChatImplementation`
2. 强化工具选择与防循环策略
3. 增强代码任务场景下的最终总结
4. 强化编辑前上下文收集与编辑后验证意识

## Phase 3. 回归验证

1. 增加 `test_pro` domain pack 测试
2. 增加 implementation 级测试
3. 增加 eval cases / suite
4. 验证 playground 入口不回退

## 本批包含

1. 单 agent 能力增强
2. 相关文档
3. 测试与 eval

## 本批不包含

1. workflow-first 改造
2. 多 agent orchestration
3. GitHub 审查自动化

## 约束

1. 不污染 `core`
2. 不新造第二套工具协议
3. 保持当前 playground 可用
4. 尽量在现有 `TestProChatImplementation` 上增量改进
