from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents import InMemoryAgentRegistry, RegistryBackedAgentBindingResolver
from core.executors import BasicNodeExecutor, DomainAgentExecutor
from core.runtime import RuntimeService
from core.state.models import NodeType, RunStatus
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.contracts import RuntimeServices
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


def _literal_selector(value: str) -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class EducationAgentImplementationTestCase(unittest.TestCase):
    def test_pack_exposes_five_agent_implementations(self) -> None:
        implementations = EducationDomainPack.get_agent_implementations()

        self.assertEqual(len(implementations), 5)

    def test_education_agents_run_through_domain_agent_executor(self) -> None:
        registry = InMemoryAgentRegistry()
        for descriptor in EducationDomainPack.get_agent_descriptors():
            registry.register(descriptor)

        workflows = InMemoryWorkflowProvider()
        workflows.register(
            WorkflowDefinition(
                workflow_id="wf.education.impls",
                name="Education Implementations",
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
                                    InputSourceType.LITERAL,
                                    json.dumps(
                                        {
                                            "learner_id": "learner-001",
                                            "goal": "fractions mastery",
                                            "weak_topics": ["fractions"],
                                            "preferences": ["examples"],
                                        }
                                    ),
                                )
                            ]
                        ),
                        output_binding=OutputBinding(artifact_type="learner_profile_summary"),
                    ),
                    NodeSpec(
                        node_id="plan",
                        node_type=NodeType.AGENT,
                        executor_ref="agent.domain",
                        agent_ref="curriculum_planner",
                        input_selector=InputSelector(
                            sources=[
                                InputSource(InputSourceType.ARTIFACT, "profile"),
                            ]
                        ),
                        output_binding=OutputBinding(artifact_type="study_plan"),
                    ),
                ],
                edge_specs=[EdgeSpec(edge_id="e1", from_node_id="profile", to_node_id="plan")],
            )
        )

        runtime = RuntimeService(
            services=RuntimeServices(
                state_store=InMemoryStateStore(),
                event_store=InMemoryEventStore(),
                checkpoint_store=InMemoryCheckpointStore(),
            ),
            workflow_provider=workflows,
            node_executor=BasicNodeExecutor(
                delegates=[
                    DomainAgentExecutor(EducationDomainPack.get_agent_implementations())
                ]
            ),
            agent_binding_resolver=RegistryBackedAgentBindingResolver(registry),
        )

        thread = runtime.create_thread("task", "education implementation runtime")
        run = runtime.start_run(thread.thread_id, "wf.education.impls")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        profile_artifact = state.artifacts[state.node_states["profile"].output_artifact_id]
        plan_artifact = state.artifacts[state.node_states["plan"].output_artifact_id]
        self.assertEqual(profile_artifact.payload_inline["learner_id"], "learner-001")
        self.assertIn("milestones", plan_artifact.payload_inline)
        self.assertEqual(plan_artifact.payload_inline["goal"], "fractions mastery")
