from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


app = FastMCP("agentsroles-demo-external")


def _workspace_root() -> Path:
    raw = os.environ.get("AGENT_WORKSPACE") or os.environ.get("AGENT_WORKSPACE_ROOT") or "."
    return Path(raw).resolve()


@app.tool()
def echo_text(text: str) -> str:
    return f"echo: {text}"


@app.tool()
def list_workspace() -> list[str]:
    root = _workspace_root()
    root.mkdir(parents=True, exist_ok=True)
    return sorted(item.name for item in root.iterdir())


@app.tool()
def write_workspace_file(path: str, content: str) -> dict[str, object]:
    root = _workspace_root()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path must stay within workspace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target.relative_to(root)), "bytes_written": len(content.encode("utf-8"))}


def run() -> None:
    app.run()
