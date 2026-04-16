from __future__ import annotations

from copy import deepcopy

from core.workflow.workflow_models import WorkflowDefinition


def _version_sort_key(version: str) -> tuple[int, ...] | tuple[str]:
    parts = version.split(".")
    if all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return (version,)


class InMemoryWorkflowProvider:
    def __init__(self) -> None:
        self._definitions: dict[str, dict[str, WorkflowDefinition]] = {}

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        versions = self._definitions.setdefault(definition.workflow_id, {})
        versions[definition.version] = deepcopy(definition)
        return deepcopy(definition)

    def get_definition(
        self, workflow_id: str, *, version: str | None = None
    ) -> WorkflowDefinition | None:
        versions = self._definitions.get(workflow_id)
        if not versions:
            return None

        if version is not None:
            definition = versions.get(version)
            return deepcopy(definition) if definition is not None else None

        latest_version = max(versions, key=_version_sort_key)
        return deepcopy(versions[latest_version])
