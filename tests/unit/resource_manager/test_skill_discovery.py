from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.resource_registry.repository import FileResourceRegistryRepository
from core.resource_registry.service import ResourceRegistryService


class SkillDiscoveryTests(unittest.TestCase):
    def test_discovery_reads_codex_home_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = root / "external_codex_home"
            skill_dir = codex_home / "skills" / "sample-skill"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                """
---
name: Sample Skill
description: Example skill description.
---

# Sample Skill
                """.strip(),
                encoding="utf-8",
            )

            service = ResourceRegistryService(
                FileResourceRegistryRepository(root / "storage" / "registry.json"),
                project_root=root,
            )

            with patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
                discovery = service.list_discovered_skills()

            self.assertEqual(len(discovery["sources"]), 1)
            self.assertEqual(discovery["skills"][0]["skill_name"], "sample-skill")
            self.assertEqual(discovery["skills"][0]["name"], "Sample Skill")
            self.assertEqual(discovery["skills"][0]["source_kind"], "codex_home")

    def test_sync_preserves_existing_skill_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = root / "external_codex_home"
            skill_dir = codex_home / "skills" / "sample-skill"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                """
---
name: Sample Skill
description: Example skill description.
---
                """.strip(),
                encoding="utf-8",
            )

            service = ResourceRegistryService(
                FileResourceRegistryRepository(root / "storage" / "registry.json"),
                project_root=root,
            )
            service.save_skill(
                {
                    "skill_name": "sample-skill",
                    "name": "Manual Name",
                    "description": "Manual description",
                    "trigger_kinds": ["analysis"],
                    "enabled": False,
                    "notes": "Keep my settings",
                }
            )

            with patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
                synced = service.sync_skills_from_sources()

            self.assertEqual(len(synced), 1)
            registry = service.get_registry()
            saved = next(item for item in registry.skills if item.skill_name == "sample-skill")
            self.assertFalse(saved.enabled)
            self.assertEqual(saved.trigger_kinds, ["analysis"])
            self.assertEqual(saved.notes, "Keep my settings")
            self.assertEqual(saved.name, "Sample Skill")
            self.assertEqual(saved.source_kind, "codex_home")

    def test_custom_skill_source_participates_in_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            custom_root = root / "external-skills"
            skill_dir = custom_root / "custom-source-skill"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                """
---
name: Custom Source Skill
description: Comes from a saved skill source.
---
                """.strip(),
                encoding="utf-8",
            )

            service = ResourceRegistryService(
                FileResourceRegistryRepository(root / "storage" / "registry.json"),
                project_root=root,
            )
            service.save_skill_source(
                {
                    "source_ref": "custom.local",
                    "source_kind": "custom",
                    "root_path": str(custom_root),
                    "label": "Local custom source",
                }
            )

            with patch.dict("os.environ", {}, clear=True):
                discovery = service.list_discovered_skills()

            self.assertEqual(
                [item["source_ref"] for item in discovery["sources"]],
                ["custom.local"],
            )
            self.assertEqual(discovery["skills"][0]["skill_name"], "custom-source-skill")
            self.assertEqual(discovery["skills"][0]["name"], "Custom Source Skill")

    def test_duplicate_skill_name_surfaces_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_root = root / "skills-a"
            second_root = root / "skills-b"
            for base in (first_root, second_root):
                skill_dir = base / "duplicate-skill"
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(
                    """
---
name: Duplicate Skill
description: Duplicate from another source.
---
                    """.strip(),
                    encoding="utf-8",
                )

            service = ResourceRegistryService(
                FileResourceRegistryRepository(root / "storage" / "registry.json"),
                project_root=root,
            )
            service.save_skill_source(
                {
                    "source_ref": "custom.a",
                    "source_kind": "custom",
                    "root_path": str(first_root),
                    "label": "A",
                }
            )
            service.save_skill_source(
                {
                    "source_ref": "custom.b",
                    "source_kind": "custom",
                    "root_path": str(second_root),
                    "label": "B",
                }
            )

            with patch.dict("os.environ", {}, clear=True):
                discovery = service.list_discovered_skills()

            self.assertEqual(len(discovery["conflicts"]), 1)
            self.assertEqual(discovery["conflicts"][0]["conflict_kind"], "duplicate_skill_name")
            self.assertEqual(discovery["conflicts"][0]["skill_name"], "duplicate-skill")

    def test_can_delete_skill_and_skill_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = ResourceRegistryService(
                FileResourceRegistryRepository(root / "storage" / "registry.json"),
                project_root=root,
            )
            service.save_skill(
                {
                    "skill_name": "temporary-skill",
                    "name": "Temporary Skill",
                }
            )
            service.save_skill_source(
                {
                    "source_ref": "temporary.source",
                    "source_kind": "custom",
                    "root_path": str(root / "skills"),
                    "label": "Temporary Source",
                }
            )

            service.delete_skill("temporary-skill")
            service.delete_skill_source("temporary.source")

            registry = service.get_registry()
            self.assertEqual(registry.skills, [])
            self.assertEqual(registry.skill_sources, [])


if __name__ == "__main__":
    unittest.main()
