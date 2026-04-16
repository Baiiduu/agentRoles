# Education Domain Pack Architecture Brief

Updated: 2026-04-11

This document describes the current architecture of the platform's first real
domain pack:

`education`

Its purpose is still the same as when we started:

1. validate the platform with a real multi-agent domain
2. keep domain behavior out of `core`
3. prove that future domains can follow the same extension path

The important difference now is that the education pack is no longer only a
plan. It is an executable prototype with workflows, evaluations, and stable
registration surfaces.

## 1. Current Usage Position

The education pack is currently suitable for:

1. local self-testing
2. architecture validation
3. workflow iteration
4. regression evaluation
5. future cross-domain comparison

It is not yet positioned as:

1. a production education product
2. a hardened external-integration system
3. a large-scale runtime deployment target

That distinction is intentional. The current goal is to learn quickly without
hard-coding education assumptions into the kernel.

## 2. Primary Design Goal

The education domain pack should prove five things:

1. the platform can support structured multi-agent collaboration in a real domain
2. agent registry, bindings, and domain execution work end to end
3. workflow branching and remediation loops feel natural on the current runtime
4. evaluation assets can live inside a domain pack without forking the platform
5. the domain remains reusable instead of turning into a hidden core dependency

## 3. Boundary Rule

This education pack must remain:

`a domain pack built on the platform`

Not:

`the beginning of education-specific logic leaking into the platform core`

So this pack must not:

1. modify `RuntimeService` to add education behavior
2. add education-only fields into core state models
3. bypass `AgentRegistry`, `ToolInvoker`, or `MemoryProvider`
4. redefine orchestration semantics inside core modules
5. depend on private runtime shortcuts as its default execution path

If the education pack needs new platform capabilities later, those should be
added as explicit extension points, not hidden special cases.

## 4. Educational Scenario

The current pack is organized around one coherent learning loop:

`diagnose learner state -> plan next study steps -> generate practice -> review performance -> adapt the next step`

This scenario gives us:

1. planning
2. content generation
3. review
4. branching
5. iterative adaptation
6. domain evaluation

That is a strong first test for the platform because it exercises both linear
and conditional collaboration.

## 5. Current Agent Set

The current implementation uses five agents.

### 5.1 `learner_profiler`

Purpose:

1. organize learner goals, weaknesses, level, and preferences

Role in the pack:

1. creates the learner state summary that other agents consume

### 5.2 `curriculum_planner`

Purpose:

1. convert learner state into a staged learning plan

Role in the pack:

1. creates trajectory and milestones

### 5.3 `exercise_designer`

Purpose:

1. generate practice tasks, hints, and answer schema

Role in the pack:

1. turns learning intent into exercises
2. supports both initial practice and remediation design

### 5.4 `reviewer_grader`

Purpose:

1. analyze learner answers and classify mastery and misconceptions

Role in the pack:

1. closes the feedback loop
2. produces the signal used by remediation branching

### 5.5 `tutor_coach`

Purpose:

1. translate system results into learner-facing guidance

Role in the pack:

1. communicates plans, review outcomes, and next steps

## 6. Current Workflow Set

The education pack currently exposes three workflows.

### 6.1 `education.diagnostic_plan`

Purpose:

1. turn learner seed context into a learner profile, study plan, and guidance

Current node chain:

1. `profile_learner`
2. `plan_curriculum`
3. `coach_learner`

Primary outputs:

1. learner profile artifact
2. study plan artifact
3. learner guidance artifact

### 6.2 `education.practice_review`

Purpose:

1. generate practice, capture a learner submission, review it, and return coaching feedback

Current node chain:

1. `design_exercises`
2. `capture_submission`
3. `review_submission`
4. `coach_feedback`

Primary outputs:

1. exercise set artifact
2. submission artifact
3. review artifact
4. coaching artifact

### 6.3 `education.remediation_loop`

Purpose:

1. branch on learner mastery and either design remediation or allow progress guidance

Current node chain:

1. `design_initial_exercises`
2. `capture_attempt`
3. `review_attempt`
4. `decide_remediation_path`
5. if weak:
   `design_remediation_exercises -> coach_remediation_path`
6. otherwise:
   `coach_progress_path`

Primary outputs:

1. remediation decision artifact
2. remediation exercise artifact when needed
3. remediation or progress guidance artifact

This workflow is especially important because it validates condition nodes and
branch-driven multi-agent adaptation inside a real domain.

## 7. Collaboration Shape

The education pack uses a structured collaboration graph:

1. profiler establishes learner state
2. planner establishes trajectory
3. designer produces practice
4. reviewer evaluates outcomes
5. tutor translates results into learner guidance

This is intentionally not a free-form swarm.
It is a role-separated graph with explicit handoffs.

That makes it easier to:

1. evaluate
2. debug
3. compare future domain packs
4. avoid collapsing all logic into one oversized agent

## 8. Current Tool And Memory Direction

The pack already reserves stable references for future education tools.

Current tool refs in agent descriptors:

