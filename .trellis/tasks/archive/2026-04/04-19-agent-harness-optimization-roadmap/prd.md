# brainstorm: agent harness optimization roadmap

## Goal

Define the final target and staged roadmap for optimizing the `coding-deepgent`
agent harness after reviewing DeerFlow 2.0 patterns. The plan should improve
architecture, LangChain-native usage, subagent/runtime contracts, and future UI
readiness while avoiding implementation drift before the target is approved.

## What I already know

* The user is doing frontend work in parallel in another thread/workstream.
* This task should avoid frontend implementation changes by default and should
  define backend/runtime contracts that the frontend can consume later.
* Trellis planning principles require final goals before development.
* The current product mainline is `coding-deepgent/`; tutorial/reference layers
  are evidence only unless explicitly targeted.
* `coding-deepgent` already uses LangChain `create_agent` through
  `RuntimeAgentBuildRequest` and `create_runtime_agent`.
* Current subagents and fork agents are already created through the same runtime
  factory path, not a separate hand-rolled loop.
* DeerFlow 2.0 is useful as a reference for a productized agent harness, but not
  a wholesale target architecture.
* `.trellis/project-handoff.md` says the current next recommended task is final
  release validation / PR cleanup for the completed backend-next-step roadmap,
  not opening another backend feature family by default.
* `04-19-runtime-architecture-refactor-plan` is already terminal/approved:
  runtime roles/factory, subagent domain split, background hardening, and H13/H14
  readiness gate are complete.
* `04-19-frontend-architecture-cc-cli-reuse` is already terminal/approved:
  React/Ink CLI frontend v1, Python JSONL bridge, frontend protocol models,
  event mapping, tests, and docs are complete.
* `04-19-post-cli-frontend-v1-roadmap` already proposes a CLI Completion Pack
  before Web/HTML: real streaming, permission/HITL boundary, product command,
  and CLI polish.
* `coding_deepgent.frontend.protocol` already defines strict
  `FrontendEvent`/`FrontendInput` models for session, assistant deltas,
  tool events, permission events, todos/tasks, runtime events, recovery brief,
  and run terminal states.

## Assumptions (temporary)

* The optimization plan should primarily target final-goal alignment,
  acceptance gates, and sequencing across existing backend/frontend plans.
* Frontend-facing implementation should continue in the existing frontend
  workstream unless explicitly coordinated.
* The plan should be large enough to set a final target, but sliced into staged
  implementation tasks after approval.
* New backend optimization work should be justified by a concrete gap discovered
  during final validation, not by general similarity to DeerFlow.

## Open Questions

* Confirm final full test cleanup plan before moving into Task Workflow.

## Acceptance Targets

* A final target architecture is written before implementation begins.
* The roadmap distinguishes acceptance targets, planned features, planned
  extensions, and out-of-scope items.
* The roadmap explicitly avoids conflicting with parallel frontend work.
* DeerFlow learnings are mapped to `coding-deepgent` constraints instead of
  copied directly.

## Planned Features

* Compare current `coding-deepgent` agent harness boundaries with DeerFlow 2.0
  patterns.
* Identify high-value optimization areas in runtime, middleware order, tool
  projection, deferred tools, subagent/fork contracts, store/checkpointer usage,
  and event/protocol surfaces.
* Propose staged implementation slices with validation expectations.
* Record key architecture decisions as ADR-lite notes in this PRD.

## Planned Extensions

* Frontend implementation once the parallel frontend workstream converges.
* Web/Ink UI event rendering improvements beyond protocol contracts.
* Deep model-provider compatibility expansion unless selected as an MVP target.
* Wholesale DeerFlow parity.

## Requirements (evolving)

* Keep the plan scoped to `coding-deepgent/` and `.trellis/` by default.
* Do not implement code changes during brainstorm.
* Treat DeerFlow as a reference for proven patterns, not as the architecture to
  copy wholesale.
* Preserve the current LangChain-native direction: official tools, middleware,
  typed state/context, store/checkpointer, and `create_agent`.
* Avoid frontend file edits unless the user explicitly moves this task into that
  workstream.
