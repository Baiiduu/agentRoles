from __future__ import annotations

from copy import deepcopy
from typing import Sequence

from core.contracts import MemoryResult


def memory_results_hint(slot: str, results: Sequence[MemoryResult]) -> dict[str, object]:
    if not slot:
        raise ValueError("slot must be non-empty")
    serialized_items = [serialize_memory_result(result) for result in results]
    top_item = deepcopy(serialized_items[0]) if serialized_items else None
    return {
        "run_state_extensions": {
            "memory_results": {
                slot: {
                    "count": len(serialized_items),
                    "top_item": top_item,
                    "items": serialized_items,
                }
            }
        }
    }


def serialize_memory_result(result: MemoryResult) -> dict[str, object]:
    return {
        "memory_id": result.memory_id,
        "scope": result.scope,
        "score": result.score,
        "payload": deepcopy(result.payload),
        "source_ref": result.source_ref,
        "metadata": deepcopy(result.metadata),
    }
