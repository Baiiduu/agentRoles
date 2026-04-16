from __future__ import annotations

from typing import Protocol

from core.state.models import ReducedSnapshot
from core.workflow.workflow_models import CompiledWorkflow, InputSelector


class StateSelector(Protocol):
    def select_node_input(
        self, snapshot: ReducedSnapshot, selector: InputSelector
    ) -> dict[str, object]: ...

    def select_ready_nodes(
        self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow
    ) -> list[str]: ...

    def terminal_condition_met(
        self, snapshot: ReducedSnapshot, workflow: CompiledWorkflow
    ) -> bool: ...
