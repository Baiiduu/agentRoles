from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.agents.bindings import ResolvedAgentBinding
from core.contracts import ExecutionContext, RuntimeServices
from core.state.models import NodeState, NodeStatus, NodeType, RunRecord, RunState, RunStatus, ThreadRecord, ThreadState
from core.stores import InMemoryCheckpointStore, InMemoryEventStore, InMemoryStateStore
from core.workflow.workflow_models import CompiledWorkflow, InputSelector, InputSource, InputSourceType, NodeSpec
from domain_packs.operations.filesystem import (
    find_references_handler,
    lookup_definition_handler,
    symbol_outline_handler,
    symbol_search_handler,
)


def _context(workspace_root: Path) -> ExecutionContext:
    binding = ResolvedAgentBinding(
        node_id="tool_node",
        agent_ref="test_pro_chat",
        resolved_agent_id="test_pro_chat",
        resolved_version="0.1.0",
        executor_ref="agent.domain",
        implementation_ref="test_pro.chat",
        metadata={
            "runtime_resource_context": {
                "workspace": {
                    "enabled": True,
                    "absolute_path": str(workspace_root),
                }
            }
        },
    )
    node_spec = NodeSpec(
        node_id="tool_node",
        node_type=NodeType.TOOL,
        executor_ref="tool.executor",
        input_selector=InputSelector(
            sources=[InputSource(InputSourceType.LITERAL, "seed")]
        ),
    )
    workflow = CompiledWorkflow(
        workflow_id="wf.operations.symbols",
        version="1.0.0",
        entry_node_id="tool_node",
        node_map={"tool_node": node_spec},
        outgoing_edges={"tool_node": []},
        incoming_edges={"tool_node": []},
    )
    return ExecutionContext(
        thread_record=ThreadRecord(thread_id="thread_1", thread_type="task"),
        run_record=RunRecord(
            run_id="run_1",
            thread_id="thread_1",
            workflow_id="wf.operations.symbols",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
            entry_node_id="tool_node",
        ),
        thread_state=ThreadState(thread_id="thread_1", goal="test symbol tools"),
        run_state=RunState(
            run_id="run_1",
            thread_id="thread_1",
            workflow_id="wf.operations.symbols",
            workflow_version="1.0.0",
            status=RunStatus.RUNNING,
        ),
        node_state=NodeState(
            run_id="run_1",
            node_id="tool_node",
            node_type=NodeType.TOOL,
            status=NodeStatus.RUNNING,
            started_at=datetime.now(UTC),
            executor_ref="tool.executor",
        ),
        workflow=workflow,
        node_spec=node_spec,
        agent_binding=binding,
        services=RuntimeServices(
            state_store=InMemoryStateStore(),
            event_store=InMemoryEventStore(),
            checkpoint_store=InMemoryCheckpointStore(),
        ),
    )


class OperationSymbolToolsTestCase(unittest.TestCase):
    def test_symbol_navigation_tools_cover_outline_definition_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sample = root / "pkg" / "sample.py"
            sample.parent.mkdir(parents=True, exist_ok=True)
            sample.write_text(
                "\n".join(
                    [
                        "class LoginManager:",
                        "    pass",
                        "",
                        "def login_user(user, password):",
                        "    helper = LoginManager()",
                        "    return helper",
                        "",
                        "def use_login():",
                        "    return login_user('a', 'b')",
                    ]
                ),
                encoding="utf-8",
            )
            context = _context(root)

            outline = symbol_outline_handler({"path": "pkg/sample.py"}, context)
            definitions = lookup_definition_handler({"symbol": "login_user"}, context)
            symbols = symbol_search_handler({"query": "Login"}, context)
            references = find_references_handler({"symbol": "login_user"}, context)

            self.assertTrue(outline.success)
            self.assertEqual(outline.output["symbols"][0]["name"], "LoginManager")
            self.assertTrue(definitions.success)
            self.assertEqual(definitions.output["matches"][0]["path"], "pkg/sample.py")
            self.assertTrue(symbols.success)
            self.assertTrue(any(item["name"] == "LoginManager" for item in symbols.output["matches"]))
            self.assertTrue(references.success)
            self.assertTrue(any(item["match_kind"] == "reference" for item in references.output["matches"]))


if __name__ == "__main__":
    unittest.main()
