# Domain Pack Standard Structure

Updated: 2026-04-11

This document defines the standard structure for a `domain pack`.

Its purpose is simple:

1. make every domain enter the platform in the same way
2. keep domain logic out of `core`
3. make future domains reusable, testable, and comparable

This document is intentionally practical.
It is meant to guide real code generation and repository growth.

## 1. What A Domain Pack Is

A domain pack is the platform's top-level extension unit for a concrete problem
space.

Examples:

1. `education`
2. `software_supply_chain`
3. future packs such as `research_ops`, `customer_support`, or `compliance_review`

A domain pack is not:

1. a new runtime
2. a replacement for `core`
3. a private tool system
4. a separate memory architecture
5. a one-off workflow script folder

A domain pack is:

`a structured package of domain-specific agents, workflows, tools, memory scopes, and evaluation assets that plugs into the shared platform kernel`

## 2. Design Goals

The standard structure must satisfy five goals:

1. fast landing for the first domain pack
2. clear boundaries with `core`
3. stable onboarding pattern for future domains
4. reusable evaluation and observation paths
5. low refactor pressure when the second and third domains arrive

## 3. Main Boundary Rule

The most important rule is:

`domain packs may extend the platform, but they may not mutate the platform core as a shortcut`

That means:

1. domain data should not be hard-coded into `core` models
2. domain rules should not be embedded into `RuntimeService`
3. domain tool logic should not bypass the tool layer
4. domain memory logic should not bypass the memory layer
5. domain evaluation should not bypass the evaluation scaffold

If a domain needs something new from the platform, it should be surfaced as an
explicit extension point, not quietly patched into core logic.

## 4. Standard Package Shape

Recommended package root:

`src/domain_packs/<domain_name>/`

Examples:

1. `src/domain_packs/education/`
2. `src/domain_packs/software_supply_chain/`

Recommended standard layout:

```text
src/domain_packs/<domain_name>/
|- __init__.py
|- pack.py
|- metadata.py
|- agents/
|  |- __init__.py
|  |- descriptors.py
|  `- implementations.py
|- workflows/
|  |- __init__.py
|  |- definitions.py
|  `- patterns.py
|- tools/
|  |- __init__.py
|  |- descriptors.py
|  `- adapters.py
|- memory/
|  |- __init__.py
|  |- scopes.py
|  `- helpers.py
|- policies/
|  |- __init__.py
|  `- profiles.py
|- evals/
|  |- __init__.py
|  |- cases.py
|  |- suites.py
|  `- scorers.py
`- docs/
   |- architecture-brief.md
   `- workflow-notes.md
```

This is the target shape.
The first domain pack does not need every file on day one, but it should grow
toward this structure rather than inventing a custom layout.

## 5. Minimal MVP Shape

For the first version of a domain pack, the truly required files are:

```text
src/domain_packs/<domain_name>/
|- __init__.py
|- pack.py
|- metadata.py
|- agents/
|  |- __init__.py
|  |- descriptors.py
|  `- implementations.py
|- workflows/
|  |- __init__.py
|  `- definitions.py
|- evals/
|  |- __init__.py
|  `- cases.py
`- docs/
   `- architecture-brief.md
