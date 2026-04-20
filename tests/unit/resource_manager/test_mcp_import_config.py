from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.resource_manager.mcp_import_config import (
    DEFAULT_MCP_IMPORT_CONFIG,
    MCPImportConfigRepository,
)
from core.resource_registry.repository import FileResourceRegistryRepository
from core.resource_registry.service import ResourceRegistryService


class MCPImportConfigRepositoryTests(unittest.TestCase):
    def test_repository_creates_default_root_config_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "agentsroles.mcp.json"

            repository = MCPImportConfigRepository(config_path)

            servers = repository.list_mcp_servers()

            self.assertEqual(servers, [])
            self.assertTrue(config_path.exists())
            self.assertIn('"schema_version": 1', config_path.read_text(encoding="utf-8"))

    def test_imported_servers_can_be_synced_into_runtime_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "agentsroles.mcp.json"
            config_path.write_text(
                """
{
  "schema_version": 1,
  "mcp_servers": [
    {
      "server_ref": "github.audit",
      "name": "GitHub Audit Gateway",
      "connection_mode": "external",
      "transport_kind": "streamable_http",
      "endpoint": "http://127.0.0.1:9000/mcp",
      "tool_refs": ["repo.scan"],
      "notes": "Imported from root config."
    }
  ]
}
                """.strip(),
                encoding="utf-8",
            )
            registry_path = root / "storage" / "resource_manager" / "agent_resource_registry.json"
            resource_service = ResourceRegistryService(
                FileResourceRegistryRepository(registry_path),
                project_root=root,
            )
            resource_service.save_mcp_server(
                {
                    "server_ref": "manual.workspace",
                    "name": "Manual Workspace",
                    "tool_refs": ["fs.list_dir"],
                }
            )

            repository = MCPImportConfigRepository(config_path)
            for payload in repository.list_mcp_servers():
                resource_service.save_mcp_server(payload)

            registry = resource_service.get_registry()
            server_refs = [item.server_ref for item in registry.mcp_servers]

            self.assertEqual(server_refs, ["github.audit", "manual.workspace"])
            imported = next(item for item in registry.mcp_servers if item.server_ref == "github.audit")
            self.assertEqual(imported.endpoint, "http://127.0.0.1:9000/mcp")
            self.assertEqual(imported.tool_refs, ["repo.scan"])


class MCPImportConfigDefaultsTests(unittest.TestCase):
    def test_default_payload_exposes_empty_server_list(self) -> None:
        self.assertEqual(DEFAULT_MCP_IMPORT_CONFIG["mcp_servers"], [])


if __name__ == "__main__":
    unittest.main()
