# Agent Config Module Design

更新时间：2026-04-12

这份文档单独定义 `Agent Config` 模块，不揉进总设计文档。

## 目标

`Agent Config` 要解决两个问题：
1. agent 的系统提示、模型档位、风格不能继续写死在实现代码里
2. 后续替换 agent 或调优 agent 时，应该改配置，而不是改核心执行链

## 边界

这个模块不进入：
1. `core`
2. `RuntimeService`
3. workflow compiler

这个模块落在：
1. `domain_packs/education/config`
2. `interfaces/web_console/agent_config_service.py`
3. React `Agent Config` 页面

## 配置字段

当前每个 agent 配置包含：
1. `agent_id`
2. `enabled`
3. `llm_profile_ref`
4. `system_prompt`
5. `instruction_appendix`
6. `response_style`
7. `quality_bar`
8. `handoff_targets`
9. `metadata`

## 存储

当前先使用运行时 JSON 文件：

`runtime_data/education/agent_configs.json`

这样配置是外置的，可编辑的，不再写死在 Python 实现里。

## 数据流

```text
Agent Config Page
-> GET /api/agent-configs
-> select one agent
-> edit prompt/profile/style
-> POST /api/agent-configs/{agent_id}
-> config file updated
-> Agent Playground reads updated config on next request
```

## 执行接入

`AgentPlaygroundFacade` 会先读取配置，再把配置合并进 descriptor metadata。

agent 实现层只读取：
1. `llm_profile_ref`
2. `system_prompt`
3. `instruction_appendix`
4. `response_style`
5. `quality_bar`

## 当前实现状态

已完成：
1. file-based config repository
2. config service
3. config API
4. React 配置页
5. Agent Playground 改为读取配置后的 descriptor
6. agent 执行不再走本地 fallback 输出

待继续：
1. 配置版本管理
2. 多环境配置
3. config validation UI
4. 与真实 agent registry 的替换绑定
