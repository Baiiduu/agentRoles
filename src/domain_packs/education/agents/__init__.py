"""Education agent declarations and implementations."""

from .descriptors import (
    EDUCATION_MEMORY_SCOPES,
    EDUCATION_TOOL_REFS,
    get_education_agent_descriptors,
)
from .implementations import get_education_agent_implementations

__all__ = [
    "EDUCATION_MEMORY_SCOPES",
    "EDUCATION_TOOL_REFS",
    "get_education_agent_descriptors",
    "get_education_agent_implementations",
]
