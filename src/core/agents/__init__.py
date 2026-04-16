"""Agent registry reference models and in-memory implementation."""

from .bindings import ResolvedAgentBinding, ResolvedWorkflowBindings
from .implementation import AgentImplementation
from .models import AgentDescriptor, AgentQuery, AgentStatus, split_agent_ref
from .registry import InMemoryAgentRegistry
from .resolver import RegistryBackedAgentBindingResolver

__all__ = [
    "AgentDescriptor",
    "AgentImplementation",
    "AgentQuery",
    "AgentStatus",
    "InMemoryAgentRegistry",
    "RegistryBackedAgentBindingResolver",
    "ResolvedAgentBinding",
    "ResolvedWorkflowBindings",
    "split_agent_ref",
]
