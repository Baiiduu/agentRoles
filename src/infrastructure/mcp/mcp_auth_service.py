from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from threading import Thread
from urllib.parse import parse_qs, urlparse
import json
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import anyio
import httpx
from mcp.client.auth.oauth2 import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FileMCPTokenStorage(TokenStorage):
    def __init__(self, file_path: Path, server_ref: str) -> None:
        self._file_path = file_path
        self._server_ref = server_ref

    async def get_tokens(self) -> OAuthToken | None:
        payload = self._read_payload()
        item = (payload.get(self._server_ref) or {}).get("tokens")
        return OAuthToken.model_validate(item) if item else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        payload = self._read_payload()
        item = payload.setdefault(self._server_ref, {})
        item["tokens"] = tokens.model_dump(mode="json")
        self._write_payload(payload)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        payload = self._read_payload()
        item = (payload.get(self._server_ref) or {}).get("client_info")
        return OAuthClientInformationFull.model_validate(item) if item else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        payload = self._read_payload()
        item = payload.setdefault(self._server_ref, {})
        item["client_info"] = client_info.model_dump(mode="json")
        self._write_payload(payload)

    def _read_payload(self) -> dict[str, object]:
        if not self._file_path.exists():
            self._write_payload({})
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class OAuthCallbackWaiter:
    port: int
    queue: Queue[tuple[str, str | None]]
    server: ThreadingHTTPServer
    thread: Thread

    @classmethod
    def start(cls) -> "OAuthCallbackWaiter":
        port = _find_free_port()
        queue: Queue[tuple[str, str | None]] = Queue(maxsize=1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                code = (params.get("code") or [""])[0]
                state = (params.get("state") or [None])[0]
                try:
                    queue.put_nowait((code, state))
                except Exception:
                    pass
                body = "Authentication completed. You can close this window.".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return cls(port=port, queue=queue, server=server, thread=thread)

    async def wait_for_callback(self, timeout_seconds: float = 300.0) -> tuple[str, str | None]:
        return await anyio.to_thread.run_sync(self.queue.get, True, timeout_seconds)

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class MCPAuthService:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def build_auth(self, server_ref: str, server_url: str) -> tuple[OAuthClientProvider, OAuthCallbackWaiter]:
        waiter = OAuthCallbackWaiter.start()
        storage = FileMCPTokenStorage(self._file_path, server_ref)
        redirect_uri = f"http://127.0.0.1:{waiter.port}/callback"
        metadata = OAuthClientMetadata(
            redirect_uris=[redirect_uri],
            client_name="agentsRoles MCP Manager",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        )

        async def redirect_handler(url: str) -> None:
            webbrowser.open(url)

        async def callback_handler() -> tuple[str, str | None]:
            return await waiter.wait_for_callback()

        provider = OAuthClientProvider(
            server_url=server_url,
            client_metadata=metadata,
            storage=storage,
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
            timeout=300.0,
        )
        return provider, waiter

    async def build_authorized_client(self, server_ref: str, server_url: str) -> tuple[httpx.AsyncClient, OAuthCallbackWaiter]:
        provider, waiter = self.build_auth(server_ref, server_url)
        client = httpx.AsyncClient(auth=provider, timeout=30)
        return client, waiter
