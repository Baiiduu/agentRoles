from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.resource_manager.agent_resource_manager_service import (
    _agent_capability_file,
    _resource_registry_file,
)
from infrastructure.persistence.settings import PersistenceSettings


class ResourceManagerStoragePathTests(unittest.TestCase):
    def test_resource_manager_files_live_under_configured_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = PersistenceSettings(
                backend="file",
                storage_root=root,
                sqlite_path=root / "db" / "agents_roles.sqlite3",
                files_root=root / "files",
                export_root=root / "exports",
                auth_root=root / "auth",
                default_workspace_root=root / "files" / "agent_workspaces",
            )

            registry_path = _resource_registry_file(settings)
            capability_path = _agent_capability_file(settings)

            self.assertEqual(
                registry_path,
                root / "files" / "resource_manager" / "agent_resource_registry.json",
            )
            self.assertEqual(
                capability_path,
                root / "files" / "agent_admin" / "agent_capabilities.json",
            )
            self.assertNotIn("runtime_data", str(registry_path))
            self.assertNotIn("runtime_data", str(capability_path))


if __name__ == "__main__":
    unittest.main()
