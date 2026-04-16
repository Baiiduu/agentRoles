from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from core.contracts import ExecutionContext, ToolInvocationResult

from .workspace import (
    display_path,
    int_value,
    resolve_path,
    string_value,
    tool_error,
)


_TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".env",
    ".sh",
    ".ps1",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
}

_DEFAULT_SEARCH_LIMIT = 20
_DEFAULT_MAX_FILE_SIZE_KB = 256
_DEFAULT_PATCH_CONTEXT_SEPARATOR = "\n@@\n"


def list_dir_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None or not target.exists():
        return tool_error("FS_PATH_NOT_FOUND", "target directory does not exist")
    if not target.is_dir():
        return tool_error("FS_NOT_A_DIRECTORY", "target path is not a directory")

    items = []
    for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        items.append(
            {
                "path": display_path(child, resolved.root),
                "name": child.name,
                "kind": "directory" if child.is_dir() else "file",
            }
        )
    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(target, resolved.root),
            "items": items,
            "workspace_root": str(resolved.root),
        },
    )


def list_files_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None or not target.exists():
        return tool_error("FS_PATH_NOT_FOUND", "target directory does not exist")
    if not target.is_dir():
        return tool_error("FS_NOT_A_DIRECTORY", "target path is not a directory")

    recursive = bool(tool_input.get("recursive", True))
    limit = max(1, min(int_value(tool_input, "limit") or 200, 2_000))
    extensions = _normalized_extensions(tool_input.get("extensions"))

    iterator = target.rglob("*") if recursive else target.glob("*")
    items: list[dict[str, object]] = []
    for candidate in sorted(iterator, key=lambda item: str(item).lower()):
        if not candidate.is_file():
            continue
        if extensions and candidate.suffix.lower() not in extensions:
            continue
        items.append(
            {
                "path": display_path(candidate, resolved.root),
                "name": candidate.name,
                "extension": candidate.suffix.lower(),
                "size_bytes": candidate.stat().st_size,
            }
        )
        if len(items) >= limit:
            break

    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(target, resolved.root),
            "recursive": recursive,
            "items": items,
            "workspace_root": str(resolved.root),
        },
    )


def read_file_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    loaded = _load_text_file(context, string_value(tool_input, "path"), operation_name="read_file")
    if loaded.error is not None:
        return loaded.error
    assert loaded.path is not None
    return ToolInvocationResult(
        success=True,
        output={
            "path": loaded.display_path,
            "content": loaded.content,
            "line_count": len(loaded.lines),
            "workspace_root": str(loaded.root),
        },
    )


def read_file_segment_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    loaded = _load_text_file(context, string_value(tool_input, "path"), operation_name="read_file_segment")
    if loaded.error is not None:
        return loaded.error
    assert loaded.path is not None

    total_line_count = len(loaded.lines)
    start_line = max(1, int_value(tool_input, "start_line") or 1)
    end_line = int_value(tool_input, "end_line") or min(total_line_count, start_line + 199)
    end_line = min(max(end_line, start_line), total_line_count)

    if total_line_count == 0:
        content = ""
        start_line = 1
        end_line = 0
    else:
        segment_lines = loaded.lines[start_line - 1 : end_line]
        content = "\n".join(segment_lines)

    return ToolInvocationResult(
        success=True,
        output={
            "path": loaded.display_path,
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "total_line_count": total_line_count,
            "workspace_root": str(loaded.root),
        },
    )


def find_in_file_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    pattern = (string_value(tool_input, "pattern") or "").strip()
    if not pattern:
        return tool_error("FS_PATTERN_REQUIRED", "find_in_file requires pattern")

    loaded = _load_text_file(context, string_value(tool_input, "path"), operation_name="find_in_file")
    if loaded.error is not None:
        return loaded.error
    assert loaded.path is not None

    case_sensitive = bool(tool_input.get("case_sensitive", False))
    limit = max(1, min(int_value(tool_input, "limit") or _DEFAULT_SEARCH_LIMIT, 200))
    matches: list[dict[str, object]] = []
    needle = pattern if case_sensitive else pattern.lower()

    for line_number, line in enumerate(loaded.lines, start=1):
        haystack = line if case_sensitive else line.lower()
        if needle not in haystack:
            continue
        matches.append(
            {
                "line_number": line_number,
                "preview": line.strip(),
            }
        )
        if len(matches) >= limit:
            break

    return ToolInvocationResult(
        success=True,
        output={
            "path": loaded.display_path,
            "pattern": pattern,
            "case_sensitive": case_sensitive,
            "matches": matches,
            "workspace_root": str(loaded.root),
        },
    )


