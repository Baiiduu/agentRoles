from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .service import ProjectConsoleService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = PROJECT_ROOT / "frontend" / "workspace" / "dist"


class _ProjectApiMixin:
    service = ProjectConsoleService()

    def _handle_api_get(self, parsed) -> bool:
        parsed = urlparse(self.path)
        if parsed.path == "/api/overview":
            self._send_json(self.service.get_overview())
            return True
        if parsed.path == "/api/cases":
            self._send_json(self.service.list_case_workspace_cases())
            return True
        if parsed.path.startswith("/api/cases/"):
            case_path = parsed.path.removeprefix("/api/cases/").strip("/")
            if case_path.endswith("/coordination"):
                case_id = case_path.removesuffix("/coordination").strip("/")
                if not case_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "case_id is required")
                    return True
                self._send_json(self.service.get_case_coordination(case_id))
                return True
            case_id = case_path
            if not case_id:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "case_id is required")
                return True
            self._send_json(self.service.get_case_workspace_case(case_id))
            return True
        if parsed.path == "/api/agent-playground/bootstrap":
            self._send_json(self.service.get_agent_playground_bootstrap())
            return True
        if parsed.path == "/api/agent-configs":
            self._send_json(self.service.list_agent_configs())
            return True
        if parsed.path.startswith("/api/agent-configs/"):
            agent_id = parsed.path.removeprefix("/api/agent-configs/").strip("/")
            if not agent_id:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                return True
            self._send_json(self.service.get_agent_config(agent_id))
            return True
        if parsed.path == "/api/agent-capabilities":
            self._send_json(self.service.list_agent_capabilities())
            return True
        if parsed.path.startswith("/api/agent-capabilities/"):
            agent_id = parsed.path.removeprefix("/api/agent-capabilities/").strip("/")
            if not agent_id:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                return True
            self._send_json(self.service.get_agent_capability(agent_id))
            return True
        if parsed.path == "/api/agent-resource-manager":
            self._send_json(self.service.get_agent_resource_manager_snapshot())
            return True
        if parsed.path.startswith("/api/agents/"):
            if parsed.path.endswith("/sessions"):
                agent_id = (
                    parsed.path.removeprefix("/api/agents/")
                    .removesuffix("/sessions")
                    .strip("/")
                )
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                self._send_json(self.service.list_agent_playground_sessions(agent_id))
                return True
            if parsed.path.endswith("/chat-history"):
                agent_id = (
                    parsed.path.removeprefix("/api/agents/")
                    .removesuffix("/chat-history")
                    .strip("/")
                )
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                self._send_json(
                    self.service.get_agent_playground_chat_history(
                        agent_id,
                        session_id=session_id,
                    )
                )
                return True
            agent_id = parsed.path.removeprefix("/api/agents/").strip("/")
            if not agent_id:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                return True
            self._send_json(self.service.get_agent_playground_agent(agent_id))
            return True
        return False

    def _handle_api_post(self, parsed) -> bool:
        try:
            payload = self._read_json_body()
            if parsed.path == "/api/workflows/run":
                result = self.service.run_workflow(
                    str(payload.get("workflow_id", "")),
                    global_context=payload.get("global_context") or {},
                )
                self._send_json(result)
                return True
            if parsed.path == "/api/evals/run":
                result = self.service.run_eval_suite(str(payload.get("suite_id", "")))
                self._send_json(result)
                return True
            if parsed.path == "/api/assistant/chat":
                result = self.service.chat_with_project_agent(str(payload.get("message", "")))
                self._send_json(result)
                return True
            if parsed.path == "/api/agent-sessions/message":
                result = self.service.send_agent_playground_message(payload)
                self._send_json(result)
                return True
            if (
                parsed.path.startswith("/api/agents/")
                and parsed.path.endswith("/sessions/new")
            ):
                agent_id = (
                    parsed.path.removeprefix("/api/agents/")
                    .removesuffix("/sessions/new")
                    .strip("/")
                )
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                result = self.service.create_agent_playground_session(agent_id)
                self._send_json(result)
                return True
            if (
                parsed.path.startswith("/api/agents/")
                and parsed.path.endswith("/delete")
                and "/sessions/" in parsed.path
            ):
                remainder = parsed.path.removeprefix("/api/agents/").strip("/")
                agent_id, _, session_path = remainder.partition("/sessions/")
                session_id = session_path.removesuffix("/delete").strip("/")
                if not agent_id or not session_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id and session_id are required")
                    return True
                result = self.service.delete_agent_playground_session(agent_id, session_id)
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/agent-configs/"):
                agent_id = parsed.path.removeprefix("/api/agent-configs/").strip("/")
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                result = self.service.save_agent_config(agent_id, payload)
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/agent-capabilities/"):
                agent_id = parsed.path.removeprefix("/api/agent-capabilities/").strip("/")
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                result = self.service.save_agent_capability(agent_id, payload)
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/agent-resource-manager/mcp-servers/"):
                server_ref = parsed.path.removeprefix("/api/agent-resource-manager/mcp-servers/").strip("/")
                if server_ref.endswith("/test"):
                    server_ref = server_ref.removesuffix("/test").strip("/")
                    if not server_ref:
                        self._send_error_json(HTTPStatus.BAD_REQUEST, "server_ref is required")
                        return True
                    result = self.service.test_registered_mcp_server(server_ref)
                    self._send_json(result)
                    return True
                if server_ref.endswith("/authenticate"):
                    server_ref = server_ref.removesuffix("/authenticate").strip("/")
                    if not server_ref:
                        self._send_error_json(HTTPStatus.BAD_REQUEST, "server_ref is required")
                        return True
                    result = self.service.authenticate_registered_mcp_server(server_ref)
                    self._send_json(result)
                    return True
                if server_ref.endswith("/discover-tools"):
                    server_ref = server_ref.removesuffix("/discover-tools").strip("/")
                    if not server_ref:
                        self._send_error_json(HTTPStatus.BAD_REQUEST, "server_ref is required")
                        return True
                    result = self.service.discover_registered_mcp_server_tools(server_ref)
                    self._send_json(result)
                    return True
                if not server_ref:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "server_ref is required")
                    return True
                result = self.service.save_registered_mcp_server(server_ref, payload)
                self._send_json(result)
                return True
            if parsed.path == "/api/agent-resource-manager/workspace-root":
                result = self.service.save_agent_workspace_root(payload)
                self._send_json(result)
                return True
            if parsed.path == "/api/agent-resource-manager/workspace-root/pick":
                result = self.service.pick_agent_workspace_root()
                self._send_json(result)
                return True
            if parsed.path == "/api/agent-resource-manager/workspace-root/provision":
                result = self.service.provision_agent_workspace_root()
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/agent-resource-manager/skills/"):
                skill_name = parsed.path.removeprefix("/api/agent-resource-manager/skills/").strip("/")
                if not skill_name:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "skill_name is required")
                    return True
                result = self.service.save_registered_skill(skill_name, payload)
                self._send_json(result)
                return True
            if (
                parsed.path.startswith("/api/agent-resource-manager/agents/")
                and parsed.path.endswith("/workspace")
            ):
                agent_id = (
                    parsed.path.removeprefix("/api/agent-resource-manager/agents/")
                    .removesuffix("/workspace")
                    .strip("/")
                )
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                result = self.service.save_agent_workspace(agent_id, payload)
                self._send_json(result)
                return True
            if (
                parsed.path.startswith("/api/agent-resource-manager/agents/")
                and parsed.path.endswith("/distribution")
            ):
                agent_id = (
                    parsed.path.removeprefix("/api/agent-resource-manager/agents/")
                    .removesuffix("/distribution")
                    .strip("/")
                )
                if not agent_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "agent_id is required")
                    return True
                result = self.service.save_agent_resource_distribution(agent_id, payload)
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/cases/") and parsed.path.endswith("/handoffs"):
                case_id = parsed.path.removeprefix("/api/cases/").removesuffix("/handoffs").strip("/")
                if not case_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "case_id is required")
                    return True
                result = self.service.create_case_handoff(case_id, payload)
                self._send_json(result)
                return True
            if parsed.path.startswith("/api/cases/") and parsed.path.endswith("/session-feed"):
                case_id = (
                    parsed.path.removeprefix("/api/cases/")
                    .removesuffix("/session-feed")
                    .strip("/")
                )
                if not case_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "case_id is required")
                    return True
                result = self.service.append_case_session_feed_item(case_id, payload)
                self._send_json(result)
                return True
            return False
        except KeyError as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, str(exc))
            return True
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return True

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        if not raw_body:
            return {}
        decoded = json.loads(raw_body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("request body must be a JSON object")
        return decoded

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message, "status": status.value}, status=status)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


class ProjectConsoleApiHandler(_ProjectApiMixin, SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if self._handle_api_get(parsed):
                return
            self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
        except KeyError as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if self._handle_api_post(parsed):
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()


class ProjectConsoleFullstackHandler(_ProjectApiMixin, SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if self._handle_api_get(parsed):
                return
            if parsed.path in {"/", "/index.html"}:
                self.path = "/index.html"
            return super().do_GET()
        except KeyError as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if self._handle_api_post(parsed):
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()


def serve_api(host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = partial(ProjectConsoleApiHandler, directory=str(STATIC_DIR))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Project backend running at http://{host}:{port}")
        server.serve_forever()


def serve_fullstack(host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = partial(ProjectConsoleFullstackHandler, directory=str(STATIC_DIR))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Project fullstack console running at http://{host}:{port}")
        server.serve_forever()


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    serve_fullstack(host=host, port=port)


if __name__ == "__main__":
    serve_fullstack()
