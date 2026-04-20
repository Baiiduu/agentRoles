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

## Current Single-Agent Gaps

`test_pro` is now a stronger single-agent coding pack than its original prototype form, but it is still not a fully mature Codex-like coding agent. When extending domain packs, treat the following gaps as active architecture constraints rather than small polish items.

### 1. Long-horizon task execution is still limited

The current agent is good at focused and local coding tasks, but it is not yet strong enough for long, multi-phase tasks that require repeated planning, verification, repair, and continuation across many steps.

### 2. Validation and repair are not yet a full closed loop

The agent can produce structured validation guidance, but the architecture is still weaker than it should be at:

- automatically choosing validation actions
- executing validation as a first-class workflow
- recovering from failed validation with a standard repair loop

### 3. Task memory is present, but still lightweight

`test_pro` now has task-oriented memory, but memory is still not rich enough to act like a full task kernel. In particular, it still needs stronger handling for:

- pending next steps
- failed-edit and failed-validation carryover
- stale-memory cleanup and compaction
- deeper policy consumption of remembered task state

### 4. Repository intelligence is still mid-level

The pack has moved beyond plain file reads and text search, but repository understanding is still not strong enough for larger or more structural tasks. It still needs stronger:

- symbol-level navigation depth
- impact analysis across files
- active-context management for larger changes

### 5. Policy must continue replacing prompt growth

Prompt growth is a temporary bridge, not the desired long-term architecture. As packs evolve, important behavior should move from prompt wording into:

- policy
- task state
- structured tools
- runtime contracts

If a capability only works because the prompt keeps getting longer, that is a signal the architecture is still incomplete.

### 6. Single-agent quality comes before orchestration

For this project, multi-agent orchestration is a later concern. The near-term priority is to make the single-agent kernel strong enough that orchestration becomes an amplifier rather than a workaround for weak execution.