* Do not reopen completed runtime reshape stages unless final validation finds a
  concrete regression or contract gap.
* Coordinate with the existing CLI frontend plan instead of creating a competing
  frontend roadmap.
* Any next implementation family must state the concrete function being changed,
  the user/system benefit, and why the complexity is worth adding now.
* The selected roadmap posture is validation-first release stabilization.
* Do not start CLI Completion Pack implementation or H13/H14 planning from this
  task unless the validation pass identifies them as the next approved lane.
* Phase 1 validation scope is Core Release Gate.
* Core Release Gate should validate current completed mainline readiness, not
  long-range architecture wishes.
* User now prefers to organize the test suite before running Core Release Gate.
* Core Release Gate should run after test scope/layers are clear so failures are
  easier to interpret.
* User selected full test cleanup before Core Release Gate.
* User selected domain subdirectories for the test layout.

## Acceptance Criteria

* [x] PRD includes `Acceptance Targets`, `Planned Features`, and
      `Planned Extensions`.
* [x] PRD includes a recommended roadmap with staged implementation slices.
* [x] PRD captures at least one ADR-lite decision about roadmap posture.
* [x] PRD lists likely impacted backend/runtime/Trellis files.
* [x] User confirms final target before implementation begins.
* [x] Tests are moved into domain subdirectories.
* [x] Test command references are updated for the new layout.
* [x] Cleaned test suite passes before Core Release Gate.

## Definition of Done (team quality bar)

* Tests added/updated for implemented slices when implementation begins.
* Lint / typecheck / CI green for implemented slices.
* Trellis specs updated if reusable runtime/tool/subagent contracts change.
* Rollout/rollback considered for risky runtime changes.
* Frontend coordination boundary respected.

## Out of Scope (explicit)

* Direct frontend implementation in this brainstorm task.
* Replacing `coding-deepgent` with DeerFlow architecture.
* Editing tutorial/reference assets unless explicitly requested.
* Starting implementation before final target approval.

## Research Notes

### DeerFlow reference observations

* DeerFlow uses `langgraph.json` to expose `lead_agent` and a checkpointer
  factory to LangGraph server.
* Its lead agent is assembled via LangChain `create_agent` with model, tools,
  middleware, system prompt, and typed state.
* Its subagents also create child `create_agent` instances, but with filtered
  tools, inherited runtime context, and side-task streaming events.
* Its useful local patterns include middleware order documentation, deferred
  tool discovery, model provider compatibility centralization, LangGraph SDK
  frontend streaming, and subtask progress events.
* Its less suitable patterns include heavy global config/file I/O in
  `make_lead_agent`, large system prompts, and product-specific upload/channel
  complexity.

### Constraints from this repo

* Current mainline is `coding-deepgent/`.
* Trellis docs are the canonical planning/spec layer.
* Architecture posture prefers high-value clean boundaries over smallest diffs.
* Planning targets must be explicit before non-trivial implementation.
* Existing runtime already has `RuntimeAgentBuildRequest`,
  `create_runtime_agent`, domain packages, tool capability contracts, subagent
  sidechain/resume logic, runtime pressure, memory, sessions, tasks, and hooks.
* Existing frontend work already has a protocol/bridge package and React/Ink CLI
  surface under `coding-deepgent/frontend/cli`.
* Existing project handoff warns not to reopen H13/H14/H21/H22 or conditional
  L5-a without a new source-backed PRD.

### Feasible roadmap postures

**Approach A: Validation-first release stabilization** (Recommended)

* How it works: treat DeerFlow learnings as review prompts and run a final
  readiness audit across runtime, subagent, tool projection, frontend protocol,
  and Trellis specs. Only open implementation tasks for concrete failed gates.
* Pros: matches current handoff, avoids duplicating completed work, protects the
  parallel frontend stream, and produces a clean final target before more code.
* Cons: less exciting than new features; may produce mostly tests/docs/cleanup.

**Approach B: CLI Completion Pack as next integrated implementation**

* How it works: continue the existing post-CLI plan and implement streaming,
  permission/HITL boundary, packaging, and polish.