1. `education.curriculum_lookup`
2. `education.exercise_template_lookup`
3. `education.rubric_lookup`
4. `education.answer_normalizer`

Current memory scope direction:

1. `domain:education`
2. `learner:{learner_id}`
3. `session:{thread_id}`
4. `course:{course_id}`
5. `plan:{thread_id}`

This means the pack is structurally ready for richer tool and memory usage even
though the current prototype stays deliberately light on external integrations.

## 8.1 Current Tool Layer Status

The education pack now includes four real tool descriptors and local adapter
handlers:

1. `education.curriculum_lookup`
2. `education.exercise_template_lookup`
3. `education.rubric_lookup`
4. `education.answer_normalizer`

These tools currently use:

1. shared `ToolDescriptor`
2. shared `FunctionToolAdapter`
3. shared `RoutingToolInvoker`
4. education-local reference data and handlers under `src/domain_packs/education/tools/`

This is an important architectural milestone because the education domain is no
longer only reserving tool refs in descriptors. It now has actual tool assets
that can be registered and invoked through the platform tool layer.

## 8.2 Tool Boundary Rule

The education tool layer must keep the following split:

1. `descriptors.py` defines tool identity, schemas, and metadata
2. `adapters.py` provides local handlers and adapter wiring
3. `pack.py` only exposes tool descriptors to the outside
4. `core` remains the owner of tool invocation contracts and routing

This means the domain pack may define education-specific tools, but it must not:

1. create a private tool registry
2. bypass `ToolInvoker`
3. move runtime execution logic into the domain
4. encode orchestration semantics inside tool adapters

## 8.3 Why The First Tools Are Reference Tools

The first four tools are intentionally reference-oriented and read-only.

That choice is useful for this stage because it lets us validate:

1. tool registration
2. descriptor alignment with agent capability declarations
3. adapter wiring
4. future agent-tool integration patterns

without prematurely taking on:

1. network reliability
2. external credential management
3. production data integration
4. tool-side security hardening

So these tools are not placeholders, but they are deliberately prototype-grade.

## 8.4 Future Upgrade Path

When we later move from local reference tools to richer real tools, the
preferred upgrade path is:

1. keep the same stable `tool_ref`
2. replace or extend the education adapter layer
3. keep workflow and agent declarations stable
4. keep all invocation flow inside the shared tool layer

This is exactly the kind of separation we want for multi-domain extensibility.

## 9. Current Evaluation Coverage

The education pack now ships with executable evaluation assets.

Current evaluation cases:

1. `education.eval.diagnostic_plan`
2. `education.eval.practice_review`
3. `education.eval.remediation_weak`
4. `education.eval.remediation_strong`

Current evaluation suites:

1. `education.eval_suite.core_paths`
2. `education.eval_suite.remediation_paths`
3. `education.eval_suite.smoke`

Current evaluation model:

1. generic `EvaluationCase` and `EvaluationSuite` stay in `core`
2. education-specific seed injection stays in `EducationEvaluationDriver`
3. education-specific required node and event expectations stay in case metadata

This is exactly the kind of separation we want: domain-specific input shaping in
the domain pack, generic execution and scoring in the platform.

## 10. Why This Domain Is Good For First Validation

Education is still a strong first domain because it naturally exercises:

1. stateful collaboration
2. iterative memory use
3. planner-review loops
4. branching based on review outcomes
5. human-readable final outputs
6. regression-friendly evaluation scenarios

It is easier to reason about than a more operational domain while still being
rich enough to validate the platform.

## 11. Current Architecture Alignment

The education pack currently aligns with the platform rules in these important ways:

1. all education-specific behavior stays under `src/domain_packs/education/`
2. workflows use `agent_ref`
3. agent execution goes through `DomainAgentExecutor`
4. evaluation reuses the shared evaluation scaffold
5. the education-specific input bridge is isolated in `EducationEvaluationDriver`
6. `core` still does not know anything about learner-specific state fields

This alignment matters more than feature count because the long-term goal is to
support multiple domains without reshaping the kernel each time.

## 12. Main Risks To Watch

There are still a few risks we should actively avoid:

1. making one education agent too powerful and collapsing role separation
2. turning workflow nodes into giant free-form config blobs
3. scattering learner memory conventions across implementations
4. overfitting the platform around education-only assumptions
5. confusing prototype readiness with production readiness

## 13. What This Pack Should Teach The Platform

The education pack should help us learn:

1. whether the current binding model is enough for real domain use
2. whether memory scopes are expressive enough
3. whether current workflow modeling is natural for remediation loops
4. whether domain evaluation can stay inside the shared evaluation scaffold
5. whether tool and memory restrictions should be enforced more strongly later

That means the pack is both:

1. a domain experiment
2. a platform feedback instrument

## 14. Current Recommended Next Step

The best next step is no longer "start the pack".
That part is already done.

The best next step now is:

1. begin agent-tool integration for the education agents that already declare tool refs
2. keep iterating through self-testing rather than production hardening
3. continue refining docs and eval coverage as the pack grows

That keeps momentum high while still protecting the platform from premature
product complexity.
