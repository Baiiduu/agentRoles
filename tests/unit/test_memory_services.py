from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.contracts import NodeExecutionResult, RuntimeServices
from core.memory import (
    InMemoryMemoryProvider,
    MemoryPolicyError,
    ObservedMemoryProvider,
    PolicyAwareMemoryProvider,
    memory_results_hint,
)
from core.runtime import RuntimeService
from core.state.models import NodeStatus, NodeType, RunStatus
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
from core.executors import BasicNodeExecutor
from core.policies import StaticPolicyEngine


def _literal_selector(value: str = "seed") -> InputSelector:
    return InputSelector(sources=[InputSource(InputSourceType.LITERAL, value)])


class MemoryAwareExecutor:
    def can_execute(self, node_type, executor_ref):
        return node_type == NodeType.AGENT and executor_ref.startswith("memory.")

    def execute(self, context):
        provider = context.services.memory_provider
        if provider is None:
            raise ValueError("memory provider is required")

        scope = context.node_spec.config.get(
            "scope", f"thread:{context.thread_record.thread_id}"
        )
        if context.node_spec.executor_ref == "memory.write":
            try:
                memory_id = provider.write(
                    {
                        "scope": scope,
                        "content": context.node_spec.config.get("content", "default memory"),
                        "tags": list(context.node_spec.config.get("tags", [])),
                        "payload": {"node_id": context.node_state.node_id},
                        "source_ref": context.node_state.node_id,
                    },
                    context=context,
                )
            except MemoryPolicyError as exc:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code="MEMORY_POLICY_DENIED",
                    error_message=str(exc),
                )
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={"memory_id": memory_id, "scope": scope},
            )

        if context.node_spec.executor_ref == "memory.retrieve":
            try:
                results = provider.retrieve(
                    str(context.node_spec.config.get("query", "")),
                    scope,
                    top_k=int(context.node_spec.config.get("top_k", 3)),
                    context=context,
                )
            except MemoryPolicyError as exc:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code="MEMORY_POLICY_DENIED",
                    error_message=str(exc),
                )
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={
                    "result_count": len(results),
                    "top_memory_id": results[0].memory_id if results else None,
                    "top_scope": results[0].scope if results else None,
                },
            )

        if context.node_spec.executor_ref == "memory.retrieve_and_cache":
            try:
                results = provider.retrieve(
                    str(context.node_spec.config.get("query", "")),
                    scope,
                    top_k=int(context.node_spec.config.get("top_k", 3)),
                    context=context,
                )
            except MemoryPolicyError as exc:
                return NodeExecutionResult(
                    status=NodeStatus.FAILED,
                    error_code="MEMORY_POLICY_DENIED",
                    error_message=str(exc),
                )
            return NodeExecutionResult(
                status=NodeStatus.SUCCEEDED,
                output={"cached_slot": context.node_spec.config.get("slot", "default")},
                next_hints=memory_results_hint(
                    str(context.node_spec.config.get("slot", "default")),
                    results,
                ),
            )

        raise ValueError(f"unsupported memory executor_ref={context.node_spec.executor_ref}")


