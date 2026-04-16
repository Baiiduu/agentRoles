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
from core.executors import BasicNodeExecutor, DomainAgentExecutor, ToolNodeExecutor
from core.runtime import RuntimeService
from core.state.models import RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import InMemoryToolRegistry, ObservedToolInvoker, RoutingToolInvoker
from core.workflow import InMemoryWorkflowProvider
from domain_packs.education import EducationDomainPack
from domain_packs.education.tools import build_education_function_tool_adapter


def _build_education_runtime() -> tuple[RuntimeService, RuntimeServices]:
    registry = InMemoryAgentRegistry()
    for descriptor in EducationDomainPack.get_agent_descriptors():
        registry.register(descriptor)

    provider = InMemoryWorkflowProvider()
    for definition in EducationDomainPack.get_workflow_definitions():
        provider.register(definition)

    tool_registry = InMemoryToolRegistry()
    for descriptor in EducationDomainPack.get_tool_descriptors():
        tool_registry.register(descriptor)

    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
        tool_invoker=ObservedToolInvoker(
            RoutingToolInvoker(
                registry=tool_registry,
                adapters=[build_education_function_tool_adapter()],
            )
        ),
    )
    runtime = RuntimeService(
        services=services,
        workflow_provider=provider,
        node_executor=BasicNodeExecutor(
            delegates=[
                ToolNodeExecutor(),
                DomainAgentExecutor(EducationDomainPack.get_agent_implementations()),
            ]
        ),
        agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
    )
    return runtime, services


