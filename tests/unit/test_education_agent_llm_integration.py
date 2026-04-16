from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents import InMemoryAgentRegistry, RegistryBackedAgentBindingResolver
from core.contracts import RuntimeServices
from core.executors import BasicNodeExecutor, DomainAgentExecutor
from core.llm import LLMResult
from core.runtime import RuntimeService
from core.state.models import NodeType, RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.workflow import InMemoryWorkflowProvider
from core.workflow.workflow_models import (
    EdgeSpec,
    InputSelector,
    InputSource,
    InputSourceType,
    NodeSpec,
    OutputBinding,
    WorkflowDefinition,
)
from domain_packs.education import EducationDomainPack


class _FakeEducationLLMInvoker:
    def invoke(self, request, context=None):
        profile_ref = request.profile_ref
        if profile_ref == "education.curriculum_planner.default":
            return LLMResult(
                success=True,
                provider_ref="deepseek",
                model_name="deepseek-chat",
                output_json={
                    "goal": "fractions mastery",
                    "focus_areas": ["equivalent fractions", "fraction addition"],
                    "prerequisites": ["number sense"],
                    "milestones": [
                        {
                            "stage": 1,
                            "focus": "equivalent fractions",
                            "objective": "build visual intuition",
                        },
                        {
                            "stage": 2,
                            "focus": "fraction addition",
                            "objective": "apply a common denominator",
                        },
                    ],
                    "unit_sequence": ["equivalent fractions", "fraction addition"],
                    "remediation_needed": True,
                },
            )
        if profile_ref == "education.tutor_coach.default":
            return LLMResult(
                success=True,
                provider_ref="deepseek",
                model_name="deepseek-chat",
                output_json={
                    "explanation": "You are strengthening fractions by connecting models to symbols.",
                    "encouragement": "That is solid progress. Keep your steps precise.",
                    "next_steps": ["review equivalent fractions", "complete one guided addition problem"],
                    "tone": "warm_structured",
                },
            )
        return LLMResult(
            success=False,
            provider_ref="deepseek",
            model_name="deepseek-chat",
            error_code="LLM_PROFILE_NOT_FOUND",
            error_message="unknown test profile",
        )


def _build_llm_runtime() -> tuple[RuntimeService, RuntimeServices]:
    registry = InMemoryAgentRegistry()
    for descriptor in EducationDomainPack.get_agent_descriptors():
        registry.register(descriptor)

    workflow_provider = InMemoryWorkflowProvider()
    workflow_provider.register(
        WorkflowDefinition(
            workflow_id="wf.education.llm.path",
            name="Education LLM Path",
            version="1.0.0",
            entry_node_id="profile",
            node_specs=[
                NodeSpec(
                    node_id="profile",
                    node_type=NodeType.AGENT,
                    executor_ref="agent.domain",
                    agent_ref="learner_profiler",
                    input_selector=InputSelector(
                        sources=[
                            InputSource(
                                InputSourceType.THREAD_STATE,
                                "thread_context",
                                path="global_context",
                            )
                        ]
                    ),
                    output_binding=OutputBinding(artifact_type="education.learner_profile"),
                ),
                NodeSpec(
                    node_id="plan",
                    node_type=NodeType.AGENT,
                    executor_ref="agent.domain",
                    agent_ref="curriculum_planner",
                    input_selector=InputSelector(
                        sources=[InputSource(InputSourceType.ARTIFACT, "profile")]
                    ),
                    output_binding=OutputBinding(artifact_type="education.study_plan"),
                ),
                NodeSpec(
                    node_id="coach",
                    node_type=NodeType.AGENT,
                    executor_ref="agent.domain",
                    agent_ref="tutor_coach",
                    input_selector=InputSelector(
                        sources=[InputSource(InputSourceType.ARTIFACT, "plan")]
                    ),
                    output_binding=OutputBinding(artifact_type="education.learner_guidance"),
                ),
            ],
            edge_specs=[
                EdgeSpec(edge_id="e1", from_node_id="profile", to_node_id="plan"),
                EdgeSpec(edge_id="e2", from_node_id="plan", to_node_id="coach"),
            ],
        )
    )

    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
        llm_invoker=_FakeEducationLLMInvoker(),
    )

    runtime = RuntimeService(
        services=services,
        workflow_provider=workflow_provider,
        node_executor=BasicNodeExecutor(
            delegates=[DomainAgentExecutor(EducationDomainPack.get_agent_implementations())]
        ),
        agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
    )
    return runtime, services


class EducationAgentLLMIntegrationTestCase(unittest.TestCase):
    def test_planner_and_coach_can_use_llm_outputs(self) -> None:
        runtime, services = _build_llm_runtime()

        thread = runtime.create_thread("task", "education llm path")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        self.assertIsNotNone(thread_state)
        thread_state.global_context = {
            "learner_id": "learner-llm-001",
            "goal": "fractions mastery",
            "current_level": "beginner",
            "weak_topics": ["fraction addition"],
            "preferences": ["worked examples"],
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "wf.education.llm.path")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        plan_artifact = state.artifacts[state.node_states["plan"].output_artifact_id]
        coach_artifact = state.artifacts[state.node_states["coach"].output_artifact_id]

        self.assertEqual(
            plan_artifact.payload_inline["focus_areas"],
            ["equivalent fractions", "fraction addition"],
        )
        self.assertEqual(plan_artifact.payload_inline["llm_context"]["mode"], "llm")
        self.assertEqual(plan_artifact.payload_inline["llm_context"]["provider_ref"], "deepseek")
        self.assertEqual(
            coach_artifact.payload_inline["tone"],
            "warm_structured",
        )
        self.assertEqual(coach_artifact.payload_inline["llm_context"]["mode"], "llm")
        self.assertEqual(coach_artifact.payload_inline["llm_context"]["provider_ref"], "deepseek")
