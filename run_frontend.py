from __future__ import annotations

from dev_bootstrap import ensure_src_on_path

ensure_src_on_path()

from agentsroles.cli import run_frontend


if __name__ == "__main__":
    run_frontend()
