from __future__ import annotations

"""Compatibility exports for the Test Pro agent implementation.

Keep this module thin so callers can continue importing from
`domain_packs.test_pro.agents.implementations` while the real logic lives in
small internal modules under `agents.impl`.
"""

from .impl.llm_loop import (
    _invoke_final_response,
    _invoke_structured_decision,
    _invoke_tool_if_available,
    _normalize_decision_output,
    _persist_memory_snapshot,
)
from .impl.loop import TestProChatImplementation, get_test_pro_agent_implementations
from .impl.policy import _apply_policy_to_decision, _preferred_tool_decision
from .impl.shared import _NormalizedTestProInput, _ToolExecutionBundle
from .impl.state import (
    _build_working_summary,
    _edit_readiness_status,
    _enrich_final_reply,
    _infer_current_phase,
    _task_state,
    _validation_plan,
)

__all__ = [
    "_NormalizedTestProInput",
    "_ToolExecutionBundle",
    "_apply_policy_to_decision",
    "_build_working_summary",
    "_edit_readiness_status",
    "_enrich_final_reply",
    "_infer_current_phase",
    "_invoke_final_response",
    "_invoke_structured_decision",
    "_invoke_tool_if_available",
    "_normalize_decision_output",
    "_persist_memory_snapshot",
    "_preferred_tool_decision",
    "_task_state",
    "_validation_plan",
    "TestProChatImplementation",
    "get_test_pro_agent_implementations",
]
