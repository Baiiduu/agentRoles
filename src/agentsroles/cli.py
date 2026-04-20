from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .demo_mcp_server import run as run_demo_mcp_server_app
from .frontend import serve_frontend


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_WORKSPACE = PROJECT_ROOT / "frontend" / "workspace"


def _env_host(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_port(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _resolve_npm_command() -> str:
    for candidate in ("npm.cmd", "npm"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("npm was not found in PATH")


def _build_dev_backend_command(host: str, port: int) -> list[str]:
    return [sys.executable, "-m", "agentsroles", "backend", "--host", host, "--port", str(port)]


def _build_dev_frontend_command(host: str, port: int) -> list[str]:
    return [_resolve_npm_command(), "run", "dev", "--", "--host", host, "--port", str(port)]


def _terminate_process(process: subprocess.Popen[bytes] | subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def run_dev(
    backend_host: str | None = None,
    backend_port: int | None = None,
    frontend_host: str | None = None,
    frontend_port: int | None = None,
) -> None:
    resolved_backend_host = backend_host or _env_host("AGENTSROLES_BACKEND_HOST", "127.0.0.1")
    resolved_backend_port = backend_port or _env_port("AGENTSROLES_BACKEND_PORT", 8765)
    resolved_frontend_host = frontend_host or _env_host("AGENTSROLES_DEV_FRONTEND_HOST", "127.0.0.1")
    resolved_frontend_port = frontend_port or _env_port("AGENTSROLES_DEV_FRONTEND_PORT", 5173)

    backend_command = _build_dev_backend_command(resolved_backend_host, resolved_backend_port)
    frontend_command = _build_dev_frontend_command(resolved_frontend_host, resolved_frontend_port)
    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE_URL"] = (
        f"http://{resolved_backend_host}:{resolved_backend_port}"
    )

    print(
        "Starting dev backend:",
        subprocess.list2cmdline(backend_command),
    )
    backend_process = subprocess.Popen(backend_command, cwd=PROJECT_ROOT)

    try:
        print(
            "Starting dev frontend:",
            subprocess.list2cmdline(frontend_command),
        )
        frontend_process = subprocess.Popen(
            frontend_command,
            cwd=FRONTEND_WORKSPACE,
            env=frontend_env,
        )
    except Exception:
        _terminate_process(backend_process)
        raise

    try:
        backend_exit_code = backend_process.poll()
        frontend_exit_code = frontend_process.poll()
        while backend_exit_code is None and frontend_exit_code is None:
            time.sleep(0.5)
            backend_exit_code = backend_process.poll()
            frontend_exit_code = frontend_process.poll()
    except KeyboardInterrupt:
        print("Stopping dev processes...")
        _terminate_process(frontend_process)
        _terminate_process(backend_process)
        raise SystemExit(130)

    _terminate_process(frontend_process)
    _terminate_process(backend_process)

    if backend_exit_code not in (None, 0):
        raise SystemExit(backend_exit_code)
    if frontend_exit_code not in (None, 0):
        raise SystemExit(frontend_exit_code)


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

    dev = subparsers.add_parser("dev")
    dev.add_argument("--backend-host")
    dev.add_argument("--backend-port", type=int)
    dev.add_argument("--frontend-host")
    dev.add_argument("--frontend-port", type=int)

    subparsers.add_parser("demo-mcp")
    subparsers.add_parser("smoke-tests")

    args = parser.parse_args(argv)

    if args.command == "dev":
        run_dev(
            backend_host=args.backend_host,
            backend_port=args.backend_port,
            frontend_host=args.frontend_host,
            frontend_port=args.frontend_port,
        )
        return 0
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
