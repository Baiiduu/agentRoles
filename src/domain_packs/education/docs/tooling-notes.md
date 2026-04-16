# Education Tooling Notes

Updated: 2026-04-11

This document explains the current education tool layer and how it should be
extended.

## 1. Current Tool Set

The education domain pack currently exposes four tools:

1. `education.curriculum_lookup`
2. `education.exercise_template_lookup`
3. `education.rubric_lookup`
4. `education.answer_normalizer`

These tools are registered as shared `ToolDescriptor` objects and can be wired
through the shared platform tool layer.

## 2. Current Implementation Shape

The implementation is intentionally split into two parts:

1. [descriptors.py](E:/大三下/need%20to%20learn/agentsRoles/src/domain_packs/education/tools/descriptors.py)
2. [adapters.py](E:/大三下/need%20to%20learn/agentsRoles/src/domain_packs/education/tools/adapters.py)

Responsibilities:

1. `descriptors.py` defines identity, schema, provider metadata, and tags
2. `adapters.py` defines local reference handlers and adapter registration

This split matters because the descriptor contract should stay stable even if we
replace local handlers with real external adapters later.

## 3. Current Invocation Path

The intended execution path is:

1. domain pack exposes tool descriptors
2. descriptors are registered in `ToolRegistry`
3. handlers are registered in `FunctionToolAdapter`
4. calls go through `RoutingToolInvoker`
5. runtime and tool observability remain in the shared platform layer

The education tool layer should not bypass this path.

## 4. Why These Tools Are Read-Only

All current education tools are read-only reference tools.

This is deliberate.

It lets us validate:

1. tool registration
2. descriptor quality
3. shared adapter wiring
4. future agent-tool integration

without coupling the education pack to:

1. external APIs
2. unstable remote services
3. credentials and deployment concerns

## 5. Current Reference Data Role

The local reference data in [adapters.py](E:/大三下/need%20to%20learn/agentsRoles/src/domain_packs/education/tools/adapters.py)
is not meant to become a hidden product database.

Its role is only to provide:

1. stable prototype responses
2. deterministic tests
3. a realistic shape for future tool outputs

If education tooling later needs a real content source, we should swap the
adapter implementation, not push more product logic into static dictionaries.

## 6. Boundary Rules

The education tool layer must not:

1. implement its own registry
2. implement its own runtime dispatch
3. write directly into runtime state
4. smuggle orchestration decisions into tool handlers
5. redefine shared tool contracts

The education tool layer may:

1. define domain-specific `tool_ref` values
2. define domain-specific schemas
3. define domain-specific provider metadata
4. provide domain-specific handler logic

## 7. Recommended Next Step

The next step for education tooling is:

1. integrate these tools into the education agent implementations that already declare them

The first likely integrations are:

1. `learner_profiler -> curriculum_lookup`
2. `curriculum_planner -> curriculum_lookup`
3. `exercise_designer -> exercise_template_lookup`
4. `reviewer_grader -> rubric_lookup` and `answer_normalizer`

That will let the education agents become more realistic without changing the
platform core.