```

This is the smallest shape that still preserves architectural discipline.

## 6. Responsibilities Of Each Part

### 6.1 `pack.py`

This is the assembly entry point of the domain pack.

It should be responsible for:

1. exposing domain metadata
2. exposing agent descriptors
3. exposing agent implementations
4. exposing workflows
5. exposing tool descriptors if needed
6. exposing evaluation assets

It should not be responsible for:

1. direct runtime orchestration logic
2. business behavior implementation
3. platform mutation

Think of `pack.py` as the domain pack's composition root.

### 6.2 `metadata.py`

This file defines identity and boundaries of the domain pack.

It should include:

1. domain name
2. pack version
3. summary
4. owner or maintainer
5. capability tags
6. optional maturity level

### 6.3 `agents/descriptors.py`

This file declares the domain's `AgentDescriptor` objects.

These descriptors should define:

1. `agent_id`
2. `version`
3. `role`
4. `executor_ref`
5. `implementation_ref`
6. `capabilities`
7. `tool_refs`
8. `memory_scopes`
9. `policy_profiles`

This file should stay declaration-only.

### 6.4 `agents/implementations.py`

This file contains the actual `AgentImplementation` classes.

These implementations should:

1. consume `ExecutionContext`
2. rely on `context.agent_binding`
3. use platform services through `context.services`
4. return standard `NodeExecutionResult`

They should not:

1. query the registry directly
2. resolve `agent_ref` themselves
3. persist state directly
4. mutate runtime internals

### 6.5 `workflows/definitions.py`

This file contains `WorkflowDefinition` declarations for the domain.

These workflows should:

1. use `agent_ref` for agent nodes
2. use tool nodes through platform tool references
3. use memory results through standard selector paths
4. express orchestration declaratively

### 6.6 `workflows/patterns.py`

This file is optional for the MVP, but recommended once the domain grows.

It should hold reusable workflow fragments such as:

1. plan-review loop
2. evidence collection pattern
3. approval handoff pattern
4. retrieval-enrich-summarize pattern

### 6.7 `tools/descriptors.py`

This file should declare domain-specific tools through the shared tool model.

### 6.8 `tools/adapters.py`

This file contains domain-specific adapter glue when the shared tool layer is
not enough by itself.

### 6.9 `memory/scopes.py`

This file standardizes domain memory namespaces.

Examples:

1. `domain:education`
2. `learner:{learner_id}`
3. `course:{course_id}`
4. `domain:software_supply_chain`
5. `component:{component_id}`

### 6.10 `memory/helpers.py`

This file contains helper functions that shape memory reads and writes for the
domain.

### 6.11 `policies/profiles.py`

Optional in early packs, but the right place for domain-level policy profile
labels.

### 6.12 `evals/cases.py`

This file contains `EvaluationCase` objects for the domain.

### 6.13 `evals/suites.py`

This file groups cases into domain-level evaluation suites.

If a domain is still small, it is acceptable to keep suite declarations in
`evals/cases.py` for a while, as long as the public pack surface still exposes
`get_eval_suites()` and the domain can move to a split file later without
changing the pack contract.

### 6.14 `evals/scorers.py`

This file contains domain-specific scorers when generic scorers are not enough.

### 6.15 `docs/architecture-brief.md`

This file is required.

Every domain pack should have a short architecture brief that explains:

1. what problem the pack solves
2. what its core agents are
3. what workflows it provides
4. what tools and memory scopes it relies on
5. what its evaluation loop covers

## 7. Standard Dependency Direction

The allowed dependency direction should be:

`domain pack -> core`

Not:

`core -> domain pack`

Inside the domain pack, the recommended dependency flow is:

1. `metadata` is leaf/simple declaration
2. `agents/descriptors` may depend on metadata constants
3. `agents/implementations` may depend on shared core contracts and domain helpers
4. `workflows/definitions` may depend on domain descriptors, memory scopes, and tool refs
5. `evals/*` may depend on workflows and public domain assets
6. `pack.py` may import all domain-pack public parts

## 8. Registration Model

Every domain pack should expose a single standard registration surface.

Recommended shape:

1. `get_metadata()`
2. `get_agent_descriptors()`
3. `get_agent_implementations()`
4. `get_workflow_definitions()`
5. `get_tool_descriptors()`
6. `get_eval_cases()`
7. optional `get_eval_suites()`

The shape should stay stable across domains even when the internals evolve.

## 9. Standard Runtime Entry Path

A domain pack should enter the platform through this path:

1. register agent descriptors in `AgentRegistry`
2. register workflows in `WorkflowProvider`
3. register tools in `ToolRegistry` when needed
4. provide implementations to `DomainAgentExecutor`
5. run workflows through standard `RuntimeService`
6. evaluate with standard evaluation scaffold

Anything outside this path should be treated as an exception and justified.

## 10. Domain Pack Rules For Agent Nodes

Inside domain workflows:

1. agent nodes should prefer `agent_ref`
2. agent node `executor_ref` should remain generic and platform-facing
3. domain-specific routing should happen through binding and implementation selection

Recommended style:

1. `executor_ref="agent.domain"`
2. `agent_ref="teacher_planner"`

## 11. Domain Pack Rules For Tool Usage

Domain packs should use shared tool entry points.

That means:

1. use `ToolDescriptor`
2. use standard tool invoker path
3. keep tool refs stable and explicit

If a tool call matters for observability, policy, replay, or eval, it should go
through the tool layer.

## 12. Domain Pack Rules For Memory Usage

Memory usage should be explicit and named.

Every domain pack should define:

1. domain-level scopes
2. entity-level scopes
3. retrieval conventions

Avoid:

1. ad hoc memory scope strings scattered across implementations
2. direct writes to `run_state.extensions` as a replacement for memory design

## 13. Domain Pack Rules For Evaluation

Every domain pack should ship with evaluation assets early.

The first domain pack should include at minimum:

1. one happy-path case
2. one edge-case or failure-path case
3. one domain-relevant scoring check

This matters because a domain pack is not only delivery.
It is also a platform validation instrument.

## 14. What A Domain Pack Must Not Do

A domain pack must not:

1. patch `RuntimeService`
2. redefine core state models
3. bypass `AgentRegistry` for agent nodes
4. bypass `ToolInvoker` for meaningful tool usage
5. bypass `MemoryProvider` for long-lived domain memory
6. bypass the evaluation scaffold if it expects regression support

If a domain repeatedly needs to break one of these rules, that is a signal to
improve platform extension points.

## 15. First Domain Pack Quality Bar

Before we call a domain pack "properly entered", it should satisfy:

1. at least one workflow uses `agent_ref`
2. at least one agent runs through `DomainAgentExecutor`
3. at least one tool or memory path is used through shared platform services
4. at least one evaluation case exists
5. the pack has an `architecture-brief.md`

This is the minimum architecture quality bar.

## 16. Prototype Usage Note

Meeting the first domain pack quality bar means a pack is suitable for:

1. local self-testing
2. architecture validation
3. regression evaluation
4. future multi-domain comparison

It does not automatically mean the pack is ready for:

1. production deployment
2. large-scale user traffic
3. operational SLAs
4. hardened external integrations

That distinction matters because the platform should support early domain
experimentation without forcing premature production complexity.

## 17. Future Optimization Space

This standard structure intentionally leaves room for future growth:

1. stronger policy-profile enforcement
2. reusable orchestration pattern modules
3. pack discovery and registration framework
4. domain pack loading and configuration
5. domain benchmarks and cross-pack comparisons

These are future optimizations.
They should not be prerequisites for the first domain pack.

## 18. Final Standard

A domain pack should be treated as:

`a structured extension package that declares domain agents, implementations, workflows, tools, memory scopes, and evaluation assets while relying on the shared platform kernel for execution`

That is the standard we should follow for every real domain we add.
