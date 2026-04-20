from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.llm import LLMResult
from interfaces.web_console import EducationConsoleService


class FakeAssistantLLMInvoker:
    def __init__(self) -> None:
        self.last_request = None

    def invoke(self, request, context=None):
        self.last_request = request
        return LLMResult(
            success=True,
            provider_ref="deepseek",
            model_name="deepseek-chat",
            output_text="当前项目已经可以先从 diagnostic_plan 工作流开始做教育领域测试。",
        )


class FakeDisabledLLMInvoker:
    def invoke(self, request, context=None):
        return LLMResult(
            success=False,
            provider_ref="test",
            model_name="fake-model",
            error_code="TEST_DISABLED",
            error_message="llm disabled in unit test",
        )


def make_console_service(*, llm_invoker_override=None) -> EducationConsoleService:
    return EducationConsoleService(llm_invoker_override=llm_invoker_override)
