# Stage 15A: Non-Destructive Compact Transcript Records

## Goal

Add append-only compact transcript records so manual compaction events are durably visible in the session JSONL without deleting, pruning, or rewriting original transcript messages.

## Concrete Benefit

* Recoverability: future resume/audit flows can tell that a compacted continuation happened and inspect the compact summary.
* Safety: compact persistence does not mutate or delete the raw transcript.
* Testability: compact transcript semantics are deterministic and covered before any auto/reactive compact work.

## Requirements

* Add a `compact` JSONL record type.
* Load compact records into `LoadedSession` separately from `history`.
* Add `compact_count` to `SessionSummary`.
* Preserve current `history` behavior: compact records must not appear as user/assistant messages.
* Preserve state snapshot behavior.
* When `run_prompt_with_recording()` receives synthetic compact artifact messages, append one compact record before recording the continuation prompt.
* Do not persist synthetic resume context or compact artifact messages as normal message records.
* Do not delete, prune, or rewrite transcript records.

## Acceptance Criteria

* [ ] `JsonlSessionStore.append_compact()` appends a valid compact JSONL record.
* [ ] `load_session()` returns compact records separately as `loaded.compacts`.
* [ ] `loaded.history` remains only real user/assistant message records.
* [ ] `loaded.summary.compact_count` reflects valid compact records.
* [ ] Invalid/foreign compact records are ignored.
* [ ] A compacted CLI continuation records a compact record without skewing message indexes.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* auto-compact
* prompt-too-long retry
* transcript deletion/pruning
* replacing loaded history with compact summary on resume
* post-compact file/skill/tool restoration
* live LLM summarizer tests

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability, auditability, and long-session continuity.

The local runtime effect is: compact events become durable transcript metadata, while the raw session transcript remains intact and reloadable.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Compact boundary metadata | `/root/claude-code-haha/src/services/compact/compact.ts` creates compact boundary and summary messages before returning post-compact messages | compacted continuation has durable boundary/summary information | append-only `compact` JSONL record | partial | Implement record now |
| Transcript metadata continuity | `/root/claude-code-haha/src/services/compact/compact.ts` re-appends session metadata around compaction so resume display can recover context | local sessions can audit compact events later | `LoadedSession.compacts` and `SessionSummary.compact_count` | partial | Implement now |
| Transcript pruning | `/root/claude-code-haha/src/utils/sessionStorage.ts` has compact-boundary-aware loading/pruning/relinking logic | old messages may be skipped after a boundary | none now | defer | Explicitly out of scope |
| Tool-result/file restoration | cc-haha restores attachments/files/skills after compaction | richer post-compact context | none now | defer | Later stage |

## LangChain Boundary

Use:

* existing session JSONL store seam
* normal LangChain message history continuation
* compact artifact metadata from Stage 13

Avoid:

* LangChain `SummarizationMiddleware`
* automatic state replacement
* transcript deletion or `RemoveMessage`
* provider-specific retry/cache code

## LangChain Docs Consulted

* `/oss/python/langchain/short-term-memory`
* `/oss/python/langchain/context-engineering`
* `/oss/python/langgraph/add-memory`

Local decision:

LangChain summarization can persistently replace old messages, but 15A is append-only transcript metadata. Persistent state replacement and automatic summarization remain deferred.

## Technical Approach

* Extend `sessions/records.py` with:
  - `COMPACT_RECORD_TYPE`
  - `SessionCompact`
  - `make_compact_record()`
* Extend `JsonlSessionStore` with:
  - `append_compact()`
  - `_coerce_compact()`
  - `LoadedSession.compacts`
  - `SessionSummary.compact_count`
* Extend Stage 13 compact artifact messages with compact metadata so `sessions.service` can detect compacted continuations.
* Update `run_prompt_with_recording()` to append a compact record once when compact metadata is present in synthetic history.
* Extend tests in:
  - `tests/test_sessions.py`
  - `tests/test_cli.py`
  - `tests/test_compact_artifacts.py`

## Test Plan

* Compact record roundtrip and history separation.
* Invalid compact records ignored.
* Compacted continuation writes compact record and preserves real message indexes.
* Existing Stage 13/14 compact tests still pass.

## Checkpoint: Stage 15A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added append-only compact transcript records:
  - `COMPACT_RECORD_TYPE = "compact"`
  - `SessionCompact`
  - `make_compact_record()`
  - `JsonlSessionStore.append_compact()`
- Extended session loading:
  - `LoadedSession.compacts`
  - `SessionSummary.compact_count`
  - invalid/foreign compact records are ignored
  - compact records do not enter `LoadedSession.history`
- Extended compact artifact messages with `coding_deepgent_compact` metadata for boundary and summary messages.
- Added `compact_record_from_messages()` so `sessions.service.run_prompt_with_recording()` can detect synthetic compacted histories.
- Updated `run_prompt_with_recording()` to append one compact record before recording the continuation user prompt when compact artifact metadata is present.
- Fixed compacted continuation `message_index` baseline to use compact `original_message_count`, not the reduced preserved-tail message count.
- Updated backend code-spec with compact transcript record contracts.

Verification:
- `pytest -q tests/test_sessions.py tests/test_cli.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_message_projection.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `pytest -q`
- `ruff check src/coding_deepgent/compact/artifacts.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/sessions/__init__.py src/coding_deepgent/sessions/ports.py src/coding_deepgent/sessions/service.py tests/test_sessions.py tests/test_cli.py tests/test_compact_artifacts.py`
- `mypy src/coding_deepgent/compact/artifacts.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/sessions/__init__.py src/coding_deepgent/sessions/ports.py src/coding_deepgent/sessions/service.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/utils/sessionStoragePortable.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
- Aligned:
  - compact events now have durable boundary/summary metadata.
  - compact persistence is separated from normal user/assistant transcript messages.
  - real message indexing is preserved across compacted continuation.
- Deferred:
  - compact-boundary-aware transcript pruning/relinking.
  - prompt-too-long retry.
  - auto/reactive compact.
  - post-compact context restoration attachments.

LangChain architecture:
- Primitive used:
  - normal message dictionaries remain the continuation path.
  - session JSONL store remains the durability seam.
  - no `SummarizationMiddleware`, no `RemoveMessage`, and no graph state replacement were introduced.
- Why no heavier abstraction:
  - 15A only persists compact metadata; destructive history rewriting and automatic lifecycle summarization are separate behavior changes.

Boundary findings:
- New issue handled:
  - compacted histories preserve only a recent tail, so persisted continuation `message_index` must use compact `original_message_count`.
- Residual risk:
  - `load_session()` records compact events but does not yet use them to alter resume context or display compact history. This is intentional for non-destructive 15A.
- Impact on next stage:
  - Next work should be explicitly selected: compact record display/recovery use, compact transcript pruning semantics, or auto/reactive compact. These should not be bundled silently.

Decision:
- continue

Terminal note:
- Stage 15A is complete. No further Stage 15 sub-stage is started automatically because the next options materially change resume or transcript behavior and need an explicit product choice.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside append-only compact transcript records.
- No auto-compact, prompt-too-long retry, transcript deletion, or transcript pruning was introduced.
