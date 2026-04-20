from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.software_supply_chain.ui_settings.models import SoftwareSupplyChainUiSettings
from application.software_supply_chain.ui_settings.repositories import (
    FileSoftwareSupplyChainUiSettingsRepository,
)


class SoftwareSupplyChainUiSettingsRepositoryTestCase(unittest.TestCase):
    def test_file_repository_keeps_current_repo_in_saved_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = FileSoftwareSupplyChainUiSettingsRepository(
                Path(temp_dir) / "ui_settings.json"
            )

            saved = repository.save(
                SoftwareSupplyChainUiSettings(
                    current_repo_url="https://github.com/example/alpha",
                    saved_repo_urls=["https://github.com/example/beta"],
                )
            )

            self.assertEqual(saved.current_repo_url, "https://github.com/example/alpha")
            self.assertEqual(
                saved.saved_repo_urls,
                [
                    "https://github.com/example/alpha",
                    "https://github.com/example/beta",
                ],
            )

    def test_file_repository_migrates_legacy_repo_url_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "ui_settings.json"
            file_path.write_text(
                json.dumps({"repo_url": "https://github.com/example/legacy"}),
                encoding="utf-8",
            )
            repository = FileSoftwareSupplyChainUiSettingsRepository(file_path)

            loaded = repository.get()

            self.assertEqual(loaded.current_repo_url, "https://github.com/example/legacy")
            self.assertEqual(
                loaded.saved_repo_urls,
                ["https://github.com/example/legacy"],
            )


if __name__ == "__main__":
    unittest.main()