* Pros: most user-visible improvement; aligns with frontend work already in
  progress and validates the event protocol for future Web.
* Cons: touches runtime/frontend boundary while another frontend workstream is
  active; needs coordination to avoid conflicts.

**Approach C: New multi-agent capability planning**

* How it works: use the completed runtime reshape as a base and start a new
  H13/H14-style mailbox/coordinator/team plan.
* Pros: advances deferred multi-agent architecture.
* Cons: explicitly not the current handoff recommendation; high risk of scope
  expansion before release stabilization and frontend completion.

## Expansion Sweep

### Future evolution

* In 1-3 months, the same backend event/runtime contracts should support
  React/Ink CLI, browser Web, and deeper multi-agent lifecycle.
* Deferred H13/H14 should start only after release validation and CLI protocol
  maturity prove the existing surfaces are stable.

### Related scenarios

* Runtime, frontend protocol, session/evidence, and tool projection should be
  reviewed together because UI visibility depends on backend events being
  meaningful and bounded.
* Existing Typer/Rich commands and React/Ink frontend should remain separate
  surfaces over the same runtime facts.

### Failure and edge cases

* A new broad optimization task could duplicate already-completed R1-R4 runtime
  reshape or conflict with CLI frontend work.
* Copying DeerFlow app-level patterns could reintroduce global config/prompt
  coupling that Trellis specs already discourage.
* Starting H13/H14 now could violate readiness gates if mailbox/coordinator
  semantics leak into `run_subagent`, `run_fork`, or background controls.

## Proposed Final Target

`coding-deepgent` should be a LangChain-native local coding agent harness with:

* one official `create_agent` construction seam for main/subagent/fork/future
  roles,
* explicit middleware/tool/state/context/store/checkpointer contracts,
* deferred/discoverable tool surfaces governed by capability metadata and
  shared policy,
* durable JSONL session/evidence/sidechain records separate from live
  projection state,
* React/Ink CLI and future Web consuming typed frontend events rather than
  terminal text,
* DeerFlow-informed product maturity checks without adopting DeerFlow's global
  config/prompt-heavy app coupling.

## Candidate Roadmap

### Phase 0: Final Goal And Gate Lock

* Confirm final target posture and out-of-scope items.
* Turn this PRD into the umbrella roadmap/gate.
* Do not implement product code.

### Phase 1: Validation-first Release Stabilization

* Audit existing runtime reshape, ToolSearch/deferred tools, frontend protocol,
  subagent/fork/background controls, and Trellis contracts.
* Add or tighten tests only where gates are missing.
* Produce a release-readiness decision: ship, fix concrete blockers, or split.
* Selected scope: Core Release Gate.

### Phase 2: CLI Completion Pack Coordination

* If selected after Phase 1, continue the existing CLI Completion Pack:
  streaming, permission/HITL boundary, product command, and polish.
* Keep Web/HTML outside this phase.

### Phase 3: Web/HTML Or Multi-Agent Planning

* Choose one after CLI protocol matures:
  * Web/HTML over the typed event stream.
  * H13/H14 mailbox/coordinator/team planning from the readiness gate.

## Decision (ADR-lite)

**Context**: Backend runtime reshape and CLI frontend v1 are already completed
or separately planned. DeerFlow review surfaced useful maturity patterns, but
the current handoff recommends release validation / PR cleanup rather than
opening another backend feature family by default.

**Decision**: Use Approach A, validation-first release stabilization, as the
umbrella optimization roadmap. Treat CLI Completion Pack as the next
implementation candidate only after release gates are explicit and frontend
coordination is clear.

**Consequences**: This avoids duplicating completed runtime/frontend work and
keeps future implementation tied to concrete failed gates. It may defer new
multi-agent features until the current product surface is stable.

## Confirmed Roadmap Posture

Selected by user: **Validation-first release stabilization**.

This task should now converge on a concrete validation gate plan. It should not
start implementation or redefine completed runtime/frontend work.

## Confirmed Phase 1 Scope

Selected by user: **Core Release Gate**.

