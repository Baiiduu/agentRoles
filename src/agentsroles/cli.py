from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .demo_mcp_server import run as run_demo_mcp_server_app
from .frontend import serve_frontend


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_host(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_port(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def run_backend(host: str | None = None, port: int | None = None) -> None:
    from interfaces.http_console import serve_api

    serve_api(
        host=host or _env_host("AGENTSROLES_BACKEND_HOST", "127.0.0.1"),
        port=port or _env_port("AGENTSROLES_BACKEND_PORT", 8765),
    )


def run_web_console(host: str | None = None, port: int | None = None) -> None:
    from interfaces.http_console import serve_fullstack

    serve_fullstack(
        host=host or _env_host("AGENTSROLES_WEB_HOST", "127.0.0.1"),
        port=port or _env_port("AGENTSROLES_WEB_PORT", 8765),
    )


def run_frontend(host: str | None = None, port: int | None = None) -> None:
    serve_frontend(
        host=host or _env_host("AGENTSROLES_FRONTEND_HOST", "127.0.0.1"),
        port=port or _env_port("AGENTSROLES_FRONTEND_PORT", 8766),
    )


def run_demo_mcp_server() -> None:
    run_demo_mcp_server_app()


def run_backend_smoke_tests() -> None:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "tests.unit.test_agent_registry",
        "tests.unit.test_memory_services",
        "tests.unit.test_tool_layer",
        "tests.unit.test_observability_queries",
        "tests.unit.test_domain_agent_executor",
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT)
    raise SystemExit(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentsroles")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("backend", "web", "frontend"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--host")
        sub.add_argument("--port", type=int)

    subparsers.add_parser("demo-mcp")
    subparsers.add_parser("smoke-tests")

    args = parser.parse_args(argv)

    if args.command == "backend":
        run_backend(host=args.host, port=args.port)
        return 0
    if args.command == "web":
        run_web_console(host=args.host, port=args.port)
        return 0
    if args.command == "frontend":
        run_frontend(host=args.host, port=args.port)
        return 0
    if args.command == "demo-mcp":
        run_demo_mcp_server()
        return 0
    if args.command == "smoke-tests":
        run_backend_smoke_tests()
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2
