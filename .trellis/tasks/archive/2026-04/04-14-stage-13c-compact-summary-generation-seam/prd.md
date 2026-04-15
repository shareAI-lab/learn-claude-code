# Stage 13C: Compact Summary Generation Seam

## Goal

Add a compact summary generation seam and prompt contract that can later be wired to a real LangChain model, without introducing automatic compaction or live model calls in tests.

## Concrete Benefit

* Context-efficiency: manual compact no longer depends only on externally supplied summary text in future wiring.
* Reliability: summary output formatting can be tested before runtime integration.
* Maintainability: summarization prompt construction and model invocation are isolated from CLI/session/auto-compact code.

## Requirements

* Add a deterministic prompt builder for compact summarization.
* Add a generation seam that accepts a summarizer object/callable and message dictionaries.
* Strip `<analysis>` and unwrap `<summary>` using the Stage 13A formatter.
* Keep the seam testable with fake summarizers.
* Do not call live models in tests.
* Do not introduce auto-compact or runtime middleware.

## Acceptance Criteria

* [ ] A compact summarizer seam exists under `coding_deepgent.compact`.
* [ ] The summarizer receives original messages plus one compact prompt message.
* [ ] Summary output is formatted through `format_compact_summary()`.
* [ ] Empty summary output is rejected.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* live OpenAI/LangChain model selection
* CLI summary generation option
* auto-compact thresholding
* SummarizationMiddleware integration
* transcript pruning
* prompt-too-long retry

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve reliability, context-efficiency, and maintainability.

The local runtime effect is: compact summary generation gets a dedicated prompt/model seam that preserves cc-haha's “text-only summary, strip analysis scratchpad” intent without copying the full compact runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Compact prompt | `/root/claude-code-haha/src/services/compact/prompt.ts::getCompactPrompt()` requires text-only summary and analysis/summary structure | generated summaries are structured and cleanly post-processed | local compact prompt builder | partial | Implement concise prompt contract |
| Summary formatting | `/root/claude-code-haha/src/services/compact/prompt.ts::formatCompactSummary()` strips `<analysis>` and unwraps `<summary>` | no scratchpad leaks into compact artifact | reuse 13A formatter | align | Implement through seam |
| Model invocation | `/root/claude-code-haha/src/services/compact/compact.ts::streamCompactSummary()` invokes a forked/streaming summary path | local code has a replaceable model seam | fakeable summarizer protocol | partial | Implement seam only |
| Retry and hooks | cc-haha handles prompt-too-long retry, hooks, restoration, telemetry | robust production compact | none now | defer | Requires later runtime stage |

## LangChain Boundary

Use:

* normal message dictionaries as model input
* a summarizer object with `invoke()` or a callable seam
* existing Stage 13A summary formatter

Avoid:

* custom query loop
* direct provider SDK use
* live model calls in tests
* automatic middleware before manual seam is proven

## Technical Approach

* Add `compact/summarizer.py`.
* Export prompt/seam helpers from `compact/__init__.py`.
* Add `tests/test_compact_summarizer.py`.
* Keep all behavior pure/fakeable.

## Test Plan

* Fake summarizer receives original messages + prompt message.
* `<analysis>` output is stripped.
* `<summary>` content is unwrapped.
* blank summarizer output raises a clear error.

## Checkpoint: Stage 13C

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `coding-deepgent/src/coding_deepgent/compact/summarizer.py` with:
  - `COMPACT_SUMMARY_PROMPT`
  - `build_compact_summary_prompt()`
  - `build_compact_summary_request()`
  - `generate_compact_summary()`
- Exported summarizer seam helpers from `coding-deepgent/src/coding_deepgent/compact/__init__.py`.
- Added `coding-deepgent/tests/test_compact_summarizer.py` covering:
  - prompt appending without mutating source messages
  - fake `.invoke()` summarizer support
  - callable summarizer support
  - `<analysis>` stripping and `<summary>` unwrapping
  - empty summary rejection

Verification:
- `pytest -q tests/test_compact_summarizer.py tests/test_compact_artifacts.py tests/test_message_projection.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/compact/summarizer.py src/coding_deepgent/compact/__init__.py tests/test_compact_summarizer.py`
- `mypy src/coding_deepgent/compact/summarizer.py src/coding_deepgent/compact/__init__.py`

cc-haha alignment:
- Source-backed intent came from:
  - `/root/claude-code-haha/src/services/compact/prompt.ts::getCompactPrompt()`
  - `/root/claude-code-haha/src/services/compact/prompt.ts::formatCompactSummary()`
  - `/root/claude-code-haha/src/services/compact/compact.ts::streamCompactSummary()`
- Aligned:
  - compact summary prompt asks for a text-only analysis/summary shape.
  - summary output is formatted through the same scratchpad-stripping boundary as 13A.
  - model invocation is isolated behind a fakeable summarizer seam.
- Deferred:
  - forked/streaming summarizer runtime.
  - live model selection.
  - auto-compact and prompt-too-long retry.
  - CLI-generated summary option.

LangChain architecture:
- Primitive used:
  - normal message dictionaries as summarizer input.
  - `.invoke()` or callable seam, compatible with LangChain-style model invocation and fake test doubles.
- Why no heavier abstraction:
  - 13C only needed the generation seam; wiring a live model or `SummarizationMiddleware` changes runtime behavior and should be planned separately.

Boundary findings:
- New issue handled:
  - compact summary generation needed its own prompt/request builder instead of being hidden inside CLI/session code.
- Residual risk:
  - no live summarizer wiring exists yet; manual compact can use user-supplied summaries, and generated summaries can be unit-tested through fake summarizers.
- Impact on next stage:
  - next safe work should be planned explicitly as either generated-summary CLI wiring, LangChain `SummarizationMiddleware` integration, or auto/reactive compact. These are separate product choices.

Decision:
- continue

Terminal note:
- Stage 13 v1 manual compact foundation is complete through 13A-13C. No further sub-stage should be started automatically without choosing the next compaction product path.

Reason:
- Tests, ruff, and mypy passed.
- The Stage 13 v1 scope now has boundary artifact, manual resume entry point, and summary generation seam.
- The next candidates would widen runtime behavior beyond the current approved v1 slice.
