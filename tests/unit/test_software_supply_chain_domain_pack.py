from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_packs import get_registered_agent_descriptors
from domain_packs.software_supply_chain import SoftwareSupplyChainDomainPack


class SoftwareSupplyChainDomainPackTestCase(unittest.TestCase):
    def test_pack_exposes_four_supply_chain_agents(self) -> None:
        descriptors = SoftwareSupplyChainDomainPack.get_agent_descriptors()

        self.assertEqual(len(descriptors), 4)
        self.assertEqual(
            {descriptor.agent_id for descriptor in descriptors},
            {
                "dependency_auditor",
                "vulnerability_remediator",
                "compliance_specialist",
                "evolver_agent",
            },
        )
        self.assertEqual(
            {descriptor.implementation_ref for descriptor in descriptors},
            {
                "software_supply_chain.dependency_auditor",
                "software_supply_chain.vulnerability_remediator",
                "software_supply_chain.compliance_specialist",
                "software_supply_chain.evolver_agent",
            },
        )
        self.assertTrue(
            all(descriptor.domain == "software_supply_chain" for descriptor in descriptors)
        )

    def test_registered_descriptors_include_supply_chain_agents(self) -> None:
        descriptors = get_registered_agent_descriptors()
        descriptor_map = {descriptor.agent_id: descriptor for descriptor in descriptors}

        self.assertIn("dependency_auditor", descriptor_map)
        self.assertIn("vulnerability_remediator", descriptor_map)
        self.assertIn("compliance_specialist", descriptor_map)
        self.assertIn("evolver_agent", descriptor_map)
        self.assertEqual(
            descriptor_map["dependency_auditor"].memory_scopes,
            ["domain:software_supply_chain", "session:software_supply_chain:{thread_id}"],
        )


if __name__ == "__main__":
    unittest.main()
