# Memory Services Design

更新时间：2026-04-11

这份文档把 `Memory Services` 从平台总架构里单独展开，作为后续继续编码时的直接依据。

## 1. 设计目标

当前 memory 层要解决的是：

1. 给 runtime 提供统一的可注入记忆能力
2. 支持 thread / task / long-term / domain 这类作用域语义
3. 允许后续接入向量库、数据库或外部记忆系统
4. 不把领域对象直接塞进 core state

## 2. 当前边界

当前 memory 层位于：

- `Runtime + Typed State Core` 之上
- `Domain Packs` 之下

它通过 `MemoryProvider` 契约注入 runtime services，但不直接进入 runtime 主链。

也就是说：

1. runtime 不直接实现 memory
2. selector 不直接查询 memory backend
3. executor 如果需要 memory，只能通过 `context.services.memory_provider`

## 3. 当前实现结构

当前实现拆成两部分：

1. `models.py`
   - `MemoryRecord`
   - `MemorySummary`
   - `MemoryScopeKind`

2. `provider.py`
   - `InMemoryMemoryProvider`

同时保留已有 contract：

- `src/core/contracts/memory_provider.py`

## 4. 为什么先做 provider，而不是 memory node

当前没有把 memory 做成新的 workflow node 类型，这是刻意的。

原因是：

1. memory 是横向能力，不是工作流骨架本身
2. 不同 executor 对 memory 的使用方式不同
3. 过早把它做成固定 node，容易把记忆语义绑死

所以当前更稳的方式是：

- 先把 provider 和 scope 语义做对
- 后续由 agent executor、tool executor 或 domain executor 按需消费

## 5. 当前作用域设计

当前 contract 中 `scope` 保持字符串化，不提前硬编码复杂层级结构。

推荐约定：

1. `thread:{thread_id}`
2. `task:{task_key}`
3. `long_term:{tenant_or_user}`
4. `domain:{domain_key}`

之所以这样设计，是为了兼顾：

1. 多领域扩展
2. 多租户扩展
3. 后续替换存储后端

## 6. 当前 reference 实现

`InMemoryMemoryProvider` 当前提供：

1. `write(memory_item) -> memory_id`
2. `retrieve(query, scope, top_k=5) -> list[MemoryResult]`
3. `summarize(scope) -> dict`

并额外提供本地辅助方法：

1. `get_record`
2. `list_records`
3. `build_summary`

这让它既能作为 contract 的参考实现，也能作为测试和本地开发的便利层。

## 7. 当前检索策略

当前 in-memory 版本采用简单 lexical retrieval，而不是提前接向量索引。

原因是：

1. 当前阶段先验证接口与作用域边界
2. 后续换成向量库时不应该改变 contract 形状
3. reference 实现应该简单、稳定、易测试

## 8. 当前设计的关键约束

1. memory 结果必须带 `scope`
2. retrieval 必须 scope-isolated
3. write 不能依赖 runtime 私有状态
4. memory 层不负责调度、不负责审批、不负责评分

## 9. 当前最优设计结论

当前更优的收敛方案是：

1. memory 先做成 provider 层
2. retrieval 和 summary 先做成 reference implementation
3. executor 按需消费 memory provider
4. runtime 不主动内嵌 memory 逻辑

这个设计的好处是，后续接教育域 learner profile、供应链域 SBOM/风险画像时，我们扩展的是：

- scope 规则
- memory payload
- retrieval backend

而不是改 runtime 内核。