Updated sequencing: run **Full Test Cleanup** first, then run Core Release
Gate.

Core Release Gate validates the current completed mainline for release
readiness. It does not implement CLI streaming/HITL, Web/HTML, H13/H14
multi-agent orchestration, or broad long-range architecture audits unless a core
gate fails and creates a concrete follow-up.

## Decision (ADR-lite): Full Test Cleanup Before Core Gate

**Context**: Core Release Gate depends on focused validation. If the test suite
is noisy, duplicated, stale, or poorly grouped, gate failures may be hard to
interpret and may create false product blockers.

**Decision**: Insert a full test-suite cleanup pass before running Core Release
Gate.

**Consequences**:

* The next implementation task should not immediately run all release gates.
* The cleanup pass should classify tests, identify duplication/noise/stale
  coverage, define smoke/focused/deep command groups, and clean up the suite
  before the release gate.
* Cleanup may include test file moves/renames, shared fixture extraction,
  command grouping docs/scripts, merging duplicated tests, and deleting stale
  tests after replacement coverage is explicit.
* Product behavior changes remain out of scope unless cleanup exposes a real
  blocker that must be fixed before tests can make sense.

## Full Test Cleanup Plan

### Acceptance Targets

* Test commands are grouped by purpose: `release smoke`, `domain focused`, and
  `deep regression`.
* Current tests that protect runtime/subagent/tool/session/frontend contracts
  are identified and preserved.
* No high-value regression coverage is deleted just to reduce test count.
* Duplicate, stale, slow, or over-broad tests are cleaned up or explicitly left
  with rationale.
* Core Release Gate command set is updated after test organization.
* Test cleanup itself ends with the cleaned suite green before Core Release Gate
  begins.

### Planned Features

* Inventory `coding-deepgent/tests/` by domain and risk.
* Map tests to the Core Gate Matrix.
* Identify repeated fake agents, fake runtimes, stores, fixtures, and command
  helpers that may deserve shared fixtures.
* Identify stale tests that verify old implementation details rather than
  current Trellis contracts.
* Produce a test-suite triage table in this PRD before Core Release Gate.
* Extract shared fixtures/helpers only when they remove real duplication without
  hiding test intent.
* Move or rename test files only when the new layout makes domain ownership and
  command selection clearer.
* Merge/delete stale or duplicate tests only after preserving the current
  contract coverage elsewhere.

### Initial Test Inventory

* `coding-deepgent/tests/` currently has 48 Python `test_*.py` files.
* `coding-deepgent` currently has no Makefile or pytest config file; test
  commands are mainly documented in Trellis specs/PRDs and run ad hoc.
* `coding-deepgent/pyproject.toml` declares dev dependencies but does not define
  test groups, pytest markers, or command aliases.
* Top filename clusters from a quick scan:
  * `memory*`: 6 files
  * `tool*`: 4 files
  * `runtime*`: 3 files
  * `frontend*`: 3 files
  * `compact*`: 3 files
  * `session*` / `sessions`: multiple files with large JSONL/session coverage
* High-reuse fake/fixture patterns appear across:
  * `FakeAgent`, `fake_create_agent`, and runtime factory monkeypatches
  * `JsonlSessionStore(tmp_path / "sessions-store")`
  * `InMemoryStore`
  * `ToolRuntime` / runtime context helpers
  * frontend bridge fake event streams
* Early judgment: the suite is not "too many tests" by count alone; the main
  risk is unclear layering, duplicated fake setup, and old stage tests that may
  verify implementation details rather than current contracts.
* Largest Python test files by size:
  * `test_subagents.py`
  * `test_runtime_pressure.py`
  * `test_sessions.py`
  * `test_cli.py`
  * `test_tool_system_middleware.py`
  These are the highest-risk cleanup targets and should not be split or reduced
  without preserving explicit contract coverage.

### Proposed Test Layers

* `release smoke`: small must-pass set for current release readiness.
* `domain focused`: tests selected by changed package/domain.
* `deep regression`: broad runtime/session/subagent/tool/frontend protocol
  checks for architecture changes.
