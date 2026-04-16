from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.llm import (
    DeepSeekChatAdapter,
    EnvironmentProviderConfigLoader,
    InMemoryLLMProviderRegistry,
    LLMMessage,
    LLMMessageRole,
    LLMModelProfile,
    LLMProviderConfig,
    LLMProviderKind,
    LLMRequest,
    LLMResponseFormatKind,
    OpenAIResponsesAdapter,
    RoutingLLMInvoker,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _CapturingAdapter:
    def __init__(self) -> None:
        self.seen_request = None
        self.seen_provider = None

    def can_handle(self, provider_kind: LLMProviderKind) -> bool:
        return provider_kind == LLMProviderKind.OPENAI

    def invoke(self, request, provider_config, profile=None):
        self.seen_request = request
        self.seen_provider = provider_config
        from core.llm import LLMResult

        return LLMResult(
            success=True,
            provider_ref=provider_config.provider_ref,
            model_name=request.model_name or provider_config.default_model,
            output_text="ok",
        )


class LLMLayerTestCase(unittest.TestCase):
    def test_environment_loader_reads_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "AGENTSROLES_OPENAI_API_KEY=file-openai-key",
                        "AGENTSROLES_OPENAI_MODEL=gpt-5-mini",
                        "AGENTSROLES_DEEPSEEK_API_KEY=file-deepseek-key",
                        "AGENTSROLES_DEEPSEEK_MODEL=deepseek-chat",
                        "AGENTSROLES_DEFAULT_LLM_PROFILE=openai.default",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {}, clear=True):
                loader = EnvironmentProviderConfigLoader(env_file=env_file)
                bundle = loader.load()

        provider_refs = {provider.provider_ref for provider in bundle.providers}
        profile_refs = {profile.profile_ref for profile in bundle.profiles}
        self.assertEqual(provider_refs, {"openai", "deepseek"})
        self.assertEqual(bundle.default_profile_ref, "deepseek.default")
        self.assertIn("education.curriculum_planner.default", profile_refs)
        self.assertIn("education.tutor_coach.default", profile_refs)

    def test_environment_loader_reads_openai_and_deepseek(self) -> None:
        env = {
            "AGENTSROLES_OPENAI_API_KEY": "openai-key",
            "AGENTSROLES_OPENAI_MODEL": "gpt-5",
            "AGENTSROLES_DEEPSEEK_API_KEY": "deepseek-key",
            "AGENTSROLES_DEEPSEEK_MODEL": "deepseek-chat",
            "AGENTSROLES_DEFAULT_LLM_PROFILE": "deepseek.default",
        }
        with patch.dict("os.environ", env, clear=False):
            loader = EnvironmentProviderConfigLoader()
            bundle = loader.load()

        profile_refs = {profile.profile_ref for profile in bundle.profiles}
        self.assertEqual(len(bundle.providers), 2)
        self.assertEqual(bundle.default_profile_ref, "deepseek.default")
        self.assertIn("openai.default", profile_refs)
        self.assertIn("deepseek.default", profile_refs)
        self.assertIn("education.learner_profiler.default", profile_refs)
        self.assertIn("education.curriculum_planner.default", profile_refs)
        self.assertIn("education.exercise_designer.default", profile_refs)
        self.assertIn("education.reviewer_grader.default", profile_refs)
        self.assertIn("education.tutor_coach.default", profile_refs)

    def test_routing_invoker_materializes_model_from_profile(self) -> None:
        registry = InMemoryLLMProviderRegistry()
        registry.register_provider(
            LLMProviderConfig(
                provider_ref="openai",
                provider_kind=LLMProviderKind.OPENAI,
                display_name="OpenAI",
                base_url="https://api.openai.com/v1",
                api_key_env="AGENTSROLES_OPENAI_API_KEY",
                default_model="gpt-5",
            )
        )
        registry.register_profile(
            LLMModelProfile(
                profile_ref="openai.default",
                provider_ref="openai",
                model_name="gpt-5-mini",
                temperature=0.3,
                is_default=True,
            )
        )
        adapter = _CapturingAdapter()
        invoker = RoutingLLMInvoker(registry=registry, adapters=[adapter])

        result = invoker.invoke(
            LLMRequest(
                request_id="req-1",
                profile_ref="openai.default",
                messages=[LLMMessage(role=LLMMessageRole.USER, content="hello")],
            )
        )

        self.assertTrue(result.success)
        self.assertEqual(adapter.seen_provider.provider_ref, "openai")
        self.assertEqual(adapter.seen_request.model_name, "gpt-5-mini")
        self.assertEqual(adapter.seen_request.temperature, 0.3)

    def test_openai_adapter_maps_request_and_response(self) -> None:
        adapter = OpenAIResponsesAdapter()
        provider = LLMProviderConfig(
            provider_ref="openai",
            provider_kind=LLMProviderKind.OPENAI,
            display_name="OpenAI",
            base_url="https://api.openai.com/v1",
            api_key_env="AGENTSROLES_OPENAI_API_KEY",
            default_model="gpt-5",
        )
        request = LLMRequest(
            request_id="req-openai",
            model_name="gpt-5",
            system_prompt="be concise",
            response_format=LLMResponseFormatKind.JSON_OBJECT,
            messages=[LLMMessage(role=LLMMessageRole.USER, content="return json")],
        )
        response_payload = {
            "model": "gpt-5",
            "status": "completed",
            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "{\"answer\":\"ok\"}"}],
                }
            ],
        }

        with patch.dict("os.environ", {"AGENTSROLES_OPENAI_API_KEY": "secret"}, clear=False):
            with patch(
                "core.llm.openai_adapter.urllib.request.urlopen",
                return_value=_FakeResponse(response_payload),
            ) as mocked_urlopen:
                result = adapter.invoke(request, provider)

        http_request = mocked_urlopen.call_args.args[0]
        sent_payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(http_request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(sent_payload["model"], "gpt-5")
        self.assertEqual(sent_payload["instructions"], "be concise")
        self.assertEqual(result.output_text, "{\"answer\":\"ok\"}")
        self.assertEqual(result.output_json, {"answer": "ok"})
        self.assertEqual(result.usage.total_tokens, 18)

    def test_deepseek_adapter_maps_request_and_response(self) -> None:
        adapter = DeepSeekChatAdapter()
        provider = LLMProviderConfig(
            provider_ref="deepseek",
            provider_kind=LLMProviderKind.DEEPSEEK,
            display_name="DeepSeek",
            base_url="https://api.deepseek.com",
            api_key_env="AGENTSROLES_DEEPSEEK_API_KEY",
            default_model="deepseek-chat",
        )
        request = LLMRequest(
            request_id="req-deepseek",
            model_name="deepseek-chat",
            messages=[LLMMessage(role=LLMMessageRole.USER, content="hello")],
        )
        response_payload = {
            "model": "deepseek-chat",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "hi there"},
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
        }

        with patch.dict("os.environ", {"AGENTSROLES_DEEPSEEK_API_KEY": "secret"}, clear=False):
            with patch(
                "core.llm.deepseek_adapter.urllib.request.urlopen",
                return_value=_FakeResponse(response_payload),
            ) as mocked_urlopen:
                result = adapter.invoke(request, provider)

        http_request = mocked_urlopen.call_args.args[0]
        sent_payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(
            http_request.full_url,
            "https://api.deepseek.com/chat/completions",
        )
        self.assertEqual(sent_payload["model"], "deepseek-chat")
        self.assertEqual(sent_payload["messages"][0]["content"], "hello")
        self.assertEqual(result.output_text, "hi there")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.usage.total_tokens, 13)
