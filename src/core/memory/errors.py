from __future__ import annotations

from dataclasses import dataclass

from core.state.models import PolicyDecisionRecord


@dataclass
class MemoryPolicyError(RuntimeError):
    operation: str
    scope: str
    decision: PolicyDecisionRecord

    def __post_init__(self) -> None:
        super().__init__(self.decision.reason_message)
