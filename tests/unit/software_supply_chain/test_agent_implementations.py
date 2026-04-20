from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_packs.software_supply_chain.agents.implementations import (
    ComplianceSpecialistImplementation,
    DependencyAuditorImplementation,
    EvolverAgentImplementation,
    SoftwareSupplyChainChatImplementation,
    VulnerabilityRemediatorImplementation,
)


class SoftwareSupplyChainAgentImplementationTestCase(unittest.TestCase):
    def test_supply_chain_agents_use_local_base_implementation(self) -> None:
        self.assertIs(DependencyAuditorImplementation.__mro__[1], SoftwareSupplyChainChatImplementation)
        self.assertIs(VulnerabilityRemediatorImplementation.__mro__[1], SoftwareSupplyChainChatImplementation)
        self.assertIs(ComplianceSpecialistImplementation.__mro__[1], SoftwareSupplyChainChatImplementation)
        self.assertIs(EvolverAgentImplementation.__mro__[1], SoftwareSupplyChainChatImplementation)

    def test_local_base_implementation_does_not_live_in_test_pro(self) -> None:
        self.assertEqual(
            SoftwareSupplyChainChatImplementation.__module__,
            "domain_packs.software_supply_chain.agents.shared_impl.loop",
        )


if __name__ == "__main__":
    unittest.main()