def search_files_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    pattern = (string_value(tool_input, "pattern") or "").strip()
    if not pattern:
        return tool_error("FS_PATTERN_REQUIRED", "search_files requires pattern")
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    root = resolved.path
    if root is None or not root.exists():
        return tool_error("FS_PATH_NOT_FOUND", "search root does not exist")
    if not root.is_dir():
        return tool_error("FS_NOT_A_DIRECTORY", "search root must be a directory")

    include_content = bool(tool_input.get("include_content", True))
    limit = max(1, min(int_value(tool_input, "limit") or _DEFAULT_SEARCH_LIMIT, 200))
    matches: list[dict[str, object]] = []
    lowered_pattern = pattern.lower()

    for candidate in root.rglob("*"):
        if len(matches) >= limit:
            break
        relative_path = display_path(candidate, resolved.root)
        if lowered_pattern in candidate.name.lower() or lowered_pattern in relative_path.lower():
            matches.append({"path": relative_path, "match_kind": "path"})
            continue
        if not include_content or not _is_searchable_text_file(candidate):
            continue
        try:
            content = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if lowered_pattern not in content.lower():
            continue
        line_number, preview = _first_matching_line(content.splitlines(), lowered_pattern, case_sensitive=False)
        matches.append(
            {
                "path": relative_path,
                "match_kind": "content",
                "line_number": line_number,
                "preview": preview,
            }
        )

    return ToolInvocationResult(
        success=True,
        output={
            "pattern": pattern,
            "searched_root": display_path(root, resolved.root),
            "matches": matches,
            "workspace_root": str(resolved.root),
        },
    )


def ripgrep_search_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    pattern = (string_value(tool_input, "pattern") or "").strip()
    if not pattern:
        return tool_error("FS_PATTERN_REQUIRED", "ripgrep_search requires pattern")
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    root = resolved.path
    if root is None or not root.exists():
        return tool_error("FS_PATH_NOT_FOUND", "search root does not exist")
    if not root.is_dir():
        return tool_error("FS_NOT_A_DIRECTORY", "search root must be a directory")

    case_sensitive = bool(tool_input.get("case_sensitive", False))
    limit = max(1, min(int_value(tool_input, "limit") or 50, 500))
    max_file_size_kb = max(1, min(int_value(tool_input, "max_file_size_kb") or _DEFAULT_MAX_FILE_SIZE_KB, 2_048))
    glob_pattern = (string_value(tool_input, "glob") or "").strip()
    needle = pattern if case_sensitive else pattern.lower()
    matches: list[dict[str, object]] = []
    truncated = False

    for candidate in root.rglob("*"):
        if len(matches) >= limit:
            truncated = True
            break
        if not candidate.is_file():
            continue
        relative_path = display_path(candidate, resolved.root)
        if glob_pattern and not fnmatch(relative_path, glob_pattern):
            continue

        path_text = relative_path if case_sensitive else relative_path.lower()
        if needle in path_text:
            matches.append({"path": relative_path, "match_kind": "path"})
            continue

        if not _is_searchable_text_file(candidate):
            continue
        try:
            if candidate.stat().st_size > max_file_size_kb * 1024:
                continue
            content = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        lines = content.splitlines()
        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            if needle not in haystack:
                continue
            matches.append(
                {
                    "path": relative_path,
                    "match_kind": "content",
                    "line_number": line_number,
                    "preview": line.strip(),
                }
            )
            if len(matches) >= limit:
                truncated = True
                break

    return ToolInvocationResult(
        success=True,
        output={
            "pattern": pattern,
            "searched_root": display_path(root, resolved.root),
            "glob": glob_pattern,
            "case_sensitive": case_sensitive,
            "matches": matches,
            "truncated": truncated,
            "workspace_root": str(resolved.root),
        },
    )


