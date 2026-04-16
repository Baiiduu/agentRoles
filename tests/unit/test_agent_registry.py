from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents import (
    AgentDescriptor,
    AgentQuery,
    AgentStatus,
    InMemoryAgentRegistry,
    split_agent_ref,
)


class AgentRegistryTestCase(unittest.TestCase):
    def test_register_and_get_descriptor(self) -> None:
        registry = InMemoryAgentRegistry()
        descriptor = AgentDescriptor(
            agent_id="teacher_planner",
            name="Teacher Planner",
            version="1.0.0",
            role="planner",
            description="Creates lesson plans",
            executor_ref="agent.teacher_planner",
            domain="education",
            tool_refs=["tool.search", "tool.syllabus"],
            memory_scopes=["thread:{thread_id}", "domain:education"],
            policy_profiles=["edu_default"],
            capabilities=["lesson_planning", "curriculum_alignment"],
            tags=["education", "planner"],
        )

        stored = registry.register(descriptor)
        loaded = registry.get("teacher_planner", version="1.0.0")

        self.assertEqual(stored.agent_id, "teacher_planner")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.version, "1.0.0")
        self.assertEqual(loaded.domain, "education")
        self.assertIn("tool.search", loaded.tool_refs)

    def test_get_default_returns_latest_version(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.0.0",
                role="planner",
                description="v1",
                executor_ref="agent.teacher_planner",
            )
        )
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.2.0",
                role="planner",
                description="v2",
                executor_ref="agent.teacher_planner",
            )
        )

        default = registry.get_default("teacher_planner")

        self.assertIsNotNone(default)
        self.assertEqual(default.version, "1.2.0")

    def test_resolve_supports_agent_ref_with_and_without_version(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="sbom_analyst",
                name="SBOM Analyst",
                version="1.0.0",
                role="analyst",
                description="Analyzes SBOMs",
                executor_ref="agent.sbom_analyst",
            )
        )
        registry.register(
            AgentDescriptor(
                agent_id="sbom_analyst",
                name="SBOM Analyst",
                version="2.0.0",
                role="analyst",
                description="Analyzes SBOMs better",
                executor_ref="agent.sbom_analyst",
            )
        )

        explicit = registry.resolve("sbom_analyst:1.0.0")
        implicit = registry.resolve("sbom_analyst")

        self.assertEqual(explicit.version, "1.0.0")
        self.assertEqual(implicit.version, "2.0.0")

    def test_list_filters_by_domain_capability_tool_and_memory_scope(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.0.0",
                role="planner",
                description="Lesson planner",
                executor_ref="agent.teacher_planner",
                domain="education",
                tool_refs=["tool.search"],
                memory_scopes=["domain:education"],
                capabilities=["lesson_planning"],
                tags=["education", "planner"],
            )
        )
        registry.register(
            AgentDescriptor(
                agent_id="sbom_analyst",
                name="SBOM Analyst",
                version="1.0.0",
                role="analyst",
                description="SBOM analyst",
                executor_ref="agent.sbom_analyst",
                domain="supply_chain",
                tool_refs=["tool.sbom"],
                memory_scopes=["domain:supply_chain"],
                capabilities=["sbom_analysis"],
                tags=["supply-chain", "analyst"],
            )
        )

        results = registry.list(
            AgentQuery(
                domain="education",
                capabilities=["lesson_planning"],
                tool_ref="tool.search",
                memory_scope="domain:education",
                tags=["planner"],
            )
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, "teacher_planner")

    def test_list_filters_by_status(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="deprecated_agent",
                name="Deprecated Agent",
                version="1.0.0",
                role="planner",
                description="deprecated",
                executor_ref="agent.deprecated",
                status=AgentStatus.DEPRECATED,
            )
        )
        registry.register(
            AgentDescriptor(
                agent_id="active_agent",
                name="Active Agent",
                version="1.0.0",
                role="planner",
                description="active",
                executor_ref="agent.active",
                status=AgentStatus.ACTIVE,
            )
        )

        results = registry.list(AgentQuery(status=AgentStatus.ACTIVE))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, "active_agent")

    def test_registry_returns_deep_copies(self) -> None:
        registry = InMemoryAgentRegistry()
        registry.register(
            AgentDescriptor(
                agent_id="teacher_planner",
                name="Teacher Planner",
                version="1.0.0",
                role="planner",
                description="Lesson planner",
                executor_ref="agent.teacher_planner",
                capabilities=["lesson_planning"],
            )
        )

        loaded = registry.get("teacher_planner", version="1.0.0")
        loaded.capabilities.append("mutated")
        reloaded = registry.get("teacher_planner", version="1.0.0")

        self.assertEqual(reloaded.capabilities, ["lesson_planning"])

    def test_duplicate_registration_is_rejected(self) -> None:
        registry = InMemoryAgentRegistry()
        descriptor = AgentDescriptor(
            agent_id="teacher_planner",
            name="Teacher Planner",
            version="1.0.0",
            role="planner",
            description="Lesson planner",
            executor_ref="agent.teacher_planner",
        )
        registry.register(descriptor)

        with self.assertRaises(ValueError):
            registry.register(descriptor)

    def test_split_agent_ref(self) -> None:
        self.assertEqual(split_agent_ref("teacher_planner"), ("teacher_planner", None))
        self.assertEqual(
            split_agent_ref("teacher_planner:1.0.0"),
            ("teacher_planner", "1.0.0"),
        )

