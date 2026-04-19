from __future__ import annotations

from core.tools import FunctionToolAdapter

from .constants import OPERATION_TOOL_REFS
from .filesystem import (
    apply_patch_handler,
    delete_file_handler,
    find_in_file_handler,
    find_references_handler,
    list_dir_handler,
    list_files_handler,
    lookup_definition_handler,
    make_dir_handler,
    move_file_handler,
    read_file_handler,
    read_file_segment_handler,
    ripgrep_search_handler,
    search_files_handler,
    symbol_outline_handler,
    symbol_search_handler,
    write_file_handler,
)
from .git_tools import git_diff_handler, git_status_handler
from .shell import shell_run_handler


def build_operations_function_tool_adapter() -> FunctionToolAdapter:
    adapter = FunctionToolAdapter()
    register_operation_tool_handlers(adapter)
    return adapter


def register_operation_tool_handlers(adapter: FunctionToolAdapter) -> None:
    adapter.register_handler(OPERATION_TOOL_REFS["list_dir"], list_dir_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["list_files"], list_files_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["read_file"], read_file_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["read_file_segment"], read_file_segment_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["symbol_outline"], symbol_outline_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["symbol_search"], symbol_search_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["lookup_definition"], lookup_definition_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["find_references"], find_references_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["find_in_file"], find_in_file_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["search_files"], search_files_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["ripgrep_search"], ripgrep_search_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["write_file"], write_file_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["apply_patch"], apply_patch_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["make_dir"], make_dir_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["delete_file"], delete_file_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["move_file"], move_file_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["shell_run"], shell_run_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["git_status"], git_status_handler)
    adapter.register_handler(OPERATION_TOOL_REFS["git_diff"], git_diff_handler)