* `legacy/noisy candidates`: tests that may be renamed, merged, moved, or
  deleted only after confirming coverage replacement.

### Selected Test Layout

Selected by user: **domain subdirectories**.

Target shape:

```text
coding-deepgent/tests/
  conftest.py
  fixtures/
    ...
  runtime/
    test_agent_runtime_service.py
    test_app.py
    test_runtime_events.py
    test_runtime_foundation_contract.py
    test_state.py
  subagents/
    test_subagents.py
  tool_system/
    test_tool_system_registry.py
    test_tool_system_middleware.py
    test_tool_search.py
    test_tool_result_storage.py
  filesystem/
    test_tools.py
  permissions/
    test_permissions.py
  sessions/
    test_sessions.py
    test_session_contributions.py
    test_session_memory_middleware.py
  compact/
    test_compact_artifacts.py
    test_compact_budget.py
    test_compact_summarizer.py
    test_message_projection.py
    test_runtime_pressure.py
  frontend/
    test_frontend_protocol.py
    test_frontend_bridge.py
    test_frontend_event_mapping.py
  memory/
    test_memory.py
    test_memory_backend.py
    test_memory_cli.py
    test_memory_context.py
    test_memory_integration.py
    test_memory_module_closeout.py
  tasks/
    test_tasks.py
    test_planning.py
    test_planning_renderer.py
    test_todo_domain.py
  extensions/
    test_mcp.py
    test_plugins.py
    test_skills.py
    test_hooks.py
  cli/
    test_cli.py
    test_renderers.py
    test_rendering.py
  config/
    test_config.py
    test_context_payloads.py
    test_logging.py
    test_prompting.py
    test_rules.py
  structure/
    test_structure.py
    test_contract.py
    test_architecture_reshape.py
```

This layout may be adjusted during inventory if a file clearly belongs in a
different domain. The cleanup pass should keep import paths stable from product
code and update Trellis test command references after moves.

Collection check after mechanical move:

```bash
pytest -q coding-deepgent/tests --collect-only
```

Result: `386 tests collected`.

### Planned Extensions

* CI matrix integration if current repo scripts need a broader cleanup.
* Performance tuning for slow tests after release gate passes.
* Cross-package test layout changes if frontend/Web grows.

### Out Of Scope

* Large product behavior changes.
* Removing regression tests without replacement.
* Refactoring runtime/subagent/tool code just to make tests easier.
* Broad CI restructuring unless a concrete release blocker is found.
* Changing public tool schemas or frontend protocol just to simplify tests.

### Cleanup Guardrails

* Every delete/merge must name the replacement coverage.
* Prefer moving duplicated setup into local/shared fixtures over weakening
  assertions.
* Preserve contract-focused assertions even if they look verbose.
* Do not turn focused unit tests into broad integration tests.
* Do not make tests depend on live network, API keys, or user-specific state.
* Keep product code edits minimal and only for real bugs found by cleanup.

### Cleanup Stages

1. Inventory and classify
   * Build a table of every test file, owning domain, gate mapping, and rough
     layer: smoke/focused/deep/legacy.
   * Identify shared fixture candidates and stale implementation-detail tests.

2. Create test organization surface
   * Add a lightweight test index/plan under Trellis or test docs.
   * Define command groups for release smoke, domain focused, and deep
     regression.
   * Prefer documenting commands first; add pytest markers or scripts only if
     they materially improve repeatability.

3. Mechanical cleanup
   * Move tests into domain subdirectories according to the selected layout.
   * Extract repeated fixtures/helpers when duplication is concrete.
   * Keep imports and command paths updated.

4. Coverage consolidation
   * Merge truly duplicated assertions.
   * Delete stale tests only when current contract coverage is retained.
   * Mark risky candidates as follow-up instead of forcing deletion.

5. Cleanup validation
   * Run affected focused tests first.
   * Run the full cleaned Python test suite if feasible.
   * Run TS frontend tests if frontend protocol/CLI test files are touched.

6. Proceed to Core Release Gate
   * Only after cleanup validation passes.

## Core Release Gate Plan

