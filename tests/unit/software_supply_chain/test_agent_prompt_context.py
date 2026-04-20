from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents.bindings import ResolvedAgentBinding
from core.contracts import ExecutionContext, RuntimeServices
from core.llm import LLMResult
from core.state.models import NodeState, NodeStatus, NodeType, RunRecord, RunStatus, RunState, ThreadRecord, ThreadState
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec, OutputBinding
from domain_packs.software_supply_chain import SoftwareSupplyChainDomainPack
from domain_packs.software_supply_chain.agents.implementations import DependencyAuditorImplementation
from domain_packs.software_supply_chain.agents.shared_impl.shared import _normalize_input


def _literal_selector(value: str) -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class _FakeLLMInvoker:
    def __init__(self, results: list[LLMResult]) -> None:
        self._results = list(results)
        self.requests = []

    def invoke(self, request, context=None):
        self.requests.append(request)
        if not self._results:
            raise AssertionError("unexpected extra llm invoke")
        return self._results.pop(0)


def _build_context(
    *,
    message: str,
    selected_input: dict[str, object] | None = None,
    llm_invoker=None,
) -> ExecutionContext:
    descriptor = SoftwareSupplyChainDomainPack.get_agent_descriptors()[0]
    binding = ResolvedAgentBinding(
        node_id="agent",
        agent_ref=descriptor.agent_id,
        resolved_agent_id=descriptor.agent_id,
        resolved_version=descriptor.version,
        executor_ref=descriptor.executor_ref,
        implementation_ref=descriptor.implementation_ref,
        tool_refs=list(descriptor.tool_refs),
        memory_scopes=list(descriptor.memory_scopes),
        policy_profiles=list(descriptor.policy_profiles),
        capabilities=list(descriptor.capabilities),
        metadata=dict(descriptor.metadata),
    )
    node_spec = NodeSpec(
        node_id="agent",
        node_type=NodeType.AGENT,
        executor_ref="agent.domain",
        agent_ref=descriptor.agent_id,
        input_selector=_literal_selector(message or "__empty__"),
        output_binding=OutputBinding(artifact_type="software_supply_chain.chat_output"),
    )
    workflow = CompiledWorkflow(
        workflow_id="wf.software_supply_chain.invoke",
        version="1.0.0",
        entry_node_id="agent",
        node_map={"agent": node_spec},
        outgoing_edges={"agent": []},
        incoming_edges={"agent": []},
    )
    payload = {"message": message}
    if selected_input:
        payload.update(selected_input)
    return ExecutionContext(
        thread_record=ThreadRecord(thread_id="thread-ssc-1", thread_type="task"),
        run_record=RunRecord(
            run_id="run-ssc-1",
            thread_id="thread-ssc-1",
            workflow_id="wf.software_supply_chain.invoke",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
            entry_node_id="agent",
        ),
        thread_state=ThreadState(thread_id="thread-ssc-1", goal="test supply chain invoke"),
        run_state=RunState(
            run_id="run-ssc-1",
            thread_id="thread-ssc-1",
            workflow_id="wf.software_supply_chain.invoke",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
        ),
        node_state=NodeState(
            run_id="run-ssc-1",
            node_id="agent",
            node_type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            started_at=ThreadRecord(thread_id="tmp", thread_type="tmp").created_at,
            executor_ref="agent.domain",
        ),
        workflow=workflow,
        node_spec=node_spec,
        agent_binding=binding,
        selected_input=payload,
        services=RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            llm_invoker=llm_invoker,
        ),
    )


