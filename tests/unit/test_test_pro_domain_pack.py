from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_packs.test_pro import TEST_PRO_DOMAIN_METADATA, TestProDomainPack


class TestProDomainPackTestCase(unittest.TestCase):
    def test_metadata_reflects_coding_agent_positioning(self) -> None:
        self.assertEqual(TEST_PRO_DOMAIN_METADATA.domain_name, "test_pro")
        self.assertEqual(TEST_PRO_DOMAIN_METADATA.maturity, "beta")
        self.assertIn("coding assistant", TEST_PRO_DOMAIN_METADATA.summary.lower())
        self.assertIn("coding-agent", TEST_PRO_DOMAIN_METADATA.capability_tags)
        self.assertIn("code-editing", TEST_PRO_DOMAIN_METADATA.capability_tags)

    def test_descriptor_reflects_single_agent_coding_contract(self) -> None:
        descriptors = TestProDomainPack.get_agent_descriptors()

        self.assertEqual(len(descriptors), 1)
        descriptor = descriptors[0]

        self.assertEqual(descriptor.agent_id, "test_pro_chat")
        self.assertEqual(descriptor.role, "coding_assistant")
        self.assertIn("coding assistant", descriptor.description.lower())
        self.assertIn("repository_understanding", descriptor.capabilities)
        self.assertIn("targeted_code_editing", descriptor.capabilities)
        self.assertIn("symbol_navigation", descriptor.capabilities)
        self.assertIn("verification_guidance", descriptor.capabilities)
        self.assertEqual(descriptor.metadata["stage"], "coding_agent")
        self.assertTrue(descriptor.metadata["writes_memory"])
        self.assertEqual(descriptor.metadata["response_style"], "developer_coding_assistant")
        self.assertIn("acceptance_criteria", descriptor.input_contract["optional_fields"])
        self.assertIn("loop_stop_reason", descriptor.output_contract["produces"])
        self.assertIn("normalized_input", descriptor.output_contract["produces"])
        self.assertIn("memory_context", descriptor.output_contract["produces"])
        self.assertIn("recommended_memory_scope", descriptor.output_contract["produces"])
        self.assertIn("task_memory", descriptor.output_contract["produces"])
        self.assertIn("current_phase", descriptor.output_contract["produces"])
        self.assertIn("working_summary", descriptor.output_contract["produces"])
        self.assertIn("task_state", descriptor.output_contract["produces"])
        self.assertIn("validation_plan", descriptor.output_contract["produces"])


if __name__ == "__main__":
    unittest.main()