class MemoryServicesTestCase(unittest.TestCase):
    def test_in_memory_provider_is_scope_isolated_and_ranked(self) -> None:
        provider = InMemoryMemoryProvider()
        provider.write(
            {
                "scope": "thread:t1",
                "content": "algebra practice set and mastery",
                "tags": ["math", "algebra"],
            }
        )
        provider.write(
            {
                "scope": "thread:t1",
                "content": "history reading notes",
                "tags": ["history"],
            }
        )
        provider.write(
            {
                "scope": "thread:t2",
                "content": "algebra but other thread",
                "tags": ["math"],
            }
        )

        results = provider.retrieve("algebra mastery", "thread:t1", top_k=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].scope, "thread:t1")
        self.assertIn("algebra", results[0].payload["content"])

    def test_in_memory_provider_summarizes_scope(self) -> None:
        provider = InMemoryMemoryProvider()
        provider.write(
            {
                "scope": "domain:education",
                "content": "learner prefers spaced repetition",
                "tags": ["preference", "learning"],
            }
        )
        provider.write(
            {
                "scope": "domain:education",
                "content": "learner strong in algebra",
                "tags": ["profile", "algebra"],
            }
        )

        summary = provider.summarize("domain:education")

        self.assertEqual(summary["scope"], "domain:education")
        self.assertEqual(summary["total_items"], 2)
        self.assertEqual(summary["tag_counts"]["algebra"], 1)
        self.assertIsNotNone(summary["latest_updated_at"])

    def test_in_memory_provider_rejects_invalid_tags_shape(self) -> None:
        provider = InMemoryMemoryProvider()

        with self.assertRaises(ValueError):
            provider.write(
                {
                    "scope": "thread:t-invalid",
                    "content": "bad tags payload",
                    "tags": "not-a-list",
                }
            )

    def test_runtime_can_consume_memory_provider_through_executor_context(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.memory.runtime",
                name="Memory Runtime",
                version="1.0.0",
                entry_node_id="remember",
                node_specs=[
                    NodeSpec(
                        node_id="remember",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.write",
                        input_selector=_literal_selector("remember"),
                        config={
                            "scope": "thread:memory-test",
                            "content": "student is strong at algebra",
                            "tags": ["student", "algebra"],
                        },
                    ),
                    NodeSpec(
                        node_id="recall",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.retrieve",
                        input_selector=_literal_selector("recall"),
                        output_binding=OutputBinding(artifact_type="memory_lookup"),
                        config={
                            "scope": "thread:memory-test",
                            "query": "algebra student",
                            "top_k": 3,
                        },
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="remember", to_node_id="recall")
                ],
            )
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            memory_provider=InMemoryMemoryProvider(),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[MemoryAwareExecutor()]),
        )

        thread = runtime.create_thread("task", "memory service runtime test")
        run = runtime.start_run(thread.thread_id, "wf.memory.runtime")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        recall_state = state.node_states["recall"]
        self.assertIsNotNone(recall_state.output_artifact_id)
        artifact = state.artifacts[recall_state.output_artifact_id]
        self.assertEqual(artifact.payload_inline["result_count"], 1)
        self.assertEqual(artifact.payload_inline["top_scope"], "thread:memory-test")

    def test_memory_results_can_flow_into_selector_via_run_state_extensions(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.memory.selector",
                name="Memory Selector",
                version="1.0.0",
                entry_node_id="remember",
                node_specs=[
                    NodeSpec(
                        node_id="remember",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.write",
                        input_selector=_literal_selector("remember"),
                        config={
                            "scope": "thread:selector-memory",
                            "content": "learner prefers algebra examples",
                            "tags": ["learner", "algebra"],
                        },
                    ),
                    NodeSpec(
                        node_id="retrieve",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.retrieve_and_cache",
                        input_selector=_literal_selector("retrieve"),
                        config={
                            "scope": "thread:selector-memory",
                            "query": "algebra learner",
                            "slot": "learner_lookup",
                        },
                    ),
                    NodeSpec(
                        node_id="consume",
                        node_type=NodeType.NOOP,
                        executor_ref="builtin.noop",
                        input_selector=InputSelector(
                            sources=[
                                InputSource(
                                    InputSourceType.MEMORY_RESULT,
                                    "learner_lookup",
                                    path="top_item.payload.content",
                                )
                            ]
                        ),
                        output_binding=OutputBinding(artifact_type="memory_consumed"),
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="remember", to_node_id="retrieve"),
                    EdgeSpec(edge_id="e2", from_node_id="retrieve", to_node_id="consume"),
                ],
            )
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            memory_provider=InMemoryMemoryProvider(),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[MemoryAwareExecutor()]),
        )

        thread = runtime.create_thread("task", "memory selector integration")
        run = runtime.start_run(thread.thread_id, "wf.memory.selector")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.COMPLETED)
        cached = state.run_state.extensions["memory_results"]["learner_lookup"]
        self.assertEqual(cached["count"], 1)
        consume_state = state.node_states["consume"]
        artifact = state.artifacts[consume_state.output_artifact_id]
        self.assertEqual(
            artifact.payload_inline["value"],
            "learner prefers algebra examples",
        )

    def test_observed_memory_provider_emits_runtime_events(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.memory.observed",
                name="Observed Memory",
                version="1.0.0",
                entry_node_id="remember",
                node_specs=[
                    NodeSpec(
                        node_id="remember",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.write",
                        input_selector=_literal_selector("remember"),
                        config={
                            "scope": "thread:observed-memory",
                            "content": "memory events matter",
                        },
                    ),
                    NodeSpec(
                        node_id="recall",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.retrieve",
                        input_selector=_literal_selector("recall"),
                        config={
                            "scope": "thread:observed-memory",
                            "query": "events",
                        },
                    ),
                ],
                edge_specs=[
                    EdgeSpec(edge_id="e1", from_node_id="remember", to_node_id="recall")
                ],
            )
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            memory_provider=ObservedMemoryProvider(InMemoryMemoryProvider()),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[MemoryAwareExecutor()]),
        )

        thread = runtime.create_thread("task", "observed memory test")
        run = runtime.start_run(thread.thread_id, "wf.memory.observed")
        events = list(runtime.stream_events(run.run_id))
        memory_events = [event.event_type for event in events if event.event_type.startswith("memory.")]

        self.assertIn("memory.write.started", memory_events)
        self.assertIn("memory.write.succeeded", memory_events)
        self.assertIn("memory.retrieve.started", memory_events)
        self.assertIn("memory.retrieve.succeeded", memory_events)

    def test_policy_aware_memory_provider_can_deny_scope(self) -> None:
        provider = InMemoryWorkflowProvider()
        provider.register(
            WorkflowDefinition(
                workflow_id="wf.memory.policy",
                name="Policy Memory",
                version="1.0.0",
                entry_node_id="remember",
                node_specs=[
                    NodeSpec(
                        node_id="remember",
                        node_type=NodeType.AGENT,
                        executor_ref="memory.write",
                        input_selector=_literal_selector("remember"),
                        config={
                            "scope": "thread:blocked-memory",
                            "content": "should be blocked",
                        },
                    )
                ],
                edge_specs=[],
            )
        )
        services = RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
            policy_engine=StaticPolicyEngine(
                deny_side_effect_targets={"thread:blocked-memory"}
            ),
            memory_provider=PolicyAwareMemoryProvider(InMemoryMemoryProvider()),
        )
        runtime = RuntimeService(
            services=services,
            workflow_provider=provider,
            node_executor=BasicNodeExecutor(delegates=[MemoryAwareExecutor()]),
        )

        thread = runtime.create_thread("task", "policy memory test")
        run = runtime.start_run(thread.thread_id, "wf.memory.policy")
        state = runtime.get_state(run.run_id)

        self.assertEqual(state.run_record.status, RunStatus.FAILED)
        self.assertEqual(state.node_states["remember"].status, NodeStatus.FAILED)
        self.assertEqual(state.node_states["remember"].error_code, "MEMORY_POLICY_DENIED")
