from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import TYPE_CHECKING

from .models import DEFAULT_REPO_URL, SoftwareSupplyChainUiSettings

if TYPE_CHECKING:
    from infrastructure.persistence import SQLiteDocumentStore


class FileSoftwareSupplyChainUiSettingsRepository:
    def __init__(
        self,
        file_path: Path,
        *,
        default_repo_url: str = DEFAULT_REPO_URL,
    ) -> None:
        self._file_path = file_path
        self._default_repo_url = default_repo_url
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> SoftwareSupplyChainUiSettings:
        if not self._file_path.exists():
            return self._default()
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        return _deserialize_settings(payload, self._default_repo_url)

    def save(self, settings: SoftwareSupplyChainUiSettings) -> SoftwareSupplyChainUiSettings:
        normalized = _normalize_settings(settings, default_repo_url=self._default_repo_url)
        self._file_path.write_text(
            json.dumps(asdict(normalized), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return normalized

    def _default(self) -> SoftwareSupplyChainUiSettings:
        return SoftwareSupplyChainUiSettings(
            current_repo_url=self._default_repo_url,
            saved_repo_urls=[self._default_repo_url],
        )


class SQLiteSoftwareSupplyChainUiSettingsRepository:
    collection_name = "software_supply_chain_ui_settings"
    document_id = "default"

    def __init__(
        self,
        store: SQLiteDocumentStore,
        *,
        default_repo_url: str = DEFAULT_REPO_URL,
        legacy_file_path: Path | None = None,
    ) -> None:
        self._store = store
        self._default_repo_url = default_repo_url
        self._legacy_file_path = legacy_file_path
        self._import_legacy_if_needed()

    def get(self) -> SoftwareSupplyChainUiSettings:
        payload = self._store.get_document(self.collection_name, self.document_id)
        if payload is None:
            settings = self._default()
            self.save(settings)
            return settings
        return _deserialize_settings(payload, self._default_repo_url)

    def save(self, settings: SoftwareSupplyChainUiSettings) -> SoftwareSupplyChainUiSettings:
        normalized = _normalize_settings(settings, default_repo_url=self._default_repo_url)
        self._store.put_document(self.collection_name, self.document_id, asdict(normalized))
        return normalized

    def _import_legacy_if_needed(self) -> None:
        if self._store.get_document(self.collection_name, self.document_id) is not None:
            return
        if self._legacy_file_path is None or not self._legacy_file_path.exists():
            return
        payload = json.loads(self._legacy_file_path.read_text(encoding="utf-8"))
        settings = _deserialize_settings(payload, self._default_repo_url)
        self._store.put_document(self.collection_name, self.document_id, asdict(settings))

    def _default(self) -> SoftwareSupplyChainUiSettings:
        return SoftwareSupplyChainUiSettings(
            current_repo_url=self._default_repo_url,
            saved_repo_urls=[self._default_repo_url],
        )


def _normalize_repo_url(value: str, default_repo_url: str) -> str:
    candidate = value.strip()
    if not candidate:
        return default_repo_url
    if not candidate.startswith(("http://", "https://")):
        raise ValueError("repo_url must start with http:// or https://")
    return candidate


def _normalize_repo_urls(values: list[str], default_repo_url: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = str(value).strip()
        if not candidate:
            continue
        normalized_candidate = _normalize_repo_url(candidate, default_repo_url)
        if normalized_candidate in seen:
            continue
        seen.add(normalized_candidate)
        normalized.append(normalized_candidate)
    return normalized


def _normalize_settings(
    settings: SoftwareSupplyChainUiSettings,
    *,
    default_repo_url: str,
) -> SoftwareSupplyChainUiSettings:
    current_repo_url = _normalize_repo_url(settings.current_repo_url, default_repo_url)
    saved_repo_urls = _normalize_repo_urls(settings.saved_repo_urls, default_repo_url)
    if current_repo_url not in saved_repo_urls:
        saved_repo_urls.insert(0, current_repo_url)
    return SoftwareSupplyChainUiSettings(
        current_repo_url=current_repo_url,
        saved_repo_urls=saved_repo_urls,
    )


def _deserialize_settings(
    payload: dict[str, object],
    default_repo_url: str,
) -> SoftwareSupplyChainUiSettings:
    raw_saved_repo_urls = payload.get("saved_repo_urls")
    if isinstance(raw_saved_repo_urls, list):
        saved_repo_urls = [str(item) for item in raw_saved_repo_urls]
    else:
        saved_repo_urls = []
    current_repo_url = str(
        payload.get("current_repo_url", payload.get("repo_url", default_repo_url))
    )
    return _normalize_settings(
        SoftwareSupplyChainUiSettings(
            current_repo_url=current_repo_url,
            saved_repo_urls=saved_repo_urls,
        ),
        default_repo_url=default_repo_url,
    )
