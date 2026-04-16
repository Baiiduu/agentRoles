from __future__ import annotations

import subprocess

from core.contracts import ExecutionContext, ToolInvocationResult

from .workspace import (
    decode_process_output,
    display_path,
    resolve_path,
    string_value,
    tool_error,
)


def git_status_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    workdir = resolved.path
    if workdir is None or not workdir.exists():
        return tool_error("GIT_PATH_NOT_FOUND", "git status path does not exist")
    if not workdir.is_dir():
        return tool_error("GIT_PATH_INVALID", "git status path must be a directory")

    branch_result = _run_git_command(["branch", "--show-current"], workdir)
    if branch_result["error"] is not None:
        return branch_result["error"]
    status_result = _run_git_command(["status", "--short"], workdir)
    if status_result["error"] is not None:
        return status_result["error"]

    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(workdir, resolved.root),
            "branch": branch_result["stdout"].strip(),
            "status_lines": [line for line in status_result["stdout"].splitlines() if line.strip()],
            "workspace_root": str(resolved.root),
        },
    )


def git_diff_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    resolved = resolve_path(context, string_value(tool_input, "path"))
    if resolved.error is not None:
        return resolved.error
    workdir = resolved.path
    if workdir is None or not workdir.exists():
        return tool_error("GIT_PATH_NOT_FOUND", "git diff path does not exist")
    if not workdir.is_dir():
        return tool_error("GIT_PATH_INVALID", "git diff path must be a directory")

    target = (string_value(tool_input, "target") or "").strip()
    args = ["diff"]
    if target:
        args.extend(["--", target])
    result = _run_git_command(args, workdir)
    if result["error"] is not None:
        return result["error"]
    return ToolInvocationResult(
        success=True,
        output={
            "path": display_path(workdir, resolved.root),
            "target": target,
            "diff": result["stdout"],
            "workspace_root": str(resolved.root),
        },
    )


def _run_git_command(args: list[str], workdir) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(workdir),
            capture_output=True,
            timeout=5,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": tool_error("GIT_TIMEOUT", "git command timed out"), "stdout": ""}
    except OSError as exc:
        return {"error": tool_error("GIT_EXECUTION_FAILED", str(exc)), "stdout": ""}
    stdout = decode_process_output(completed.stdout)
    stderr = decode_process_output(completed.stderr)
    if completed.returncode != 0:
        return {
            "error": tool_error(
                "GIT_COMMAND_FAILED",
                stderr.strip() or "git command failed",
            ),
            "stdout": stdout,
        }
    return {"error": None, "stdout": stdout}
