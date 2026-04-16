from __future__ import annotations

from dev_bootstrap import ensure_src_on_path

ensure_src_on_path()

from agentsroles.demo_mcp_server import run

if __name__ == "__main__":
    run()
