# Stage 12A: Context Payload Foundation

## Goal

Introduce a typed, bounded, testable dynamic context payload foundation for `coding-deepgent`, so todo, memory, task, session, and future subagent/mailbox context do not keep growing as ad hoc `SystemMessage` string fragments.

This stage is infrastructure-only and should prepare the product for later context projection, recovery, memory quality, task, and multi-agent upgrades.

## What I already know

* This is the first sub-stage of `Stage 12: Context and Recovery Hardening`.
* The parent readiness decision says advanced cc highlight work should wait until H04/H05/H06/H07 infrastructure is stronger.
* Existing local context injection is partial:
  - `PlanContextMiddleware` renders todos/reminders directly into a `SystemMessage`.
  - `MemoryContextMiddleware` renders memories directly into a `SystemMessage`.
  - `RuntimeContext` carries session/workdir/trusted_workdirs/entrypoint/agent_name/skill_dir/event_sink/hook_registry.
* Existing local prompt foundation is small and should remain small:
  - `PromptContext`
  - `build_default_system_prompt()`
  - `build_prompt_context()`
* cc-haha source shows attachment/context is a typed dynamic protocol, not just prompt string concatenation:
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/utils/queryContext.ts`
  - `/root/claude-code-haha/src/context.ts`
* LangChain docs frame context engineering as controlling model context, tool context, and lifecycle context through middleware.
* `langchain-architecture-guard` says the smallest viable shape should use middleware and avoid speculative wrapper layers.

## Assumptions

* Stage 12A should introduce a small typed context payload model, not a full cc-haha attachment clone.
* The first implementation should support existing todo and memory dynamic context only.
* Future payload kinds should be possible without changing every middleware.
* Rendering should be deterministic and bounded.
* Injection should fail soft: empty/no-op payloads should not change the model request.

## Requirements

* Add a product-local dynamic context payload foundation.
* Represent payloads with explicit fields:
  - `kind`
  - `text`
  - `source`
  - priority/order metadata if useful for deterministic rendering
* Provide bounded rendering helpers.
* Migrate `PlanContextMiddleware` and `MemoryContextMiddleware` to build context payloads and render through the shared helper.
* Preserve current user-visible behavior as much as possible:
  - todos still render as "Current session todos"
  - stale todo reminders still render
  - recalled memories still render as "Relevant long-term memory"
* Add deterministic tests for:
  - payload render output
  - max length / bounded output
  - no duplicate payload rendering
  - memory middleware uses shared payload rendering
  - todo middleware uses shared payload rendering
* Keep the implementation LangChain-native:
  - middleware remains `AgentMiddleware`
  - model request updates use `request.override(system_message=SystemMessage(...))`
  - no custom agent loop or query runtime

## Acceptance Criteria

* [ ] A context payload module exists with typed payload data and bounded render helpers.
* [ ] Existing todo context injection goes through the shared payload renderer.
* [ ] Existing memory context injection goes through the shared payload renderer.
* [ ] Tests prove bounded rendering and deterministic ordering.
* [ ] Tests prove duplicate payloads are not rendered twice in one injection pass.
* [ ] Existing app/tool binding tests still pass.
* [ ] No product code introduces a custom query loop or a cc-haha-style full attachment framework.

## Definition of Done

* Unit tests are added/updated for the new context payload foundation.
* Existing relevant tests continue to pass:
  - `tests/test_app.py`
  - `tests/test_memory_context.py`
  - `tests/test_memory_integration.py`
  - `tests/test_planning.py`
  - `tests/test_todo_domain.py`
* Lint/typecheck are run if available and scoped enough for this package.
* Product docs/status are updated if the implementation changes architecture-visible behavior.

## Out of Scope

* Full cc-haha attachment protocol parity
* Message projection
* Tool result projection or persistence
* Microcompact / autocompact / reactive compact
* Session resume changes
* Recovery brief
* Memory quality policy
* Subagent mailbox / team context payloads
* Coordinator mode
* Plugin marketplace behavior
* Permission classifier / rich HITL approval UI

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve context-efficiency, reliability, maintainability, and product parity.

The local runtime effect is: dynamic context is built through a typed, bounded, testable payload layer instead of each middleware appending raw text to the system prompt independently. If this does not reduce ad hoc prompt injection and make later context projection easier, it is not worth shipping.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Attachment as dynamic context protocol | `/root/claude-code-haha/src/utils/attachments.ts` defines many typed `Attachment` variants such as `nested_memory`, `relevant_memories`, `plan_mode`, `agent_listing_delta`, `task_status`, `teammate_mailbox` | avoid ad hoc untyped context injection | small `ContextPayload` model | partial | Implement a small local equivalent, not full parity |
| Attachment message conversion | `/root/claude-code-haha/src/utils/attachments.ts:createAttachmentMessage` wraps attachments as typed messages with UUID/timestamp | separate payload creation from model-message rendering | payload builder + renderer helper | partial | Render to LangChain `SystemMessage` blocks now; full message protocol later |
| Todo reminders | cc-haha produces `todo_reminder` attachments based on turns since TodoWrite | preserve bounded todo nudges | todo middleware payloads | align | Keep local behavior, change the internal rendering path |
| Task reminders/status | cc-haha has `task_reminder` / `task_status` attachment paths | future task/subagent context can share protocol | reserved payload kinds or extensible model | defer | Do not implement task payloads in 12A |
| Relevant memories | cc-haha relevant memory attachments include stable metadata to avoid cache churn | memory context should be bounded and deterministic | memory middleware payloads | partial | Keep simple rendered memories now; richer metadata later |
| Teammate mailbox | cc-haha mailbox messages are delivered as attachments | future multi-agent comms need payload boundary | none now | defer | Requires H13 work later |

### Non-goals

* Do not port the full TypeScript `Attachment` union.
* Do not add timestamps/UUIDs to every local payload unless needed for local behavior.
* Do not add task/subagent/mailbox context in this stage.
* Do not add LLM summarization or compaction.

### State boundary

* Short-term state remains in LangGraph state (`todos`, `rounds_since_update`, messages).
* Persistent memory remains in LangGraph store and memory domain.
* Context payloads are transient model-context render inputs, not persistent state by themselves.

### Model-visible boundary

The model should see the same meaningful text as before:

* current session todos
* todo reminders
* relevant long-term memory

The model should not see new implementation-specific payload metadata unless it is intentionally rendered.

### LangChain boundary

Use:

* `AgentMiddleware.wrap_model_call`
* `SystemMessage` content blocks
* small helper functions for payload rendering

Avoid:

* custom query runtime
* custom LangGraph graph nodes for this stage
* new stores/checkpointers
* prompt-builder service locator

## Technical Approach

Recommended minimal design:

* Add `coding_deepgent.context_payloads` or `coding_deepgent.context/` module.
* Define a small immutable payload dataclass, for example:
  - `kind: Literal["todo", "todo_reminder", "memory"]`
  - `text: str`
  - `source: str`
  - `priority: int = 100`
* Add helpers:
  - `render_context_payloads(payloads, max_chars=...) -> list[dict[str, str]]`
  - dedupe by `(kind, source, text)`
  - deterministic sort by `(priority, kind, source, text)`
  - trim oversized payload text with an explicit marker
* Update:
  - `todo/middleware.py` to emit payloads for todos/reminder before converting to `SystemMessage`
  - `memory/middleware.py` to emit payloads for rendered memory before converting to `SystemMessage`
* Add tests near existing context tests, likely:
  - `tests/test_context_payloads.py`
  - updates to `tests/test_planning.py`
  - updates to `tests/test_memory_integration.py`

## Research Notes

### Current local patterns

* `PlanContextMiddleware.wrap_model_call()` builds `extra_blocks` as raw dicts and appends them to `SystemMessage`.
* `MemoryContextMiddleware.wrap_model_call()` appends one memory text block directly to `SystemMessage`.
* `PromptContext` already separates base prompt, user/system context, append prompt, and memory context, but runtime middleware context does not share a payload model.

### Feasible approaches

**Approach A: Small shared payload renderer** (Recommended)

How it works:

* Add a tiny typed payload object and renderer.
* Existing middlewares continue to own their domain logic.
* The shared layer only owns dedupe, ordering, bounds, and conversion to content blocks.

Pros:

* Smallest useful infrastructure.
* Fits LangChain middleware.
* Avoids cc-haha attachment clone.
* Gives 12B/12C/12D a shared boundary.

Cons:

* Does not yet model full message lifecycle or compact boundaries.

**Approach B: Full attachment protocol model**

How it works:

* Create a richer local attachment union modeled after cc-haha.

Pros:

* More direct parity vocabulary.

Cons:

* Too much unused structure now.
* Higher risk of custom runtime drift.
* Likely to invite task/mailbox/compact work too early.

**Approach C: Keep current per-middleware raw SystemMessage injection**

How it works:

* Do nothing now; each middleware keeps appending raw strings.

Pros:

* No immediate code change.

Cons:

* Fails the infrastructure goal.
* Future memory/task/subagent context will repeat ad hoc injection.
* Harder to add projection/compaction invariants.

## Decision (ADR-lite)

**Context**: Stage 12A is meant to create the smallest shared dynamic-context boundary before projection, recovery, memory quality, task, and subagent work.

**Decision**: Use Approach A, a small shared payload renderer.

**Consequences**:

* Todo and memory remain domain-owned.
* Dynamic context gains a shared bounded rendering path.
* Full cc-haha attachment protocol remains deferred.
* Later Stage 12B can build projection/invariant work around a known context payload shape.

## Checkpoint: Stage 12A

Implemented:

* Added a shared `context_payloads` module with:
  - typed `ContextPayload`
  - deterministic ordering
  - dedupe
  - bounded truncation
  - merge helper for system-message content
* Updated todo middleware to emit payloads instead of raw ad hoc text blocks.
* Updated memory middleware to emit payloads instead of raw ad hoc text blocks.
* Added focused renderer tests and shared-path integration assertions.

Verification:

* `pytest -q coding-deepgent/tests/test_context_payloads.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_planning.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_context.py`
* `ruff check coding-deepgent/src/coding_deepgent/context_payloads.py coding-deepgent/src/coding_deepgent/todo/middleware.py coding-deepgent/src/coding_deepgent/memory/middleware.py coding-deepgent/tests/test_context_payloads.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_planning.py`
* `mypy coding-deepgent/src/coding_deepgent/context_payloads.py coding-deepgent/src/coding_deepgent/todo/middleware.py coding-deepgent/src/coding_deepgent/memory/middleware.py`

cc-haha alignment:

* Source files inspected:
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/utils/queryContext.ts`
  - `/root/claude-code-haha/src/context.ts`
* Aligned:
  - treat dynamic context as typed payloads rather than ad hoc prompt strings
  - separate payload creation from message rendering
  - keep todo and memory as domain-owned producers
* Deferred:
  - full attachment protocol
  - task/mailbox payloads
  - compact boundary payloads
* Do-not-copy:
  - UUID/timestamp-heavy attachment envelope
  - full cc-haha attachment union

LangChain architecture:

* Primitive used:
  - `AgentMiddleware.wrap_model_call`
  - `SystemMessage`
  - small shared render helper
* Why no heavier abstraction:
  - Stage 12A only needed a typed bounded seam for existing middleware.
  - A full attachment framework would have been speculative and would have widened scope into context projection and recovery too early.

Boundary findings:

* New issue:
  - Existing dynamic context middleware was duplicating `SystemMessage` block assembly, which would have multiplied future work for task/session/subagent context.
* Impact on next stage:
  - 12B can now build deterministic projection/invariant work around a shared payload seam instead of reverse-engineering two independent middleware patterns.

Decision:

* continue

Reason:

* Tests passed.
* cc-haha alignment for the scoped payload seam is sufficient.
* LangChain-native architecture stayed intact.
* The next sub-stage still holds and does not require a prerequisite split.
