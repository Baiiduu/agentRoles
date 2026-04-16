from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.state.models import JsonMap


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class LLMProviderKind(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"


class LLMMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    DEVELOPER = "developer"


class LLMResponseFormatKind(StrEnum):
    TEXT = "text"
    JSON_OBJECT = "json_object"


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must be non-empty")


def _require_unique(items: list[str], field_name: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} contains duplicate values")


@dataclass
class LLMProviderConfig:
    provider_ref: str
    provider_kind: LLMProviderKind
    display_name: str
    base_url: str
    api_key_env: str
    default_model: str
    default_timeout_ms: int = 30_000
    default_headers: JsonMap = field(default_factory=dict)
    organization: str | None = None
    project: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("provider_ref", self.provider_ref),
            ("display_name", self.display_name),
            ("base_url", self.base_url),
            ("api_key_env", self.api_key_env),
            ("default_model", self.default_model),
        ):
            _require_non_empty(value, field_name)
        if self.default_timeout_ms <= 0:
            raise ValueError("default_timeout_ms must be > 0")


@dataclass
class LLMModelProfile:
    profile_ref: str
    provider_ref: str
    model_name: str
    temperature: float | None = None
    max_output_tokens: int | None = None
    top_p: float | None = None
    supports_tools: bool = False
    supports_json_mode: bool = False
    supports_system_prompt: bool = True
    is_default: bool = False
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name, value in (
            ("profile_ref", self.profile_ref),
            ("provider_ref", self.provider_ref),
            ("model_name", self.model_name),
        ):
            _require_non_empty(value, field_name)
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be > 0 when provided")
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature must be >= 0 when provided")
        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be between 0 and 1 when provided")


@dataclass
class LLMMessage:
    role: LLMMessageRole
    content: str
    name: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.content, "content")


@dataclass
class LLMToolSpec:
    name: str
    description: str
    input_schema: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "name")
        _require_non_empty(self.description, "description")


@dataclass
class LLMRequest:
    request_id: str
    messages: list[LLMMessage]
    provider_ref: str | None = None
    profile_ref: str | None = None
    model_name: str | None = None
    system_prompt: str | None = None
    response_format: LLMResponseFormatKind = LLMResponseFormatKind.TEXT
    temperature: float | None = None
    max_output_tokens: int | None = None
    top_p: float | None = None
    tools: list[LLMToolSpec] = field(default_factory=list)
    tool_choice: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.request_id, "request_id")
        if not self.messages:
            raise ValueError("messages must be non-empty")
        tool_names = [tool.name for tool in self.tools]
        _require_unique(tool_names, "tools")
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature must be >= 0 when provided")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be > 0 when provided")
        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be between 0 and 1 when provided")


@dataclass
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


@dataclass
class LLMToolCall:
    tool_name: str
    arguments: JsonMap = field(default_factory=dict)
    call_id: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.tool_name, "tool_name")


@dataclass
class LLMResult:
    success: bool
    provider_ref: str
    model_name: str
    output_text: str | None = None
    output_json: JsonMap | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw_response_ref: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.provider_ref, "provider_ref")
        _require_non_empty(self.model_name, "model_name")
