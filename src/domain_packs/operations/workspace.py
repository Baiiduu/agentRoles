from __future__ import annotations

import locale
from pathlib import Path

from core.contracts import ExecutionContext, ToolInvocationResult


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ResolvedPath:
    def __init__(
        self,
        *,
        root: Path,
        path: Path | None,
        error: ToolInvocationResult | None = None,
    ) -> None:
        self.root = root
        self.path = path
        self.error = error


def resolve_path(context: ExecutionContext, raw_path: str | None) -> ResolvedPath:
    root = workspace_root(context)
    candidate = (raw_path or ".").strip()
    target = (root / candidate).resolve() if not Path(candidate).is_absolute() else Path(candidate).resolve()
    if not is_within_root(target, root):
        return ResolvedPath(
            root=root,
            path=None,
            error=tool_error(
                "FS_PATH_OUTSIDE_ROOT",
                "path must stay within the allowed workspace root",
            ),
        )
    return ResolvedPath(root=root, path=target)


def workspace_root(context: ExecutionContext) -> Path:
    binding = context.agent_binding
    runtime_resource_context = binding.metadata.get("runtime_resource_context", {}) if binding else {}
    if isinstance(runtime_resource_context, dict):
        workspace = runtime_resource_context.get("workspace")
        if isinstance(workspace, dict):
            absolute_path = workspace.get("absolute_path")
            if isinstance(absolute_path, str) and absolute_path.strip():
                return Path(absolute_path).resolve()
    return PROJECT_ROOT


def is_within_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/") or "."
    except ValueError:
        return str(path)


def string_value(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def int_value(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def decode_process_output(data: bytes) -> str:
    if not data:
        return ""

    candidate_encodings: list[str] = ["utf-8-sig"]
    preferred_encoding = locale.getpreferredencoding(False)
    if preferred_encoding:
        candidate_encodings.append(preferred_encoding)
    candidate_encodings.extend(["gbk", "cp936", "utf-16-le", "utf-16-be"])

    tried: set[str] = set()
    for encoding in candidate_encodings:
        normalized = encoding.lower()
        if normalized in tried:
            continue
        tried.add(normalized)
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def tool_error(error_code: str, error_message: str) -> ToolInvocationResult:
    return ToolInvocationResult(
        success=False,
        error_code=error_code,
        error_message=error_message,
    )