### Acceptance Targets

* Current `coding-deepgent` backend/runtime mainline has a source-backed
  release readiness verdict.
* Completed runtime reshape work is verified rather than reopened.
* Completed frontend protocol/bridge v1 is checked only as a backend contract
  surface, not as a new frontend implementation lane.
* DeerFlow learnings are converted into concrete gates: construction seam,
  middleware/tool/state boundaries, deferred tool discovery, subagent lifecycle,
  session/evidence continuity, and typed UI protocol.
* Any failed gate produces a small, concrete follow-up task with affected files,
  expected behavior, tests, and owner boundary.

### Planned Features

* Build a Core Release Gate checklist in this PRD.
* Run focused validation against current runtime/subagent/tool/session/frontend
  protocol surfaces.
* Compare validation results with Trellis contracts and update this PRD with a
  release-readiness verdict.
* If gaps are found, classify them as:
  * `blocker`: must fix before release,
  * `follow-up`: should be planned but does not block current release,
  * `deferred`: intentionally out of current scope.

### Planned Extensions

* CLI Completion Pack: streaming, permission/HITL, product command, CLI polish.
* Web/HTML over typed frontend event protocol.
* H13/H14 mailbox/coordinator/team runtime.
* Deep architecture audits for transcript identity, durable memory backend, and
  long-range Web/multi-agent evolution.

### Out Of Scope

* Implementing new frontend features.
* Implementing real streaming or HITL permission pause/resume.
* Implementing H13/H14 or changing subagent/fork schemas to support team
  semantics.
* Replacing LangChain/LangGraph seams.
* Copying DeerFlow application structure.

## Core Gate Matrix

### Gate 1: Runtime Construction Seam

Target:

* main/subagent/fork agent construction goes through
  `RuntimeAgentBuildRequest` and `create_runtime_agent`.
* no direct child/fork bypass of the project-local runtime factory seam.
* `create_agent` remains the official LangChain primitive behind that seam.

Evidence:

* `coding-deepgent/src/coding_deepgent/runtime/agent_factory.py`
* `coding-deepgent/src/coding_deepgent/agent_service.py`
* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/tests/runtime/test_agent_runtime_service.py`
* `coding-deepgent/tests/subagents/test_subagents.py`

Validation:

```bash
pytest -q coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/runtime/test_app.py
pytest -q coding-deepgent/tests/subagents/test_subagents.py
```

### Gate 2: Subagent/Fork/Background Boundaries

Target:

* `run_subagent`, `run_fork`, resume tools, and background controls keep their
  current bounded local semantics.
* mailbox/coordinator/team/Scratchpad fields do not leak into these schemas.
* sidechain/resume/evidence lineage remains durable and bounded.
* background runs preserve durable record vs runtime snapshot vs process-local
  handle separation.

Evidence:

* `coding-deepgent/src/coding_deepgent/subagents/`
* `coding-deepgent/src/coding_deepgent/sessions/`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

Validation:

```bash
pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/sessions/test_sessions.py
```

### Gate 3: Tool Capability And Deferred Discovery

Target:

* tool capability metadata remains five-factor complete.
* builtin name collisions are rejected.
* role/tool projection remains explicit.
* `ToolSearch` / `invoke_deferred_tool` goes through shared policy and
  middleware, including denied/error cases.
* MCP and advanced lifecycle tools remain deferred unless explicitly promoted.

Evidence:

* `coding-deepgent/src/coding_deepgent/tool_system/`
* `coding-deepgent/src/coding_deepgent/mcp/`
* `.trellis/spec/backend/tool-capability-contracts.md`

Validation:

```bash
pytest -q coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_system_middleware.py coding-deepgent/tests/tool_system/test_tool_search.py coding-deepgent/tests/extensions/test_mcp.py
```

### Gate 4: Session, Evidence, Recovery, And Runtime Pressure

Target:

* JSONL transcript/session/evidence remains the durable user-facing record.
* runtime pressure, compact/collapse projection, and tool-result persistence do
  not corrupt raw session history.
* recovery briefs expose bounded high-value evidence and state.
* runtime event evidence remains whitelisted and bounded.

Evidence:

* `coding-deepgent/src/coding_deepgent/sessions/`
* `coding-deepgent/src/coding_deepgent/compact/`
* `coding-deepgent/src/coding_deepgent/runtime/events.py`
* `.trellis/spec/backend/runtime-context-compaction-contracts.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

