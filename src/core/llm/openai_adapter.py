from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .models import (
    LLMMessage,
    LLMMessageRole,
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


class OpenAIResponsesAdapter:
    def can_handle(self, provider_kind: LLMProviderKind) -> bool:
        return provider_kind == LLMProviderKind.OPENAI

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
            _join_url(provider_config.base_url, "/responses"),
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **{str(key): str(value) for key, value in provider_config.default_headers.items()},
            },
            method="POST",
        )
        if provider_config.organization:
            http_request.add_header("OpenAI-Organization", provider_config.organization)
        if provider_config.project:
            http_request.add_header("OpenAI-Project", provider_config.project)

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
        usage_payload = response_payload.get("usage", {})
        return LLMResult(
            success=True,
            provider_ref=provider_config.provider_ref,
            model_name=str(response_payload.get("model", request.model_name or provider_config.default_model)),
            output_text=self._extract_output_text(response_payload),
            output_json=self._extract_json_output(response_payload, request.response_format),
            finish_reason=self._extract_finish_reason(response_payload),
            usage=LLMUsage(
                input_tokens=usage_payload.get("input_tokens"),
                output_tokens=usage_payload.get("output_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
                latency_ms=elapsed_ms,
            ),
            metadata={"provider_kind": str(provider_config.provider_kind)},
        )

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model_name,
            "input": [self._to_openai_message(message) for message in request.messages],
        }
        if request.system_prompt:
            payload["instructions"] = request.system_prompt
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.response_format == LLMResponseFormatKind.JSON_OBJECT:
            payload["text"] = {"format": {"type": "json_object"}}
        return payload

    def _to_openai_message(self, message: LLMMessage) -> dict[str, object]:
        if message.role in {LLMMessageRole.SYSTEM, LLMMessageRole.DEVELOPER}:
            return {
                "role": str(message.role),
                "content": [{"type": "input_text", "text": message.content}],
            }
        return {
            "role": str(message.role),
            "content": [{"type": "input_text", "text": message.content}],
        }

    def _extract_output_text(self, payload: dict[str, object]) -> str | None:
        output = payload.get("output", [])
        parts: list[str] = []
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "message":
                    continue
                content = item.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") in {"output_text", "text"} and isinstance(
                        block.get("text"), str
                    ):
                        parts.append(block["text"])
        if parts:
            return "\n".join(parts).strip()
        return None

    def _extract_json_output(
        self,
        payload: dict[str, object],
        response_format: LLMResponseFormatKind,
    ) -> dict[str, object] | None:
        if response_format != LLMResponseFormatKind.JSON_OBJECT:
            return None
        output_text = self._extract_output_text(payload)
        if not output_text:
            return None
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _extract_finish_reason(self, payload: dict[str, object]) -> str | None:
        status = payload.get("status")
        return str(status) if status is not None else None
