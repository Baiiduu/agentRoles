from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import ExecutionContext, RuntimeServices
from core.state.models import (
    NodeState,
    NodeStatus,
    NodeType,
    RunRecord,
    RunState,
    RunStatus,
    ThreadRecord,
    ThreadState,
    ThreadStatus,
)
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.tools import FunctionToolAdapter, InMemoryToolRegistry, RoutingToolInvoker
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec
from domain_packs.education import EducationDomainPack
from domain_packs.education.tools import (
    EDUCATION_TOOL_REFS,
    build_education_function_tool_adapter,
)


def _context() -> ExecutionContext:
    thread_record = ThreadRecord(thread_id="thread_1", thread_type="task", status=ThreadStatus.ACTIVE)
    run_record = RunRecord(
        run_id="run_1",
        thread_id="thread_1",
        workflow_id="wf.education.tools",
        workflow_version="1.0.0",
        status=RunStatus.RUNNING,
        entry_node_id="tool_node",
    )
    thread_state = ThreadState(
        thread_id="thread_1",
        goal="exercise education tools",
        active_run_id="run_1",
        thread_status=ThreadStatus.ACTIVE,
    )
    run_state = RunState(
        run_id="run_1",
        thread_id="thread_1",
        workflow_id="wf.education.tools",
        workflow_version="1.0.0",
        status=RunStatus.RUNNING,
        frontier=["tool_node"],
    )
    node_state = NodeState(
        run_id="run_1",
        node_id="tool_node",
        node_type=NodeType.TOOL,
        status=NodeStatus.RUNNING,
        attempt=1,
        executor_ref="tool.executor",
        started_at=datetime.now(UTC),
    )
    node_spec = NodeSpec(
        node_id="tool_node",
        node_type=NodeType.TOOL,
        executor_ref="tool.executor",
        input_selector=InputSelector(
            sources=[InputSource(InputSourceType.LITERAL, "seed")],
        ),
    )
    workflow = CompiledWorkflow(
        workflow_id="wf.education.tools",
        version="1.0.0",
        entry_node_id="tool_node",
        node_map={"tool_node": node_spec},
        outgoing_edges={"tool_node": []},
        incoming_edges={"tool_node": []},
    )
    services = RuntimeServices(
        state_store=InMemoryStateStore(),
        event_store=InMemoryEventStore(),
        checkpoint_store=InMemoryCheckpointStore(),
    )
    return ExecutionContext(
        thread_record=thread_record,
        run_record=run_record,
        thread_state=thread_state,
        run_state=run_state,
        node_state=node_state,
        workflow=workflow,
        node_spec=node_spec,
        services=services,
    )


class EducationToolLayerTestCase(unittest.TestCase):
    def test_pack_exposes_education_tool_descriptors(self) -> None:
        descriptors = EducationDomainPack.get_tool_descriptors()

        self.assertEqual(len(descriptors), 4)
        self.assertEqual(
            {descriptor.tool_ref for descriptor in descriptors},
            {
                EDUCATION_TOOL_REFS["curriculum_lookup"],
                EDUCATION_TOOL_REFS["exercise_template_lookup"],
                EDUCATION_TOOL_REFS["rubric_lookup"],
                EDUCATION_TOOL_REFS["answer_normalizer"],
            },
        )
        self.assertTrue(all(descriptor.provider_ref == "education.local_reference" for descriptor in descriptors))

    def test_descriptors_align_with_agent_declared_tool_refs(self) -> None:
        descriptor_refs = {
            descriptor.tool_ref for descriptor in EducationDomainPack.get_tool_descriptors()
        }
        agent_refs = {
            tool_ref
            for descriptor in EducationDomainPack.get_agent_descriptors()
            for tool_ref in descriptor.tool_refs
        }

        self.assertTrue(agent_refs.issubset(descriptor_refs))

    def test_education_function_tool_adapter_invokes_reference_tools(self) -> None:
        registry = InMemoryToolRegistry()
        for descriptor in EducationDomainPack.get_tool_descriptors():
            registry.register(descriptor)

        adapter = build_education_function_tool_adapter()
        self.assertIsInstance(adapter, FunctionToolAdapter)
        invoker = RoutingToolInvoker(registry=registry, adapters=[adapter])

        curriculum_result = invoker.invoke(
            EDUCATION_TOOL_REFS["curriculum_lookup"],
            {"target_skill": "fraction addition", "current_level": "beginner"},
            _context(),
        )
        normalizer_result = invoker.invoke(
            EDUCATION_TOOL_REFS["answer_normalizer"],
            {"learner_response": " I Added   The Denominators Too "},
            _context(),
        )

        self.assertTrue(curriculum_result.success)
        self.assertIn("common denominators", curriculum_result.output["prerequisites"])
        self.assertTrue(normalizer_result.success)
        self.assertEqual(
            normalizer_result.output["normalized_response"],
            "i added the denominators too",
        )
        self.assertIn("denominators", normalizer_result.output["keywords"])

    def test_exercise_template_lookup_supports_remediation_variant(self) -> None:
        registry = InMemoryToolRegistry()
        for descriptor in EducationDomainPack.get_tool_descriptors():
            registry.register(descriptor)

        invoker = RoutingToolInvoker(
            registry=registry,
            adapters=[build_education_function_tool_adapter()],
        )

        result = invoker.invoke(
            EDUCATION_TOOL_REFS["exercise_template_lookup"],
            {
                "target_skill": "fraction addition",
                "current_level": "beginner",
                "mastery_signal": "weak",
            },
            _context(),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.output["template_type"], "scaffolded-remediation")
        self.assertIn("worked-example", result.output["hint_styles"])