class SoftwareSupplyChainAgentPromptContextTestCase(unittest.TestCase):
    def test_normalize_input_extracts_current_and_saved_github_links(self) -> None:
        context = _build_context(
            message="帮我分析这个仓库的依赖风险",
            selected_input={
                "github_repository": "https://github.com/acme/semgrep-clone",
                "software_supply_chain_context": {
                    "current_repo_url": "https://github.com/acme/semgrep-clone",
                    "saved_repo_urls": [
                        "https://github.com/acme/semgrep-clone",
                        "https://github.com/acme/shared-security-lib",
                    ],
                },
            },
        )

        normalized = _normalize_input(context)

        self.assertEqual(
            normalized.current_repo_url,
            "https://github.com/acme/semgrep-clone",
        )
        self.assertEqual(
            normalized.saved_repo_urls,
            [
                "https://github.com/acme/semgrep-clone",
                "https://github.com/acme/shared-security-lib",
            ],
        )
        self.assertEqual(
            normalized.task_memory["current_repo_url"],
            "https://github.com/acme/semgrep-clone",
        )
        self.assertIn(
            "Active repository target: https://github.com/acme/semgrep-clone",
            normalized.system_prompt,
        )

    def test_invoke_includes_repository_context_in_llm_payload(self) -> None:
        llm = _FakeLLMInvoker(
            [
                LLMResult(
                    success=True,
                    provider_ref="test",
                    model_name="fake-model",
                    output_json={
                        "decision_type": "respond",
                        "reply": "我已经结合当前 GitHub 仓库目标完成了初步依赖审计判断。",
                        "reasoning_summary": "当前问题可以先直接总结。",
                        "should_use_tools": False,
                        "suggested_tool_ref": "",
                        "suggested_tool_input": {},
                        "task_kind": "audit",
                        "next_step": "输出和当前仓库绑定的审计结论。",
                    },
                )
            ]
        )
        context = _build_context(
            message="围绕当前 GitHub 仓库给我做一次依赖审计",
            selected_input={
                "github_repository": "https://github.com/acme/semgrep-clone",
                "software_supply_chain_context": {
                    "current_repo_url": "https://github.com/acme/semgrep-clone",
                    "saved_repo_urls": [
                        "https://github.com/acme/semgrep-clone",
                        "https://github.com/acme/shared-security-lib",
                    ],
                },
            },
            llm_invoker=llm,
        )

        result = DependencyAuditorImplementation().invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertTrue(llm.requests)
        request = llm.requests[0]
        payload = json.loads(request.messages[0].content)
        self.assertEqual(
            payload["github_context"]["current_repo_url"],
            "https://github.com/acme/semgrep-clone",
        )
        self.assertIn(
            "https://github.com/acme/shared-security-lib",
            payload["github_context"]["saved_repo_urls"],
        )
        self.assertIn(
            "Active repository target: https://github.com/acme/semgrep-clone",
            request.system_prompt,
        )
        self.assertEqual(
            result.output["task_state"]["current_repo_url"],
            "https://github.com/acme/semgrep-clone",
        )
        self.assertEqual(
            result.output["normalized_input"]["current_repo_url"],
            "https://github.com/acme/semgrep-clone",
        )
        self.assertEqual(
            result.output["task_memory"]["current_repo_url"],
            "https://github.com/acme/semgrep-clone",
        )

    def test_invoke_includes_active_skill_prompt_in_system_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_file = Path(temp_dir) / "SKILL.md"
            prompt_file.write_text(
                """
---
name: Dependency Audit
description: Review dependency risk carefully.
---

# Dependency Audit

Inspect dependency manifests before making a recommendation.

Ask for confirmation before publishing an externally visible dependency verdict.
                """.strip(),
                encoding="utf-8",
            )
            llm = _FakeLLMInvoker(
                [
                    LLMResult(
                        success=True,
                        provider_ref="test",
                        model_name="fake-model",
                        output_json={
                            "decision_type": "respond",
                            "reply": "我已经根据技能要求完成了依赖审计建议。",
                            "reasoning_summary": "结合技能说明整理了审计结论。",
                            "should_use_tools": False,
                            "suggested_tool_ref": "",
                            "suggested_tool_input": {},
                            "task_kind": "audit",
                            "next_step": "输出结论",
                        },
                    )
                ]
            )
            context = _build_context(
                message="请帮我做一次 dependency audit",
                llm_invoker=llm,
            )
            context.agent_binding.metadata["runtime_resource_context"] = {
                "skills": [
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "description": "Review dependency risk carefully.",
                        "prompt_file": str(prompt_file),
                    }
                ],
                "skill_packages": [
                    {
                        "skill_name": "dependency-audit",
                        "name": "Dependency Audit",
                        "description": "Review dependency risk carefully.",
                        "trigger_kinds": ["dependency", "audit"],
                        "execution_mode": "human_confirmed",
                        "scope": "session",
                        "usage_notes": "Use for package review tasks.",
                        "prompt_summary": "Inspect manifests before making a recommendation.",
                        "prompt_body": "Inspect dependency manifests before making a recommendation.\nAsk for confirmation before publishing an externally visible dependency verdict.",
                    }
                ],
            }

            result = DependencyAuditorImplementation().invoke(context)

            self.assertEqual(result.status, NodeStatus.SUCCEEDED)
            self.assertTrue(llm.requests)
            request = llm.requests[0]
            self.assertIn(
                "Active skills for this request:",
                request.system_prompt,
            )
            self.assertIn(
                "Inspect dependency manifests before making a recommendation.",
                request.system_prompt,
            )
            self.assertIn(
                "human_confirmed = ask before irreversible or externally visible actions",
                request.system_prompt,
            )

    def test_skill_inventory_request_returns_assigned_skill_packages_directly(self) -> None:
        context = _build_context(
            message="现在你有哪些skills能看到",
            llm_invoker=None,
        )
        context.agent_binding.metadata["runtime_resource_context"] = {
            "skill_packages": [
                {
                    "skill_name": "dependency-audit",
                    "name": "Dependency Audit",
                    "description": "Review dependency risk carefully.",
                    "trigger_kinds": ["dependency", "audit"],
                    "execution_mode": "human_confirmed",
                },
                {
                    "skill_name": "sbom-helper",
                    "name": "SBOM Helper",
                    "description": "Work with SBOM data.",
                    "trigger_kinds": ["sbom"],
                    "execution_mode": "advisory",
                },
            ]
        }

        result = DependencyAuditorImplementation().invoke(context)

        self.assertEqual(result.status, NodeStatus.SUCCEEDED)
        self.assertEqual(result.output["mode"], "skill_inventory")
        self.assertIn("Dependency Audit [dependency-audit]", result.output["reply"])
        self.assertIn("SBOM Helper [sbom-helper]", result.output["reply"])
        self.assertIn("当前分配给我的 skills 如下：", result.output["reply"])


if __name__ == "__main__":
    unittest.main()
