from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agentsroles import cli


class CliDevCommandTestCase(unittest.TestCase):
    def test_build_dev_backend_command_uses_current_python(self) -> None:
        command = cli._build_dev_backend_command("127.0.0.1", 8765)

        self.assertEqual(
            command,
            [sys.executable, "-m", "agentsroles", "backend", "--host", "127.0.0.1", "--port", "8765"],
        )

    def test_build_dev_frontend_command_uses_resolved_npm(self) -> None:
        with mock.patch("agentsroles.cli._resolve_npm_command", return_value="C:\\npm.cmd"):
            command = cli._build_dev_frontend_command("127.0.0.1", 5173)

        self.assertEqual(
            command,
            ["C:\\npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        )

    def test_resolve_npm_command_prefers_npm_cmd_on_windows(self) -> None:
        with mock.patch("agentsroles.cli.shutil.which", side_effect=["C:\\npm.cmd", None]):
            command = cli._resolve_npm_command()

        self.assertEqual(command, "C:\\npm.cmd")


if __name__ == "__main__":
    unittest.main()
