from __future__ import annotations

import subprocess

from core.contracts import ExecutionContext, ToolInvocationResult

from .workspace import (
    decode_process_output,
    display_path,
    int_value,
    resolve_path,
    string_value,
    tool_error,
)


def shell_run_handler(
    tool_input: dict[str, object],
    context: ExecutionContext,
) -> ToolInvocationResult:
    command = (string_value(tool_input, "command") or "").strip()
    if not command:
        return tool_error("SHELL_COMMAND_REQUIRED", "shell.run requires command")
    resolved = resolve_path(context, string_value(tool_input, "workdir"))
    if resolved.error is not None:
        return resolved.error
    workdir = resolved.path
    if workdir is None or not workdir.exists():
        return tool_error("SHELL_WORKDIR_NOT_FOUND", "shell workdir does not exist")
    if not workdir.is_dir():
        return tool_error("SHELL_WORKDIR_INVALID", "shell workdir must be a directory")

    timeout_ms = int_value(tool_input, "timeout_ms") or 15_000
    wrapped_command = (
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
        "$OutputEncoding = [Console]::OutputEncoding; "
        f"{command}"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", wrapped_command],
            cwd=str(workdir),
            capture_output=True,
            timeout=max(timeout_ms / 1000, 1),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return tool_error("SHELL_TIMEOUT", "shell command timed out")
    except OSError as exc:
        return tool_error("SHELL_EXECUTION_FAILED", str(exc))

    return ToolInvocationResult(
        success=True,
        output={
            "command": command,
            "workdir": display_path(workdir, resolved.root),
            "stdout": decode_process_output(completed.stdout),
            "stderr": decode_process_output(completed.stderr),
            "exit_code": completed.returncode,
            "workspace_root": str(resolved.root),
        },
    )
