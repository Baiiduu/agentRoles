"""Education tool descriptors and local adapter wiring."""

from .adapters import (
    build_education_function_tool_adapter,
    register_education_tool_handlers,
)
from .constants import EDUCATION_TOOL_REFS
from .descriptors import get_education_tool_descriptors

__all__ = [
    "EDUCATION_TOOL_REFS",
    "build_education_function_tool_adapter",
    "get_education_tool_descriptors",
    "register_education_tool_handlers",
]
