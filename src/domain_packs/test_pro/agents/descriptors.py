from __future__ import annotations

from copy import deepcopy

from core.agents import AgentDescriptor
from domain_packs.operations import OPERATION_TOOL_REFS


_TEST_PRO_AGENT_DESCRIPTORS = [
    AgentDescriptor(
        agent_id="test_pro_chat",
        name="Test Pro Chat",
        version="0.1.0",
        role="tester",
        description=(
            "A minimal sandbox agent for prompt testing, response tuning, and "
            "fine-grained behavior experiments."
        ),
        executor_ref="agent.domain",
        implementation_ref="test_pro.chat",
        domain="test_pro",
        tags=["test", "sandbox", "chat", "agentic"],
        tool_refs=[
            OPERATION_TOOL_REFS["list_dir"],
            OPERATION_TOOL_REFS["list_files"],
            OPERATION_TOOL_REFS["read_file"],
            OPERATION_TOOL_REFS["read_file_segment"],
            OPERATION_TOOL_REFS["find_in_file"],
            OPERATION_TOOL_REFS["search_files"],
            OPERATION_TOOL_REFS["ripgrep_search"],
            OPERATION_TOOL_REFS["write_file"],
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
            "plain_chat",
            "prompt_tuning",
            "behavior_testing",
            "filesystem_navigation",
            "filesystem_mutation",
            "shell_execution",
            "tool_orchestration",
            "git_inspection",
            "mcp_orchestration",
        ],
        input_contract={
            "type": "test_pro_chat_input",
            "required_fields": ["message"],
        },
        output_contract={
            "type": "test_pro_chat_output",
            "produces": ["reply", "summary", "mode", "decision", "execution_trace", "tool_context"],
        },
        metadata={
            "stage": "sandbox",
            "writes_memory": False,
            "llm_profile_ref": "deepseek.default",
            "system_prompt": (
                "You are Test Pro Chat, an experimental workspace agent for repository "
                "inspection, lightweight coding assistance, and tool-driven task execution.\n\n"
                "Your job is to help the user complete concrete tasks inside the allowed "
                "workspace. You may inspect files, search the codebase, check git state, and "
                "run assigned tools when they are useful.\n\n"
                "Operate with these priorities:\n"
                "1. Understand the user task before acting.\n"
                "2. Prefer direct answers when no tool is needed.\n"
                "3. Use assigned tools when they improve accuracy, verification, or task completion.\n"
                "4. Treat assigned MCP tools as first-class tools, but prefer local repository tools for local code and file work.\n"
                "5. Keep tool use purposeful and avoid redundant repeated calls.\n"
                "6. Stay inside the allowed workspace and never assume access beyond assigned tools.\n"
                "7. When enough evidence has been gathered, stop using tools and answer clearly.\n\n"
                "Behavior rules:\n"
                "- Be concise, concrete, and execution-oriented.\n"
                "- Do not invent tools, files, results, or hidden capabilities.\n"
                "- If a tool fails, explain the limitation and choose the next best step.\n"
                "- If the task is ambiguous but still actionable, make a reasonable assumption and proceed.\n"
                "- When giving a final answer, summarize what you found, what you changed or observed, "
                "and any remaining uncertainty."
            ),
            "instruction_appendix": (
                "Prefer concise answers unless the user explicitly asks for detail. "
                "Use assigned tools when they materially improve accuracy or verification. "
                "Avoid unnecessary tool loops. "
                "Do not invent tools or hidden capabilities."
            ),
            "response_style": "agentic_sandbox",
            "quality_bar": "Be predictable, tool-aware, and easy to compare across test runs.",
        },
    )
]


def get_test_pro_agent_descriptors() -> list[AgentDescriptor]:
    return [deepcopy(descriptor) for descriptor in _TEST_PRO_AGENT_DESCRIPTORS]
