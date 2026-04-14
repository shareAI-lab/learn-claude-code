# Stage 14A: Explicit Generated Summary CLI Wiring

## Goal

Wire the Stage 13C compact summarizer seam into an explicit user-triggered CLI path so a resumed session can generate a compact summary and continue from a compacted history.

## Concrete Benefit

* Context-efficiency: users no longer have to hand-write `--compact-summary` to reduce resume context.
* Reliability: generated summaries still pass through the Stage 13C formatter and Stage 13A compact artifact boundary.
* Maintainability: live model wiring remains isolated in CLI/service seams and does not introduce auto-compact or transcript pruning.

## Requirements

* Add an explicit CLI option for generated manual compact summary.
* Keep existing `--compact-summary` behavior unchanged.
* Reject using user-supplied summary and generated summary together.
* Reject generated summary without `--prompt`.
* Use Stage 13C `generate_compact_summary()` seam.
* Reuse Stage 13B `compacted_continuation_history()`.
* Keep compaction user-triggered only.
* Do not mutate session transcript or state beyond the normal continuation prompt recording.
* Add tests with fake summarizers / monkeypatching; no live model tests.

## Acceptance Criteria

* [ ] `sessions resume --prompt ... --generate-compact-summary` generates summary through the compact seam and uses compacted continuation history.
* [ ] `--compact-summary` and `--generate-compact-summary` are mutually exclusive.
* [ ] `--generate-compact-summary` without `--prompt` fails clearly and does not call the run path.
* [ ] Optional compact instructions are passed to the summarizer seam.
* [ ] Focused CLI/compact tests pass.
* [ ] Ruff and mypy pass on changed files.

## Definition of Done

* No auto-compact trigger is introduced.
* No transcript pruning is introduced.
* No prompt-too-long retry is introduced.
* No LangChain `SummarizationMiddleware` is introduced.
* No live LLM tests are introduced.

## Out of Scope

* automatic token thresholds
* reactive compact
* prompt-too-long retry
* transcript compact records / delete semantics
* pre/post compact hooks
* post-compact file/skill/tool restoration
* background session memory extraction

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve context-efficiency, long-session continuity, and product parity.

The local runtime effect is: a user can explicitly request a generated compact summary for resume continuation, while the implementation still preserves LangChain-native message history and avoids automatic runtime behavior.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Compact prompt | `/root/claude-code-haha/src/services/compact/prompt.ts::getCompactPrompt()` uses strict text-only compact instructions and summary formatting | generated summaries follow a stable contract | Stage 13C prompt/seam | partial | Reuse local seam |
| Summary invocation | `/root/claude-code-haha/src/services/compact/compact.ts::streamCompactSummary()` invokes a summarizer with conversation messages + compact prompt | manual compact can generate summary instead of requiring user text | explicit CLI generated summary path | partial | Implement user-triggered path only |
| Post-compact artifact | `/root/claude-code-haha/src/services/compact/compact.ts::buildPostCompactMessages()` returns boundary/summary/recent messages | compacted continuation has stable boundary and recent tail | Stage 13A/13B compacted continuation | align | Reuse existing helper |
| Prompt-too-long retry | `compactConversation()` retries compaction after prompt-too-long by dropping old message groups | robust fallback if summary request is too large | none | defer | Explicitly out of scope |
| Auto compact | cc-haha auto/micro/reactive compact paths | proactive context pressure management | none | defer | Later stage |

## LangChain Boundary

Use:

* Stage 13C fakeable summarizer seam.
* Normal `.invoke()` model interface for live use.
* Existing message dictionaries and CLI service boundary.

Avoid:

* LangChain `SummarizationMiddleware` because it persists/replaces state automatically.
* Custom query runtime.
* Automatic background compaction.
* Provider-specific retry/cache code.

## LangChain Docs Consulted

* `/oss/python/langchain/short-term-memory`
* `/oss/python/langchain/context-engineering`
* `/oss/python/langgraph/add-memory`

Local decision:

LangChain summarization middleware is appropriate for later persistent lifecycle summarization, but 14A is an explicit CLI continuation path. Therefore use the existing fakeable summarizer seam instead of adding middleware.

## Technical Approach

* Add `cli_service.generated_compacted_continuation_history()`.
* Add CLI options:
  - `--generate-compact-summary`
  - `--compact-instructions`
* In CLI, call `build_openai_model()` only when the generated summary flag is explicitly present.
* Preserve `--compact-summary` for user-provided summaries.
* Add focused CLI tests that monkeypatch `build_openai_model()`.

## Test Plan

* Generated compact summary path uses fake summarizer and compacted history.
* Generated compact summary and manual summary conflict test.
* Generated summary without prompt test.
* Compact instructions passed to fake summarizer.
* Existing manual summary and non-compact resume tests still pass.

## Checkpoint: Stage 14A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `cli_service.generated_compacted_continuation_history()` to generate a compact summary through the Stage 13C summarizer seam and then reuse Stage 13B compacted continuation history.
- Added explicit CLI options to `sessions resume`:
  - `--generate-compact-summary`
  - `--compact-instructions`
- Preserved existing `--compact-summary` behavior for user-provided summaries.
- Added validation:
  - compact options require `--prompt`
  - `--compact-summary` and `--generate-compact-summary` are mutually exclusive
  - `--compact-instructions` requires `--generate-compact-summary`
- Added fake-summarizer CLI tests; no live LLM tests were introduced.

Verification:
- `pytest -q tests/test_cli.py tests/test_compact_summarizer.py tests/test_compact_artifacts.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py tests/test_cli.py`
- `mypy src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/compact/prompt.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
- Aligned:
  - user-triggered compact can now call a summarizer over conversation history plus a compact prompt.
  - generated summary is formatted through the same `<analysis>` stripping and `<summary>` unwrapping contract.
  - post-summary continuation reuses compact boundary + summary + preserved tail.
- Deferred:
  - stream/fork summarizer runtime.
  - prompt-too-long retry.
  - pre/post compact hooks.
  - auto/reactive compact.
  - transcript pruning.

LangChain architecture:
- Primitive used:
  - normal `.invoke()`-style summarizer seam via Stage 13C.
  - existing CLI/service boundaries and normal message history continuation.
- Why no heavier abstraction:
  - LangChain `SummarizationMiddleware` persists/replaces state automatically; 14A is explicit CLI continuation and intentionally non-destructive.

Boundary findings:
- New issue handled:
  - `--compact-instructions` without generated compact summary would otherwise be ambiguous, so it is rejected.
- Residual risk:
  - live summarizer quality and prompt-too-long handling are not covered yet; this stage only wires the explicit generated-summary path.
- Impact on next stage:
  - Next work should be explicitly chosen as either live/manual smoke coverage, persistent compact transcript semantics, or auto/reactive compact. These should not be silently bundled into 14A.

Decision:
- continue

Terminal note:
- Stage 14A completes the requested generated manual compact slice. No further sub-stage is started automatically because the next options widen product behavior beyond the current explicit user-triggered scope.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside explicit generated manual compact wiring.
- No auto-compact, transcript pruning, prompt-too-long retry, or live LLM tests were introduced.
