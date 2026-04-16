# Evaluation Scaffold Design

更新时间：2026-04-11

这份文档定义的是 `evaluation scaffold`，也就是平台里的最小评估骨架。
它的目标不是替代 runtime，也不是把领域评分逻辑写进 core，而是提供一层稳定的“运行案例 -> 读取结果 -> 结构化打分 -> 汇总回归”的公共能力。

## 1. 设计目标

当前评估层必须满足这几个要求：

1. 只消费 `Runtime` 协议，不反向侵入 orchestration
2. 复用已有 `state / events / trace` 输出，不创建第二套执行状态
3. 支持 `case -> suite -> regression` 的自然扩展路径
4. 允许不同领域替换 driver 和 scorer，而不修改 runtime
5. 可以作为后续 domain pack 的统一回归入口

## 2. 在平台里的位置

`evaluation scaffold` 属于 `Observability & Evaluation` 层，但它依赖的输入来自更底层：

- `Runtime`
- `ReducedSnapshot`
- `RuntimeEvent`
- 已有的 `checkpoint / tool trace / policy trace`

它不应该直接依赖：

- 具体数据库实现
- 具体 tool transport
- 具体 domain pack 代码

## 3. 当前采用的结构

当前实现拆成三块：

1. `models.py`
   负责定义 `EvaluationCase / EvaluationSuite / EvaluationExecution / EvaluationCaseResult / EvaluationSuiteResult`

2. `runner.py`
   负责驱动 runtime 执行 case，并把输出交给 scorer

3. `scorers.py`
   负责把一次 execution 转成可比对的 metric result

这个拆法的目的是保持边界清晰：

- runner 负责“跑”
- scorer 负责“评”
- runtime 继续只负责“执行”

## 4. 为什么要有 driver

如果 evaluation 只有一个固定 runner，那么它很快就会被复杂流程拖进 runtime 细节里。

所以当前设计引入了 `EvaluationDriver`：

- 默认 driver 负责最简单的 `create_thread -> start_run -> read final state`
- 自定义 driver 可以处理更复杂的流程，例如：
  - `human_gate -> resume`
  - 多轮外部输入
  - 特定 checkpoint 恢复路径

这样复杂评估流程不会污染默认 runner，也不会逼 runtime 增加“只为评估服务”的方法。

## 5. 为什么要有 scorer

不同领域的“好结果”定义不同：

- 教育域可能关心是否产出正确学习计划、是否减少人工介入
- 供应链域可能关心策略拦截、工具错误率、外部写操作数量

所以评估标准不能硬编码在 runner 里。

当前 scaffold 的 scorer 设计原则是：

1. scorer 只读取 execution，不调用 runtime
2. 每个 scorer 产出单条 `EvaluationMetricResult`
3. suite 汇总时只关心 metric pass/fail，不理解领域逻辑

当前内置的基础 scorer：

- `RunStatusScorer`
- `CompletedNodesScorer`
- `EventPresenceScorer`
- `SideEffectCountScorer`
- `MetadataScorer`

## 6. 当前边界

这层当前故意不做下面这些事：

1. 不把评分逻辑写进 runtime
2. 不创建新的 event store
3. 不创建新的 state snapshot
4. 不引入领域专属指标模型
5. 不直接做 dashboard UI

这些约束是为了保证后续扩展时：

- runtime 仍然保持通用
- observability 和 evaluation 可以共用同一份事实数据
- domain pack 只需要加 scorer / driver / dataset

## 7. 当前适合的用途

这版 scaffold 适合做：

1. 核心回归测试
2. workflow 行为验证
3. tool / policy / interrupt 相关回归评估
4. 后续 domain pack 的最小 benchmark baseline

## 8. 下一步自然扩展

在保持边界不变的前提下，后续最自然的增强是：

1. evaluation dataset loader
2. scorer registry
3. suite-level metrics aggregation
4. trace query helpers
5. domain-specific scorer packs

当前这版已经足够支撑我们继续编码，因为它把“评估”正式放到了独立层，而不是临时散落在测试脚本里。
