from __future__ import annotations

import json
from pathlib import Path


DEFAULT_MCP_IMPORT_CONFIG: dict[str, object] = {
    "schema_version": 1,
    "notes": "Add MCP server definitions here to import them into the runtime registry.",
    "mcp_servers": [],
}


class MCPImportConfigRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    @property
    def file_path(self) -> Path:
        return self._file_path

    def list_mcp_servers(self) -> list[dict[str, object]]:
        payload = self._read_payload()
        raw_servers = payload.get("mcp_servers") or []
        if not isinstance(raw_servers, list):
            raise ValueError("mcp_servers must be a list")
        servers: list[dict[str, object]] = []
        for index, item in enumerate(raw_servers):
            if not isinstance(item, dict):
                raise ValueError(f"mcp_servers[{index}] must be an object")
            servers.append({str(key): value for key, value in item.items()})
        return servers

    def ensure_exists(self) -> None:
        if self._file_path.exists():
            return
        self._file_path.write_text(
            json.dumps(DEFAULT_MCP_IMPORT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_payload(self) -> dict[str, object]:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_exists()
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("MCP import config must be a JSON object")
        return payload
