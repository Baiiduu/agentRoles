from __future__ import annotations

from copy import deepcopy

from core.agents import AgentDescriptor
from domain_packs.operations import OPERATION_TOOL_REFS


_TEST_PRO_AGENT_DESCRIPTORS = [
    AgentDescriptor(
        agent_id="test_pro_chat",
        name="Test Pro Coding Agent",
        version="0.1.0",
        role="coding_assistant",
        description=(
            "A single-agent coding assistant for repository understanding, focused "
            "code changes, tool-guided verification, and concise developer reporting."
        ),
        executor_ref="agent.domain",
        implementation_ref="test_pro.chat",
        domain="test_pro",
        tags=["coding", "repository", "developer-tools", "agentic"],
        tool_refs=[
            OPERATION_TOOL_REFS["list_dir"],
            OPERATION_TOOL_REFS["list_files"],
            OPERATION_TOOL_REFS["read_file"],
            OPERATION_TOOL_REFS["read_file_segment"],
            OPERATION_TOOL_REFS["symbol_outline"],
            OPERATION_TOOL_REFS["symbol_search"],
            OPERATION_TOOL_REFS["lookup_definition"],
            OPERATION_TOOL_REFS["find_references"],
            OPERATION_TOOL_REFS["find_in_file"],
            OPERATION_TOOL_REFS["search_files"],
            OPERATION_TOOL_REFS["ripgrep_search"],
            OPERATION_TOOL_REFS["write_file"],
            OPERATION_TOOL_REFS["preview_structured_edit"],
            OPERATION_TOOL_REFS["replace_in_file"],
            OPERATION_TOOL_REFS["insert_in_file"],
            OPERATION_TOOL_REFS["apply_patch"],
            OPERATION_TOOL_REFS["make_dir"],
            OPERATION_TOOL_REFS["delete_file"],
            OPERATION_TOOL_REFS["move_file"],
            OPERATION_TOOL_REFS["shell_run"],
            OPERATION_TOOL_REFS["git_status"],
            OPERATION_TOOL_REFS["git_diff"],
        ],
        memory_scopes=["domain:test_pro", "session:test_pro:{thread_id}"],
        policy_profiles=[],
        capabilities=[
            "repository_understanding",
            "code_navigation",
            "symbol_navigation",
            "targeted_code_editing",
            "patch_planning",
            "verification_guidance",
            "filesystem_navigation",
            "filesystem_mutation",
            "shell_execution",
            "tool_orchestration",
            "git_awareness",
            "mcp_orchestration",
        ],
        input_contract={
            "type": "test_pro_chat_input",
            "required_fields": ["message"],
            "optional_fields": [
                "conversation_history",
                "task_goal",
                "acceptance_criteria",
                "changed_files_hint",
                "verification_mode",
                "workspace_context",
            ],
        },
        output_contract={
            "type": "test_pro_chat_output",
            "produces": [
                "reply",
                "summary",
                "mode",
                "decision",
                "execution_trace",
                "tool_context",
                "loop_stop_reason",
                "llm_context",
                "normalized_input",
                "memory_context",
                "recommended_memory_scope",
                "task_memory",
                "current_phase",
                "working_summary",
                "task_state",
                "validation_plan",
            ],
        },
        metadata={
            "stage": "coding_agent",
            "writes_memory": True,
            "llm_profile_ref": "deepseek.default",
            "system_prompt": (
                "You are Test Pro Coding Agent, a repository-aware coding assistant for "
                "understanding code, making focused changes, and reporting results clearly.\n\n"
                "Your job is to help the user complete concrete coding tasks inside the "
                "allowed workspace. You may inspect files, search the codebase, review git "
                "state, edit files, and use assigned tools when they improve accuracy or "
                "execution quality.\n\n"
                "Operate with these priorities:\n"
                "1. Understand the user task before acting.\n"
                "2. Gather the minimum context needed before proposing or applying edits.\n"
                "3. Prefer assigned repository tools over shell when a specific tool can do the job.\n"
                "4. Use assigned tools when they improve accuracy, verification, or task completion.\n"
                "5. Treat assigned MCP tools as first-class tools, but prefer local repository tools for local code and file work.\n"
                "6. Keep tool use purposeful and avoid redundant repeated calls.\n"
                "7. After changes, explain how the work should be validated or what validation already happened.\n"
                "8. Stay inside the allowed workspace and never assume access beyond assigned tools.\n"
                "9. When enough evidence has been gathered, stop using tools and answer clearly.\n\n"
                "Behavior rules:\n"
                "- Be concise, concrete, and execution-oriented.\n"
                "- Do not invent tools, files, results, or hidden capabilities.\n"
                "- If a tool fails, explain the limitation and choose the next best step.\n"
                "- If the task is ambiguous but still actionable, make a reasonable assumption and proceed.\n"
                "- For edit requests, avoid patching until you have enough local context.\n"
                "- When giving a final answer, summarize what you found, what you changed or observed, "
                "how to validate it, and any remaining uncertainty."
            ),
            "instruction_appendix": (
                "Prefer concise answers unless the user explicitly asks for detail. "
                "Use assigned tools when they materially improve accuracy or verification. "
                "Prefer read/search/git/patch tools over shell whenever possible. "
                "Avoid unnecessary tool loops. "
                "Do not invent tools or hidden capabilities. "
                "Keep the final response useful for a developer who wants to act on the result."
            ),
            "response_style": "developer_coding_assistant",
            "quality_bar": (
                "Be predictable, repository-aware, tool-disciplined, and clear about "
                "changes, evidence, validation, and uncertainty."
            ),
        },
    )
]


def get_test_pro_agent_descriptors() -> list[AgentDescriptor]:
    return [deepcopy(descriptor) for descriptor in _TEST_PRO_AGENT_DESCRIPTORS]