def write_file_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_path = string_value(tool_input, "path")
    content = string_value(tool_input, "content")
    if not target_path:
        return tool_error("FS_PATH_REQUIRED", "write_file requires path")
    if content is None:
        return tool_error("FS_CONTENT_REQUIRED", "write_file requires content")
    resolved = resolve_path(context, target_path)
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None:
        return tool_error("FS_PATH_REQUIRED", "write_file requires path")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(target, resolved.root),
            "bytes_written": len(content.encode("utf-8")),
            "workspace_root": str(resolved.root),
        },
    )


def apply_patch_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_path = string_value(tool_input, "path")
    patch = string_value(tool_input, "patch")
    if not target_path:
        return tool_error("FS_PATH_REQUIRED", "apply_patch requires path")
    if patch is None or not patch.strip():
        return tool_error("FS_PATCH_REQUIRED", "apply_patch requires patch")

    resolved = resolve_path(context, target_path)
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None:
        return tool_error("FS_PATH_REQUIRED", "apply_patch requires path")

    patch_lines = [line.rstrip("\r") for line in patch.splitlines()]
    if not patch_lines:
        return tool_error("FS_PATCH_REQUIRED", "apply_patch requires patch")

    operation = patch_lines[0].strip().lower()
    if operation == "*** add":
        if target.exists():
            return tool_error("FS_PATCH_TARGET_EXISTS", "cannot add a file that already exists")
        content = "\n".join(patch_lines[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolInvocationResult(
            success=True,
            output={
                "path": display_path(target, resolved.root),
                "applied": True,
                "change_count": 1,
                "workspace_root": str(resolved.root),
            },
        )

    if operation == "*** delete":
        if not target.exists():
            return tool_error("FS_PATH_NOT_FOUND", "target file does not exist")
        if not target.is_file():
            return tool_error("FS_NOT_A_FILE", "apply_patch delete requires a file path")
        target.unlink()
        return ToolInvocationResult(
            success=True,
            output={
                "path": display_path(target, resolved.root),
                "applied": True,
                "change_count": 1,
                "workspace_root": str(resolved.root),
            },
        )

    loaded = _load_text_file(context, target_path, operation_name="apply_patch", allow_missing=False)
    if loaded.error is not None:
        return loaded.error
    assert loaded.path is not None

    if operation != "*** replace":
        return tool_error(
            "FS_PATCH_INVALID",
            "apply_patch patch must start with '*** add', '*** delete', or '*** replace'",
        )

    body = "\n".join(patch_lines[1:])
    if _DEFAULT_PATCH_CONTEXT_SEPARATOR not in body:
        return tool_error(
            "FS_PATCH_INVALID",
            "replace patch must contain an old/new section separated by '\\n@@\\n'",
        )
    old_text, new_text = body.split(_DEFAULT_PATCH_CONTEXT_SEPARATOR, 1)
    if old_text not in loaded.content:
        return tool_error("FS_PATCH_CONTEXT_NOT_FOUND", "old patch content was not found in file")

    updated_content = loaded.content.replace(old_text, new_text, 1)
    loaded.path.write_text(updated_content, encoding="utf-8")
    return ToolInvocationResult(
        success=True,
        output={
            "path": loaded.display_path,
            "applied": True,
            "change_count": 1,
            "workspace_root": str(loaded.root),
        },
    )


def make_dir_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_path = string_value(tool_input, "path")
    if not target_path:
        return tool_error("FS_PATH_REQUIRED", "make_dir requires path")
    resolved = resolve_path(context, target_path)
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None:
        return tool_error("FS_PATH_REQUIRED", "make_dir requires path")
    target.mkdir(parents=True, exist_ok=True)
    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(target, resolved.root),
            "workspace_root": str(resolved.root),
        },
    )


def delete_file_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    target_path = string_value(tool_input, "path")
    if not target_path:
        return tool_error("FS_PATH_REQUIRED", "delete_file requires path")
    resolved = resolve_path(context, target_path)
    if resolved.error is not None:
        return resolved.error
    target = resolved.path
    if target is None or not target.exists():
        return tool_error("FS_PATH_NOT_FOUND", "target file does not exist")
    if not target.is_file():
        return tool_error("FS_NOT_A_FILE", "delete_file requires a file path")
    target.unlink()
    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(target, resolved.root),
            "deleted": True,
            "workspace_root": str(resolved.root),
        },
    )


