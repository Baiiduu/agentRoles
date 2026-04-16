from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .models import (
    LLMModelProfile,
    LLMProviderConfig,
    LLMProviderKind,
    LLMRequest,
    LLMResponseFormatKind,
    LLMResult,
    LLMUsage,
)


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


class DeepSeekChatAdapter:
    def can_handle(self, provider_kind: LLMProviderKind) -> bool:
        return provider_kind == LLMProviderKind.DEEPSEEK

    def invoke(
        self,
        request: LLMRequest,
        provider_config: LLMProviderConfig,
        profile: LLMModelProfile | None = None,
    ) -> LLMResult:
        api_key = os.getenv(provider_config.api_key_env)
        if not api_key:
            return LLMResult(
                success=False,
                provider_ref=provider_config.provider_ref,
                model_name=request.model_name or provider_config.default_model,
                error_code="LLM_AUTH_ERROR",
                error_message=(
                    f"missing API key in environment variable '{provider_config.api_key_env}'"
                ),
            )

        payload = self._build_payload(request)
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            _join_url(provider_config.base_url, "/chat/completions"),
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **{str(key): str(value) for key, value in provider_config.default_headers.items()},
            },
            method="POST",
        )
        started_at = time.perf_counter()
        try:
            with urllib.request.urlopen(
                http_request,
                timeout=provider_config.default_timeout_ms / 1000,
            ) as response:
                raw_payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return LLMResult(
                success=False,
                provider_ref=provider_config.provider_ref,
                model_name=request.model_name or provider_config.default_model,
                error_code="LLM_BAD_RESPONSE",
                error_message=exc.read().decode("utf-8", errors="replace"),
            )
        except urllib.error.URLError as exc:
            return LLMResult(
                success=False,
                provider_ref=provider_config.provider_ref,
                model_name=request.model_name or provider_config.default_model,
                error_code="LLM_TIMEOUT",
                error_message=str(exc.reason),
            )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

        response_payload = json.loads(raw_payload)
        choice = self._first_choice(response_payload)
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        usage_payload = response_payload.get("usage", {})
        output_json = None
        if request.response_format == LLMResponseFormatKind.JSON_OBJECT and isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                output_json = parsed

        return LLMResult(
            success=True,
            provider_ref=provider_config.provider_ref,
            model_name=str(response_payload.get("model", request.model_name or provider_config.default_model)),
            output_text=content if isinstance(content, str) else None,
            output_json=output_json,
            finish_reason=choice.get("finish_reason") if isinstance(choice, dict) else None,
            usage=LLMUsage(
                input_tokens=usage_payload.get("prompt_tokens"),
                output_tokens=usage_payload.get("completion_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
                latency_ms=elapsed_ms,
            ),
            metadata={"provider_kind": str(provider_config.provider_kind)},
        )

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        messages: list[dict[str, object]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(
            {"role": str(message.role), "content": message.content} for message in request.messages
        )
        payload: dict[str, object] = {
            "model": request.model_name,
            "messages": messages,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.response_format == LLMResponseFormatKind.JSON_OBJECT:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _first_choice(self, payload: dict[str, object]) -> dict[str, object]:
        choices = payload.get("choices", [])
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            return choices[0]
        return {}
