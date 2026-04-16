from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_ROOT / "frontend" / "workspace" / "dist"


def serve_frontend(host: str = "127.0.0.1", port: int = 8766) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(STATIC_DIR))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Education frontend running at http://{host}:{port}")
        server.serve_forever()
