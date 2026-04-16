from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TestProDomainMetadata:
    domain_name: str
    pack_version: str
    summary: str
    owner: str
    capability_tags: list[str] = field(default_factory=list)
    maturity: str = "prototype"


TEST_PRO_DOMAIN_METADATA = TestProDomainMetadata(
    domain_name="test_pro",
    pack_version="0.1.0",
    summary=(
        "Minimal test-focused domain pack for prompt tuning, response shaping, "
        "and iterative agent behavior experiments."
    ),
    owner="agentsRoles",
    capability_tags=[
        "testing",
        "prompt-lab",
        "agent-tuning",
        "sandbox-chat",
    ],
    maturity="prototype",
)