class EducationWorkflowTestCase(unittest.TestCase):
    def test_pack_exposes_education_workflows(self) -> None:
        workflows = EducationDomainPack.get_workflow_definitions()

        self.assertEqual(len(workflows), 3)
        self.assertEqual(
            [workflow.workflow_id for workflow in workflows],
            [
                "education.diagnostic_plan",
                "education.practice_review",
                "education.remediation_loop",
            ],
        )
        self.assertEqual(workflows[0].entry_node_id, "profile_learner")
        self.assertEqual(workflows[1].entry_node_id, "design_exercises")
        self.assertEqual(workflows[2].entry_node_id, "design_initial_exercises")

    def test_diagnostic_plan_workflow_runs_end_to_end(self) -> None:
        runtime, services = _build_education_runtime()

        thread = runtime.create_thread("task", "fractions mastery")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        thread_state.global_context = {
            "learner_id": "learner-001",
            "goal": "fractions mastery",
            "current_level": "beginner",
            "weak_topics": ["fractions", "word problems"],
            "preferences": ["worked examples"],
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "education.diagnostic_plan")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(
            set(state.run_state.completed_nodes),
            {
                "profile_learner",
                "lookup_curriculum_context",
                "plan_curriculum",
                "coach_learner",
            },
        )

        lookup_artifact = state.artifacts[
            state.node_states["lookup_curriculum_context"].output_artifact_id
        ]
        plan_artifact = state.artifacts[state.node_states["plan_curriculum"].output_artifact_id]
        coach_artifact = state.artifacts[state.node_states["coach_learner"].output_artifact_id]

        self.assertIn("prerequisites", lookup_artifact.payload_inline)
        self.assertEqual(plan_artifact.payload_inline["goal"], "fractions mastery")
        self.assertIn("milestones", plan_artifact.payload_inline)
        self.assertIn("explanation", coach_artifact.payload_inline)
        self.assertIn("next_steps", coach_artifact.payload_inline)

    def test_practice_review_workflow_runs_end_to_end(self) -> None:
        runtime, services = _build_education_runtime()

        thread = runtime.create_thread("task", "practice fractions")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        thread_state.global_context = {
            "learner_id": "learner-001",
            "goal": "fractions mastery",
            "target_skill": "fraction addition",
            "current_level": "beginner",
            "learner_response": "I added the denominators too.",
            "score": 0.45,
            "error_analysis": "The learner still confuses denominator handling.",
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "education.practice_review")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(
            set(state.run_state.completed_nodes),
            {
                "design_exercises",
                "lookup_exercise_template",
                "capture_submission",
                "normalize_submission",
                "lookup_review_rubric",
                "review_submission",
                "coach_feedback",
            },
        )

        normalized_artifact = state.artifacts[
            state.node_states["normalize_submission"].output_artifact_id
        ]
        review_artifact = state.artifacts[state.node_states["review_submission"].output_artifact_id]
        coach_artifact = state.artifacts[state.node_states["coach_feedback"].output_artifact_id]

        self.assertEqual(
            normalized_artifact.payload_inline["normalized_response"],
            "i added the denominators too.",
        )
        self.assertEqual(review_artifact.payload_inline["mastery_signal"], "weak")
        self.assertEqual(
            review_artifact.payload_inline["remediation_recommendation"],
            "remediation_required",
        )
        self.assertIn("fractions mastery", coach_artifact.payload_inline["explanation"])
        self.assertIn("remediation_required", coach_artifact.payload_inline["next_steps"])

    def test_remediation_loop_workflow_routes_to_remediation_path(self) -> None:
        runtime, services = _build_education_runtime()

        thread = runtime.create_thread("task", "remediate fractions")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        thread_state.global_context = {
            "learner_id": "learner-001",
            "goal": "fractions mastery",
            "target_skill": "fraction addition",
            "current_level": "beginner",
            "learner_response": "I added the denominators too.",
            "score": 0.2,
            "error_analysis": "The learner is still applying whole-number addition rules.",
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "education.remediation_loop")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(
            set(state.run_state.completed_nodes),
            {
                "design_initial_exercises",
                "capture_attempt",
                "normalize_attempt",
                "lookup_attempt_rubric",
                "review_attempt",
                "decide_remediation_path",
                "lookup_remediation_template",
                "design_remediation_exercises",
                "coach_remediation_path",
            },
        )

        decision_artifact = state.artifacts[
            state.node_states["decide_remediation_path"].output_artifact_id
        ]
        remediation_artifact = state.artifacts[
            state.node_states["design_remediation_exercises"].output_artifact_id
        ]
        coach_artifact = state.artifacts[
            state.node_states["coach_remediation_path"].output_artifact_id
        ]

        self.assertTrue(decision_artifact.payload_inline["matched"])
        self.assertEqual(
            decision_artifact.payload_inline["selected_branch"],
            "design_remediation_exercises",
        )
        self.assertEqual(remediation_artifact.payload_inline["target_skill"], "fraction addition")
        self.assertIn(
            "remediation_required",
            coach_artifact.payload_inline["next_steps"],
        )
        self.assertNotIn("coach_progress_path", state.run_state.completed_nodes)

    def test_remediation_loop_workflow_can_exit_without_remediation(self) -> None:
        runtime, services = _build_education_runtime()

        thread = runtime.create_thread("task", "advance fractions")
        thread_state = services.state_store.get_thread_state(thread.thread_id)
        thread_state.global_context = {
            "learner_id": "learner-002",
            "goal": "fractions mastery",
            "target_skill": "fraction addition",
            "current_level": "intermediate",
            "learner_response": "I found a common denominator and added the numerators.",
            "score": 0.9,
            "error_analysis": "Minor notation slip only.",
        }
        services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(thread.thread_id, "education.remediation_loop")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        self.assertEqual(
            set(state.run_state.completed_nodes),
            {
                "design_initial_exercises",
                "capture_attempt",
                "normalize_attempt",
                "lookup_attempt_rubric",
                "review_attempt",
                "decide_remediation_path",
                "coach_progress_path",
            },
        )

        decision_artifact = state.artifacts[
            state.node_states["decide_remediation_path"].output_artifact_id
        ]
        coach_artifact = state.artifacts[
            state.node_states["coach_progress_path"].output_artifact_id
        ]

        self.assertFalse(decision_artifact.payload_inline["matched"])
        self.assertEqual(
            decision_artifact.payload_inline["selected_branch"],
            "coach_progress_path",
        )
        self.assertIn("advance", coach_artifact.payload_inline["next_steps"])
        self.assertNotIn("design_remediation_exercises", state.run_state.completed_nodes)
        self.assertNotIn("lookup_remediation_template", state.run_state.completed_nodes)
