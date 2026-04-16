# LLM Adapter / Provider Config Layer Design

更新时间：2026-04-11

这份文档定义平台如何把真实 LLM API 接入 agent 系统，同时保持核心边界清晰。

当前主目标：

1. 接入 `DeepSeek` 与 `OpenAI`
2. 不把 provider 细节写进 `runtime`
3. 不把 API key 暴露给前端
4. 让所有领域包都能复用同一套 LLM 接入层

## 1. 层级位置

推荐调用链：

`Workflow -> AgentImplementation -> LLMInvoker -> LLMAdapter -> Provider API`

其中：

1. `workflow` 只决定协作关系
2. `agent` 只表达业务行为和提示构造
3. `llm_invoker` 负责 profile 解析与路由
4. `adapter` 负责 provider 协议适配
5. `provider api` 才是真实外部模型服务

## 2. 边界规则

### 2.1 `runtime` 不知道 provider 细节

`runtime` 不应直接知道：

1. `base_url`
2. `api_key`
3. OpenAI / DeepSeek 的 HTTP 细节
4. 某家 provider 的返回字段差异

### 2.2 `domain pack` 只依赖统一抽象

领域 agent 只应依赖：

1. `LLMRequest`
2. `LLMResult`
3. `LLMInvoker`
4. `profile_ref`

而不应直接依赖：

1. OpenAI SDK
2. DeepSeek SDK
3. 某家厂商私有的原始返回格式

### 2.3 前端不保存密钥

前端只负责：

1. 展示当前 provider 配置状态
2. 触发 workflow / eval / assistant chat
3. 展示运行结果

前端不负责：

1. 保存 API key
2. 直接请求模型服务
3. 决定 provider 路由策略

## 3. 当前接入策略

当前项目已经采用：

1. `DeepSeek-first`
2. 若 `DeepSeek` 不可用，再尝试 `OpenAI`

该策略目前适用于：

1. 教育域 agent
2. Web 控制台中的教育项目助手

## 4. 核心对象模型

### 4.1 Provider Config

`LLMProviderConfig`

建议字段：

1. `provider_ref`
2. `provider_kind`
3. `display_name`
4. `base_url`
5. `api_key_env`
6. `default_model`
7. `default_timeout_ms`
8. `default_headers`
9. `metadata`

### 4.2 Model Profile

`LLMModelProfile`

建议字段：

1. `profile_ref`
2. `provider_ref`
3. `model_name`
4. `temperature`
5. `max_output_tokens`
6. `supports_tools`
7. `supports_json_mode`
8. `metadata`

### 4.3 Request

`LLMRequest`

建议字段：

1. `request_id`
2. `provider_ref`
3. `profile_ref`
4. `model_name`
5. `messages`
6. `system_prompt`
7. `response_format`
8. `temperature`
9. `max_output_tokens`
10. `metadata`

### 4.4 Result

`LLMResult`

建议字段：

1. `success`
2. `provider_ref`
3. `model_name`
4. `output_text`
5. `output_json`
6. `finish_reason`
7. `usage`
8. `error_code`
9. `error_message`
10. `metadata`

## 5. 推荐 contracts

### 5.1 `LLMProviderRegistry`

职责：

1. 注册 provider 配置
2. 注册 model profile
3. 查询 provider
4. 查询 profile
5. 列出当前可用 provider / profile

### 5.2 `LLMAdapter`

职责：

1. 接收统一 `LLMRequest`
2. 转换为 provider 协议
3. 调用外部 API
4. 返回统一 `LLMResult`

### 5.3 `LLMInvoker`

职责：

1. 解析 profile
2. 选择 adapter
3. 统一调用入口
4. 在 agent 看来提供稳定能力

## 6. Provider 适配策略

### 6.1 OpenAI

当前推荐：

1. 使用 `Responses API`
2. provider kind 为 `openai`
3. adapter 独立实现，不与其他 provider 混写

### 6.2 DeepSeek

当前推荐：

1. 使用 `deepseek-chat` 兼容接口
2. provider kind 为 `deepseek`
3. adapter 独立实现

### 6.3 为什么分开 adapter

虽然 DeepSeek 在部分接口上兼容 OpenAI 风格，但仍建议分开 adapter。

原因：

1. 后续 structured output 差异更好处理
2. tool calling 差异更容易隔离
3. usage 字段差异不会污染通用层
4. 错误处理更稳定

## 7. 配置加载原则

当前推荐从环境变量或 `.env` 加载。

建议变量：

1. `AGENTSROLES_DEEPSEEK_API_KEY`
2. `AGENTSROLES_DEEPSEEK_BASE_URL`
3. `AGENTSROLES_DEEPSEEK_MODEL`
4. `AGENTSROLES_OPENAI_API_KEY`
5. `AGENTSROLES_OPENAI_BASE_URL`
6. `AGENTSROLES_OPENAI_MODEL`
7. `AGENTSROLES_DEFAULT_LLM_PROFILE`

当前项目已支持从项目根目录 `.env` 自动读取。

## 8. 与领域包的关系

领域 agent 现在推荐的写法是：

1. 优先通过 `context.services.llm_invoker` 调用 LLM
2. 通过 `llm_profile_ref` 选择默认 profile
3. 当 LLM 不可用时，允许保留本地 fallback

这样做的好处：

1. 可以先自测，再逐步提高真实 LLM 占比
2. 不会把 agent 绑定死在某一家 provider 上
3. 后续新领域可以复用同一套接入方式

## 9. 当前项目落地状态

当前已经完成：

1. `core/llm` 基础模型、registry、invoker、config
2. `OpenAI adapter`
3. `DeepSeek adapter`
4. 教育域 5 个 agent 的 LLM-first 能力
5. 教育项目助手的 LLM 接入
6. DeepSeek-first 策略

当前尚未追求：

1. 生产级 provider failover
2. 多租户 provider routing
3. 完整的 prompt management 系统
4. 成熟的 token cost governance

## 10. 当前结论

这一层现在已经足够支撑：

1. 你提供真实 DeepSeek / OpenAI API 后进行本地自测
2. 教育域 agent 用真实模型运行
3. 后续新领域继续沿用同一套 LLM 接入方式

它的核心价值不是“多接了两个 API”，而是：

`把模型供应商差异隔离在平台边界内，让 agent 与 domain pack 继续保持稳定。`
