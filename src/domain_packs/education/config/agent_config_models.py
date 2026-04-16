from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonMap = dict[str, Any]


@dataclass
class EducationAgentConfig:
    agent_id: str
    enabled: bool
    llm_profile_ref: str
    system_prompt: str
    instruction_appendix: str = ""
    response_style: str = "structured"
    quality_bar: str = ""
    handoff_targets: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agent_id = self.agent_id.strip()
        self.llm_profile_ref = self.llm_profile_ref.strip()
        self.system_prompt = self.system_prompt.strip()
        self.instruction_appendix = self.instruction_appendix.strip()
        self.response_style = self.response_style.strip() or "structured"
        self.quality_bar = self.quality_bar.strip()
        self.handoff_targets = [item.strip() for item in self.handoff_targets if item.strip()]
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")
        if not self.llm_profile_ref:
            raise ValueError("llm_profile_ref must be non-empty")
        if not self.system_prompt:
            raise ValueError("system_prompt must be non-empty")
