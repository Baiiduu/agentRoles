"""LLM provider registry, routing invoker, and provider adapters."""

from .models import (
    LLMMessage,
    LLMMessageRole,
    LLMModelProfile,
    LLMProviderConfig,
    LLMProviderKind,
    LLMRequest,
    LLMResponseFormatKind,
    LLMResult,
    LLMToolCall,
    LLMToolSpec,
    LLMUsage,
)

__all__ = [
    "DeepSeekChatAdapter",
    "EnvironmentConfigBundle",
    "EnvironmentProviderConfigLoader",
    "InMemoryLLMProviderRegistry",
    "LLMMessage",
    "LLMMessageRole",
    "LLMModelProfile",
    "LLMProviderConfig",
    "LLMProviderKind",
    "LLMRequest",
    "LLMResponseFormatKind",
    "LLMResult",
    "LLMToolCall",
    "LLMToolSpec",
    "LLMUsage",
    "OpenAIResponsesAdapter",
    "RoutingLLMInvoker",
]


def __getattr__(name: str):
    if name in {"EnvironmentConfigBundle", "EnvironmentProviderConfigLoader"}:
        from .config import EnvironmentConfigBundle, EnvironmentProviderConfigLoader

        return {
            "EnvironmentConfigBundle": EnvironmentConfigBundle,
            "EnvironmentProviderConfigLoader": EnvironmentProviderConfigLoader,
        }[name]
    if name == "InMemoryLLMProviderRegistry":
        from .registry import InMemoryLLMProviderRegistry

        return InMemoryLLMProviderRegistry
    if name == "RoutingLLMInvoker":
        from .invoker import RoutingLLMInvoker

        return RoutingLLMInvoker
    if name == "OpenAIResponsesAdapter":
        from .openai_adapter import OpenAIResponsesAdapter

        return OpenAIResponsesAdapter
    if name == "DeepSeekChatAdapter":
        from .deepseek_adapter import DeepSeekChatAdapter

        return DeepSeekChatAdapter
    raise AttributeError(name)
