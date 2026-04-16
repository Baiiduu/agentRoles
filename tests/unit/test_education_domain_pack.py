from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_packs.education import EducationDomainPack


class EducationDomainPackTestCase(unittest.TestCase):
    def test_pack_exposes_five_core_agent_descriptors(self) -> None:
        descriptors = EducationDomainPack.get_agent_descriptors()

        self.assertEqual(len(descriptors), 5)
        self.assertEqual(
            [descriptor.agent_id for descriptor in descriptors],
            [
                "learner_profiler",
                "curriculum_planner",
                "exercise_designer",
                "reviewer_grader",
                "tutor_coach",
            ],
        )

    def test_descriptors_use_generic_domain_executor_and_education_domain(self) -> None:
        descriptors = EducationDomainPack.get_agent_descriptors()

        for descriptor in descriptors:
            self.assertEqual(descriptor.executor_ref, "agent.domain")
            self.assertEqual(descriptor.domain, "education")
            self.assertTrue(descriptor.implementation_ref)
            self.assertIn("edu_default", descriptor.policy_profiles)

    def test_descriptor_collection_returns_deep_copies(self) -> None:
        descriptors = EducationDomainPack.get_agent_descriptors()
        descriptors[0].capabilities.append("mutated")

        reloaded = EducationDomainPack.get_agent_descriptors()

        self.assertNotIn("mutated", reloaded[0].capabilities)

    def test_all_descriptors_define_default_llm_profile(self) -> None:
        descriptors = EducationDomainPack.get_agent_descriptors()

        for descriptor in descriptors:
            self.assertIn("llm_profile_ref", descriptor.metadata)
            self.assertTrue(descriptor.metadata["llm_profile_ref"])
