from __future__ import annotations

from typing import Protocol

from core.workflow.workflow_models import WorkflowDefinition


class WorkflowProvider(Protocol):
    def get_definition(
        self, workflow_id: str, *, version: str | None = None
    ) -> WorkflowDefinition | None: ...
