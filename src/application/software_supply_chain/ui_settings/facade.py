from __future__ import annotations

from pathlib import Path

from infrastructure.persistence import SQLiteDocumentStore, get_persistence_settings

from .models import DEFAULT_REPO_URL, SoftwareSupplyChainUiSettings
from .repositories import (
    FileSoftwareSupplyChainUiSettingsRepository,
    SQLiteSoftwareSupplyChainUiSettingsRepository,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
UI_SETTINGS_FILE = PROJECT_ROOT / "runtime_data" / "software_supply_chain" / "ui_settings.json"


class SoftwareSupplyChainUiSettingsFacade:
    def __init__(self) -> None:
        settings = get_persistence_settings()
        if settings.backend == "sqlite":
            self._repository = SQLiteSoftwareSupplyChainUiSettingsRepository(
                SQLiteDocumentStore(settings.sqlite_path),
                default_repo_url=DEFAULT_REPO_URL,
                legacy_file_path=UI_SETTINGS_FILE,
            )
        else:
            self._repository = FileSoftwareSupplyChainUiSettingsRepository(
                UI_SETTINGS_FILE,
                default_repo_url=DEFAULT_REPO_URL,
            )

    def get_settings(self) -> dict[str, object]:
        return _serialize_settings(self._repository.get())

    def save_settings(self, payload: dict[str, object]) -> dict[str, object]:
        current_repo_url = str(
            payload.get("current_repo_url", payload.get("repo_url", ""))
        ).strip()
        saved_repo_urls = payload.get("saved_repo_urls") or []
        if not isinstance(saved_repo_urls, list):
            raise ValueError("saved_repo_urls must be a list")
        settings = self._repository.save(
            SoftwareSupplyChainUiSettings(
                current_repo_url=current_repo_url,
                saved_repo_urls=[str(item) for item in saved_repo_urls],
            )
        )
        return _serialize_settings(settings)


def _serialize_settings(settings: SoftwareSupplyChainUiSettings) -> dict[str, object]:
    return {
        "repo_url": settings.current_repo_url,
        "current_repo_url": settings.current_repo_url,
        "saved_repo_urls": list(settings.saved_repo_urls),
    }
