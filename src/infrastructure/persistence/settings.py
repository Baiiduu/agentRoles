from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


def _expand_path(value: str) -> Path:
    expanded = os.path.expandvars(value.strip())
    return Path(expanded).expanduser()


@dataclass(frozen=True)
class PersistenceSettings:
    backend: str
    storage_root: Path
    sqlite_path: Path
    files_root: Path
    export_root: Path
    auth_root: Path
    default_workspace_root: Path

    def ensure_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_root.mkdir(parents=True, exist_ok=True)
        self.export_root.mkdir(parents=True, exist_ok=True)
        self.auth_root.mkdir(parents=True, exist_ok=True)
        self.default_workspace_root.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_persistence_settings() -> PersistenceSettings:
    backend = (os.getenv("AGENTSROLES_PERSISTENCE_BACKEND", "sqlite").strip() or "sqlite").lower()
    storage_root_value = os.getenv("AGENTSROLES_STORAGE_ROOT", r"E:\agentsRolesData")
    storage_root = _expand_path(storage_root_value)
    sqlite_path_value = os.getenv(
        "AGENTSROLES_SQLITE_PATH",
        str(storage_root / "db" / "agents_roles.sqlite3"),
    )
    files_root_value = os.getenv(
        "AGENTSROLES_FILES_ROOT",
        str(storage_root / "files"),
    )
    export_root_value = os.getenv(
        "AGENTSROLES_EXPORT_ROOT",
        str(storage_root / "exports"),
    )
    auth_root_value = os.getenv(
        "AGENTSROLES_AUTH_ROOT",
        str(storage_root / "auth"),
    )
    workspace_root_value = os.getenv(
        "AGENTSROLES_DEFAULT_WORKSPACE_ROOT",
        str(_expand_path(files_root_value) / "agent_workspaces"),
    )
    settings = PersistenceSettings(
        backend=backend,
        storage_root=storage_root,
        sqlite_path=_expand_path(sqlite_path_value),
        files_root=_expand_path(files_root_value),
        export_root=_expand_path(export_root_value),
        auth_root=_expand_path(auth_root_value),
        default_workspace_root=_expand_path(workspace_root_value),
    )
    settings.ensure_directories()
    return settings
