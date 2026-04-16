from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SoftwareSupplyChainDomainMetadata:
    domain_name: str
    pack_version: str
    summary: str
    owner: str
    capability_tags: list[str] = field(default_factory=list)
    maturity: str = "prototype"


SOFTWARE_SUPPLY_CHAIN_DOMAIN_METADATA = SoftwareSupplyChainDomainMetadata(
    domain_name="software_supply_chain",
    pack_version="0.1.0",
    summary=(
        "Software supply chain domain pack for dependency review, vulnerability "
        "remediation, compliance analysis, and iterative security evolution."
    ),
    owner="agentsRoles",
    capability_tags=[
        "software-supply-chain",
        "dependency-audit",
        "vulnerability-remediation",
        "compliance-review",
        "security-evolution",
    ],
    maturity="prototype",
)