Validation:

```bash
pytest -q coding-deepgent/tests/sessions/test_sessions.py coding-deepgent/tests/compact/test_runtime_pressure.py coding-deepgent/tests/tool_system/test_tool_result_storage.py coding-deepgent/tests/runtime/test_runtime_events.py
```

### Gate 5: Frontend Protocol Contract

Target:

* Python frontend protocol models, JSONL bridge, and event mapping remain strict
  and synchronized with the React/Ink CLI contract.
* validation covers fake bridge and event mapping without entering CLI
  Completion Pack work.
* stdout remains event-only and logs remain out of the JSONL stream.

Evidence:

* `coding-deepgent/src/coding_deepgent/frontend/`
* `coding-deepgent/frontend/cli/src/bridge/`
* `coding-deepgent/frontend/protocol/README.md`
* `.trellis/spec/frontend/*`

Validation:

```bash
pytest -q coding-deepgent/tests/frontend/test_frontend_protocol.py coding-deepgent/tests/frontend/test_frontend_bridge.py coding-deepgent/tests/frontend/test_frontend_event_mapping.py
npm --prefix coding-deepgent/frontend/cli run typecheck
npm --prefix coding-deepgent/frontend/cli test
```

### Gate 6: Trellis Contract Alignment

Target:

* `.trellis/project-handoff.md` and backend/frontend specs match the actual
  implemented state.
* completed stages are not reopened by vague "closer to DeerFlow/cc" language.
* next recommended work remains release validation / cleanup unless a concrete
  gate fails.

Evidence:

* `.trellis/project-handoff.md`
* `.trellis/spec/backend/index.md`
* `.trellis/spec/frontend/index.md`
* `.trellis/tasks/04-19-*`

Validation:

* Manual spec/readiness review recorded in this PRD.
* No code change required unless a mismatch creates a concrete release risk.

## Phase 1 Execution Plan

1. Full Test Cleanup
   * Inventory test files and map them to domains/gates.
   * Produce recommended command groups.
   * Extract shared fixtures/helpers where they clearly reduce duplication.
   * Move/rename/merge/delete stale or duplicate tests only with replacement
     coverage identified.
   * Validate the cleaned suite before the release gate.

2. Preflight
   * Record branch/status and dirty worktree caveats.
   * Identify unrelated changes to avoid touching.

3. Focused Test Pass
   * Run the gate commands above in logical groups.
   * Prefer focused tests over broad suite unless a failure suggests wider risk.

4. Contract Review
   * Compare implemented state with Trellis backend/frontend contracts.
   * Check for stale claims, duplicated docs, or completed tasks that should not
     be reopened.

5. Gap Classification
   * For each failed gate, classify as `blocker`, `follow-up`, or `deferred`.
   * Do not fix during validation unless the issue is tiny, isolated, and clearly
     within release readiness.

6. Release Verdict
   * Write one of:
     * `READY`: no blocking gaps,
     * `READY_WITH_FOLLOW_UPS`: non-blocking gaps remain,
     * `NOT_READY`: one or more blockers require a scoped task.

## Validation Command Set

Primary focused validation:

```bash
pytest -q coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/runtime/test_app.py
pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/sessions/test_sessions.py
pytest -q coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_system_middleware.py coding-deepgent/tests/tool_system/test_tool_search.py coding-deepgent/tests/extensions/test_mcp.py
pytest -q coding-deepgent/tests/compact/test_runtime_pressure.py coding-deepgent/tests/tool_system/test_tool_result_storage.py coding-deepgent/tests/runtime/test_runtime_events.py
pytest -q coding-deepgent/tests/frontend/test_frontend_protocol.py coding-deepgent/tests/frontend/test_frontend_bridge.py coding-deepgent/tests/frontend/test_frontend_event_mapping.py
npm --prefix coding-deepgent/frontend/cli run typecheck
npm --prefix coding-deepgent/frontend/cli test
```

