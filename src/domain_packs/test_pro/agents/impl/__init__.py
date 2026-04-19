"""Internal implementation modules for the Test Pro coding agent.

Module split:
- `shared`: normalization, parsing, small shared helpers
- `policy`: tool preference and policy guards
- `state`: phase, working summary, validation, task state
- `llm_loop`: LLM/tool invocation helpers
- `loop`: top-level agent invoke loop
"""