def move_file_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    source_path = string_value(tool_input, "source_path")
    destination_path = string_value(tool_input, "destination_path")
    if not source_path or not destination_path:
        return tool_error(
            "FS_MOVE_PATH_REQUIRED",
            "move_file requires source_path and destination_path",
        )
    source_resolved = resolve_path(context, source_path)
    if source_resolved.error is not None:
        return source_resolved.error
    destination_resolved = resolve_path(context, destination_path)
    if destination_resolved.error is not None:
        return destination_resolved.error
    source = source_resolved.path
    destination = destination_resolved.path
    if source is None or not source.exists():
        return tool_error("FS_PATH_NOT_FOUND", "source file does not exist")
    if not source.is_file():
        return tool_error("FS_NOT_A_FILE", "move_file requires a file source")
    if destination is None:
        return tool_error(
            "FS_MOVE_PATH_REQUIRED",
            "move_file requires destination_path",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return ToolInvocationResult(
        success=True,
        output={
            "source_path": display_path(source, source_resolved.root),
            "destination_path": display_path(destination, destination_resolved.root),
            "workspace_root": str(source_resolved.root),
        },
    )


class _LoadedTextFile:
    def __init__(
        self,
        *,
        root: Path,
        path: Path | None,
        display_path: str,
        content: str,
        lines: list[str],
        error: ToolInvocationResult | None = None,
    ) -> None:
        self.root = root
        self.path = path
        self.display_path = display_path
        self.content = content
        self.lines = lines
        self.error = error


def _load_text_file(
    context: ExecutionContext,
    raw_path: str | None,
    *,
    operation_name: str,
    allow_missing: bool = False,
) -> _LoadedTextFile:
    if not raw_path:
        return _LoadedTextFile(
            root=Path("."),
            path=None,
            display_path="",
            content="",
            lines=[],
            error=tool_error("FS_PATH_REQUIRED", f"{operation_name} requires path"),
        )
    resolved = resolve_path(context, raw_path)
    if resolved.error is not None:
        return _LoadedTextFile(
            root=resolved.root,
            path=None,
            display_path="",
            content="",
            lines=[],
            error=resolved.error,
        )
    target = resolved.path
    if target is None:
        return _LoadedTextFile(
            root=resolved.root,
            path=None,
            display_path="",
            content="",
            lines=[],
            error=tool_error("FS_PATH_REQUIRED", f"{operation_name} requires path"),
        )
    if not target.exists():
        if allow_missing:
            return _LoadedTextFile(
                root=resolved.root,
                path=target,
                display_path=display_path(target, resolved.root),
                content="",
                lines=[],
            )
        return _LoadedTextFile(
            root=resolved.root,
            path=None,
            display_path="",
            content="",
            lines=[],
            error=tool_error("FS_PATH_NOT_FOUND", "target file does not exist"),
        )
    if not target.is_file():
        return _LoadedTextFile(
            root=resolved.root,
            path=None,
            display_path="",
            content="",
            lines=[],
            error=tool_error("FS_NOT_A_FILE", "target path is not a file"),
        )
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _LoadedTextFile(
            root=resolved.root,
            path=None,
            display_path="",
            content="",
            lines=[],
            error=tool_error("FS_BINARY_FILE", f"{operation_name} only supports utf-8 text files"),
        )
    return _LoadedTextFile(
        root=resolved.root,
        path=target,
        display_path=display_path(target, resolved.root),
        content=content,
        lines=content.splitlines(),
    )


def _normalized_extensions(raw_extensions: object) -> set[str]:
    if not isinstance(raw_extensions, list):
        return set()
    normalized: set[str] = set()
    for value in raw_extensions:
        if not isinstance(value, str):
            continue
        extension = value.strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = f".{extension}"
        normalized.add(extension)
    return normalized


def _is_searchable_text_file(candidate: Path) -> bool:
    return candidate.is_file() and candidate.suffix.lower() in _TEXT_EXTENSIONS


def _first_matching_line(
    lines: list[str],
    pattern: str,
    *,
    case_sensitive: bool,
) -> tuple[int | None, str]:
    needle = pattern if case_sensitive else pattern.lower()
    for index, line in enumerate(lines, start=1):
        haystack = line if case_sensitive else line.lower()
        if needle in haystack:
            return index, line.strip()
    return None, ""
