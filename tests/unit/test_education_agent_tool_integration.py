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
from core.runtime import RuntimeService
from core.state.models import NodeType, RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import InMemoryToolRegistry, ObservedToolInvoker, RoutingToolInvoker
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
from domain_packs.education.tools import (
    EDUCATION_TOOL_REFS,
    build_education_function_tool_adapter,
)


def _build_tool_runtime(*definitions: WorkflowDefinition) -> tuple[RuntimeService, RuntimeServices]:
    registry = InMemoryAgentRegistry()
    for descriptor in EducationDomainPack.get_agent_descriptors():
        registry.register(descriptor)

    workflow_provider = InMemoryWorkflowProvider()
    for definition in definitions:
        workflow_provider.register(definition)

    tool_registry = InMemoryToolRegistry()
    for descriptor in EducationDomainPack.get_tool_descriptors():
        tool_registry.register(descriptor)

    tool_invoker = ObservedToolInvoker(
        RoutingToolInvoker(
            registry=tool_registry,
            adapters=[build_education_function_tool_adapter()],
        )
    )

    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
        tool_invoker=tool_invoker,
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


class EducationAgentToolIntegrationTestCase(unittest.TestCase):
    def test_profiler_and_planner_are_enriched_by_curriculum_tool(self) -> None:
        runtime, services = _build_tool_runtime(
            WorkflowDefinition(
                workflow_id="wf.education.tool.plan",
                name="Education Tool Planning",
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
                ],
                edge_specs=[EdgeSpec(edge_id="e1", from_node_id="profile", to_node_id="plan")],
            )
        )

        thread = runtime.create_thread("task", "education tool planning")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        self.assertIsNotNone(thread_state)
        thread_state.global_context = {
            "learner_id": "learner-100",
            "goal": "fractions mastery",
            "current_level": "beginner",
            "weak_topics": ["fraction addition"],
            "preferences": ["worked examples"],
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "wf.education.tool.plan")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        profile_artifact = state.artifacts[state.node_states["profile"].output_artifact_id]
        plan_artifact = state.artifacts[state.node_states["plan"].output_artifact_id]

        self.assertIn("tool_context", profile_artifact.payload_inline)
        self.assertIn("curriculum_lookup", profile_artifact.payload_inline["tool_context"])
        self.assertIn("finding a common denominator", profile_artifact.payload_inline["focus_areas"])
        self.assertIn("prerequisites", plan_artifact.payload_inline)
        self.assertIn("equivalent fractions", plan_artifact.payload_inline["prerequisites"])
        self.assertGreaterEqual(len(state.side_effects), 2)

    def test_reviewer_uses_normalizer_and_rubric_tools(self) -> None:
        runtime, services = _build_tool_runtime(
            WorkflowDefinition(
                workflow_id="wf.education.tool.review",
                name="Education Tool Review",
                version="1.0.0",
                entry_node_id="review",
                node_specs=[
                    NodeSpec(
                        node_id="review",
                        node_type=NodeType.AGENT,
                        executor_ref="agent.domain",
                        agent_ref="reviewer_grader",
                        input_selector=InputSelector(
                            sources=[
                                InputSource(
                                    InputSourceType.THREAD_STATE,
                                    "thread_context",
                                    path="global_context",
                                )
                            ]
                        ),
                        output_binding=OutputBinding(artifact_type="education.review_summary"),
                    )
                ],
                edge_specs=[],
            )
        )

        thread = runtime.create_thread("task", "education tool review")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        self.assertIsNotNone(thread_state)
        thread_state.global_context = {
            "target_skill": "fraction addition",
            "learner_response": " I Added The Denominators Too ",
            "score": 0.4,
            "error_analysis": "The learner still adds denominators directly.",
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "wf.education.tool.review")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        review_artifact = state.artifacts[state.node_states["review"].output_artifact_id]

        self.assertEqual(review_artifact.payload_inline["normalized_response"], "i added the denominators too")
        self.assertIn(
            "chooses a valid common denominator",
            review_artifact.payload_inline["rubric_criteria"],
        )
        self.assertIn("tool_context", review_artifact.payload_inline)
        self.assertIn("answer_normalizer", review_artifact.payload_inline["tool_context"])
        self.assertIn("rubric_lookup", review_artifact.payload_inline["tool_context"])
        self.assertGreaterEqual(len(state.side_effects), 2)


if __name__ == "__main__":
    unittest.main()
