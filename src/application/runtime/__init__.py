__all__ = ["AgentRuntimeContextFacade"]


def __getattr__(name: str):
    if name == "AgentRuntimeContextFacade":
        from .agent_runtime_context_service import AgentRuntimeContextFacade

        return AgentRuntimeContextFacade
    raise AttributeError(name)