Lint/type check if files are edited:

```bash
ruff check <touched-python-files>
mypy <touched-python-files>
```

## Final Confirmation Draft

**Goal**: validate the current completed `coding-deepgent` mainline for release
readiness using a Core Release Gate, informed by DeerFlow review but not copying
DeerFlow or opening new feature work.

**Requirements**:

* Validate runtime construction, subagent/fork/background boundaries,
  tool/deferred discovery, session/evidence/recovery/runtime pressure, frontend
  protocol, and Trellis contract alignment.
* Do not implement CLI streaming/HITL, Web/HTML, or H13/H14 as part of this
  task.
* Convert any failed gate into a concrete blocker/follow-up/deferred decision.
* Preserve the parallel frontend workstream boundary.

**Implementation Plan**:

* Task Workflow Phase 2 will configure backend/fullstack validation context.
* Phase 3 will first organize/triage tests, then run the Core Release Gate
  validation pass and update this PRD with the release verdict.
* Product code edits happen only if a small release-blocking issue is found and
  can be fixed safely within this scope; otherwise create a follow-up task.

## Technical Notes

* Read `.trellis/spec/guides/planning-targets-guide.md`.
* Read `.trellis/spec/guides/architecture-posture-guide.md`.
* Read `.trellis/spec/guides/mainline-scope-guide.md`.
* Prior DeerFlow source review used `/tmp/deer-flow-codex-review`.

## Checkpoint: Full Test Cleanup And Core Release Gate

State:

* terminal

Verdict:

* READY_WITH_FOLLOW_UPS

Implemented:

* Moved 48 Python product test files from flat `coding-deepgent/tests/` into
  domain subdirectories.
* Kept root `coding-deepgent/tests/conftest.py` as the shared no-network and
  `PYTHONPATH` setup.
* Added `coding-deepgent/tests/README.md` with domain layout, release smoke,
  focused, and deep regression command groups.
* Updated current Trellis specs/plans/tasks references from old flat test paths
  to the new domain paths. Archived historical task records were left intact.
* Fixed moved root-path assumptions in structure/runtime/todo tests.
* Fixed stale memory CLI tests to patch the current `coding_deepgent.app`
  `build_container` seam instead of the old `coding_deepgent.cli` seam.
* Removed stale unused imports caught by lint in
  `tests/memory/test_memory_module_closeout.py`.

Validation:

* `pytest -q coding-deepgent/tests --collect-only` -> 386 tests collected.
* `pytest -q coding-deepgent/tests` -> 386 passed.
* `pytest -q tests/runtime tests/subagents tests/tool_system tests/sessions tests/frontend`
  from `coding-deepgent/` -> 156 passed.
* `ruff check coding-deepgent/tests` -> passed.
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed.
* `npm --prefix coding-deepgent/frontend/cli test` -> 2 files / 8 tests passed.
* Current Trellis/spec/plan search for active old flat test paths returned no
  matches.

Core Gate Result:

* Runtime construction seam: passed by moved runtime/app/subagent tests.
* Subagent/fork/background boundaries: passed by moved subagent/session tests.
* Tool capability and deferred discovery: passed by moved tool system and MCP
  tests.
* Session/evidence/recovery/runtime pressure: passed by moved sessions/compact
  tests and full suite.
* Frontend protocol contract: passed by moved frontend Python tests plus TS
  typecheck/tests.
* Trellis contract alignment: active references updated to new test layout.

Follow-ups:

* Consider a separate low-risk fixture extraction pass for repeated fake agent,
  fake runtime, `JsonlSessionStore`, and `InMemoryStore` setup after release
  gate work is committed.
* Consider adding pytest markers or a lightweight command wrapper only if the
  README command groups prove insufficient during repeated use.
* Existing broad dirty worktree contains unrelated prior changes; release verdict
  here covers the test cleanup/core gate surfaces, not the entire uncommitted
  branch state.
