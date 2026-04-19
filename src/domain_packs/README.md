# Domain Packs

`domain_packs` contains domain-scoped agent packs, shared operational tools, and the registration surface used by the runtime.

## Design Principles

### 1. Keep external entrypoints thin

Each domain pack should expose a small, stable public entrypoint such as:

- `metadata.py`
- `agents/descriptors.py`
- `agents/implementations.py`
- package `__init__.py`

These files should mainly provide registration and compatibility exports. They should not become the place where all runtime logic accumulates.

### 2. Split implementation by responsibility

When an agent implementation grows beyond a small and easily readable file, split it into internal modules by responsibility instead of continuing to expand one file.

Recommended pattern:

- `impl/shared.py`: normalization, parsing, small shared helpers
- `impl/policy.py`: tool policy and decision guards
- `impl/state.py`: task state, summaries, validation state
- `impl/llm_loop.py`: LLM and tool invocation helpers
- `impl/loop.py`: top-level invoke loop

The exact filenames can vary, but the boundary should stay clear and easy to follow.

### 3. Prefer decoupled modules over a large `implementations.py`

Do not let `agents/implementations.py` grow into a large mixed file containing:

- prompt assembly
- policy logic
- task state
- validation rules
- memory handling
- tool execution
- loop orchestration

Once those concerns start mixing in one place, the code becomes harder to review, test, and evolve.

### 4. Preserve compatibility while refactoring

When splitting implementation files:

- keep existing public import paths working when practical
- use thin re-export layers for compatibility
- avoid forcing unrelated callers and tests to change at the same time

This lets us improve structure without turning every refactor into a repo-wide migration.

### 5. Optimize for future extension

Domain packs should be easy to extend toward:

- stronger single-agent kernels
- shared harness capabilities
- future multi-agent orchestration

That means internal boundaries should make it obvious which logic is:

- domain-specific
- reusable across packs
- likely to move upward into the harness/runtime later

### 6. Treat readability as a product requirement

Code in domain packs should be easy to:

- read quickly
- test in isolation
- modify safely
- debug under pressure

If a file becomes difficult to understand in one pass, that is a signal to split it.

## Working Rule

Going forward, new domain-pack agent work should follow this default:

1. keep the public entry file small
2. add new behavior in focused internal modules
3. refactor before a single file becomes the bottleneck for understanding

`test_pro` is the reference example for this direction.
