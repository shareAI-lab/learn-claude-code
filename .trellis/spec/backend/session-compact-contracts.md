# Session Compact Contracts

> Executable contracts for resume, manual/generated compaction, compact records, session memory, and memory quality.

## Scenario: Session Resume And Manual Compaction

### 1. Scope / Trigger

- Trigger: Changes touching `coding_deepgent.cli`, `coding_deepgent.cli_service`, `coding_deepgent.sessions`, `coding_deepgent.compact`, `coding_deepgent.memory`, or runtime message projection.
- Applies when a feature changes how conversation history, recovery brief context, compact summaries, or long-term memory are assembled for a model call.
- This is an infra/cross-layer contract because CLI flags, session JSONL records, in-memory runtime state, LangChain message dictionaries, and tests must agree.

### 2. Signatures

#### CLI

```bash
coding-deepgent sessions resume SESSION_ID
coding-deepgent sessions resume SESSION_ID --prompt TEXT
coding-deepgent sessions resume SESSION_ID --prompt TEXT --session-memory TEXT
coding-deepgent sessions resume SESSION_ID --prompt TEXT --compact-summary SUMMARY [--compact-keep-last N]
coding-deepgent sessions resume SESSION_ID --prompt TEXT --generate-compact-summary [--compact-instructions TEXT] [--compact-keep-last N] [--session-memory TEXT]
```

#### Python Service Seams

```python
def continuation_history(loaded: LoadedSession) -> list[dict[str, Any]]: ...

def compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summary: str,
    keep_last: int = 4,
) -> list[dict[str, Any]]: ...

def generated_compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summarizer: Any,
    keep_last: int = 4,
    custom_instructions: str | None = None,
) -> list[dict[str, Any]]: ...

def compact_messages_with_summary(
    messages: list[dict[str, Any]],
    *,
    summary: str,
    keep_last: int = 4,
) -> CompactArtifact: ...

def generate_compact_summary(
    messages: list[dict[str, Any]],
    summarizer: CompactSummarizer | Callable[[list[dict[str, Any]]], Any],
    *,
    custom_instructions: str | None = None,
    assist_context: str | None = None,
) -> str: ...

class RuntimeStateContribution:
    key: str

class RecoveryBriefContribution:
    name: str

class CompactAssistContribution:
    name: str

class CompactSummaryUpdateContribution:
    name: str

def append_compact(
    context: SessionContext,
    *,
    trigger: str,
    summary: str,
    original_message_count: int,
    summarized_message_count: int,
    kept_message_count: int,
    metadata: dict[str, Any] | None = None,
) -> Path: ...

class LoadedSession:
    history: list[dict[str, str]]
    compacted_history: list[dict[str, Any]]
    compacted_history_source: CompactedHistorySource
    state: dict[str, Any]
    evidence: list[SessionEvidence]
    compacts: list[SessionCompact]
    summary: SessionSummary

class RuntimeContext:
    session_context: SessionContext | None = None

class CompactedHistorySource:
    mode: Literal["raw", "compact"]
    reason: str
    compact_index: int | None = None
```

### 3. Contracts

#### Resume Continuation History

- `continuation_history(loaded)` must return:
  1. one system resume context message from `build_resume_context_message(loaded)`
  2. all `loaded.history` messages in original order
- The resume context message content starts with `RESUME_CONTEXT_MESSAGE_PREFIX`.
- `sessions.service.run_prompt_with_recording()` must not count synthetic resume context messages when assigning persisted `message_index` values.
- When `run_prompt_with_recording()` creates or resumes a recorded session and
  the agent callable accepts `session_context`, it must pass the active
  `SessionContext` into runtime invocation context so tools can append bounded
  evidence records to the same session ledger.
- `render_recovery_brief()` must render concise provenance for verification
  evidence when available, using stable short fields such as `plan=<plan_id>`
  and `verdict=<verdict>`.
- `render_recovery_brief()` must not dump arbitrary evidence metadata for
  runtime or verification evidence.
- When `LoadedSession.state["session_memory"]` contains a valid artifact,
  `render_recovery_brief()` must render it in a dedicated `Session memory:`
  section and mark it `current` or `stale` based on the stored `message_count`
  versus `LoadedSession.summary.message_count`.
- Invalid `session_memory` state must be ignored rather than breaking session
  load or resume.
- Feature-specific recovery sections should enter through registered
  `RecoveryBriefContribution` providers, not through one-off conditionals in
  `render_recovery_brief()`.

#### Manual Compact Continuation History

- `compacted_continuation_history(loaded, summary=..., keep_last=N)` must return:
  1. recovery brief system message
  2. compact boundary system message
  3. compact summary user message
  4. preserved recent tail messages
- Compact boundary and summary messages use structured text content blocks:

```python
{"role": "system", "content": [{"type": "text", "text": "..."}]}
{"role": "user", "content": [{"type": "text", "text": "..."}]}
```

- Structured content is intentional. It prevents `project_messages()` from merging the compact summary into adjacent plain user messages.
- `format_compact_summary()` must strip `<analysis>...</analysis>` and unwrap `<summary>...</summary>`.
- `compact_messages_with_summary()` must not mutate the input `messages` list or its nested dictionaries.
- If the kept tail includes a `tool_result` block, the helper must include matching earlier `tool_use` blocks when they exist in the source messages.

#### Generated Manual Compact

- `--generate-compact-summary` is explicit and user-triggered only.
- It must call `build_openai_model(settings)` only when `--generate-compact-summary` is present.
- It must pass the loaded history into `generate_compact_summary()` through the fakeable summarizer seam.
- When a current valid session-memory artifact exists, `generate_compact_summary()`
  may receive it as a bounded assist text.
- Stale or invalid session-memory artifacts must not be passed to the summarizer
  as compact assist text.
- Feature-specific assist text should enter through registered
  `CompactAssistContribution` providers, then flow into the summarizer through
  the generic `assist_context` parameter.
- It must not add LangChain `SummarizationMiddleware`.
- It must not delete, prune, rewrite, or compact persisted session JSONL transcript records.

#### Module Contribution Seams

- Runtime-state extensions should use `RuntimeStateContribution` providers for
  validation/coercion instead of adding feature-specific fields to
  `JsonlSessionStore._coerce_state_snapshot()`.
- Recovery-context extensions should use `RecoveryBriefContribution` providers
  and render as bounded sections.
- Generated compact-summary extensions should use `CompactAssistContribution`
  providers and return bounded text only when the assist is current/reliable.
- State updates that happen after a generated compact summary should use
  `CompactSummaryUpdateContribution` providers. Providers may update module
  state only from the generated summary that already exists; they must not
  trigger a new model call.
- The current registry is intentionally static and local. It is not a plugin
  registration system and must not introduce background/runtime discovery.
- Contribution seams reduce accidental coupling but do not eliminate essential
  cross-layer integration for model-visible flows.

#### Session-Memory Local Updates

- `--generate-compact-summary` is the only current path that can refresh
  `LoadedSession.state["session_memory"]` automatically.
- Plain `sessions resume SESSION_ID --prompt TEXT` must not trigger an implicit
  summarizer call to update session memory.
- A missing valid session-memory artifact may be initialized from the generated
  compact summary.
- A stale-enough artifact may be refreshed from the generated compact summary
  when the module-owned threshold policy says it is due.
- The module-owned threshold policy may use message-count delta, deterministic
  estimated-token delta, and tool-call delta. Token counts are local estimates,
  not provider billing/tokenizer values.
- A current/recent artifact must not be refreshed.
- Refreshed artifacts use `source == "generated_compact"` and
  message, estimated-token, and tool-call counters derived from
  `LoadedSession.history`.

#### Compact Transcript Records

- Compact events are persisted as append-only JSONL records with `record_type == "compact"`.
- Compact records must be loaded into `LoadedSession.compacts`.
- Compact records must increment `SessionSummary.compact_count`.
- Compact records must not appear in `LoadedSession.history`.
- Compact records must not replace or delete any message/state/evidence record.
- `LoadedSession.history` is the raw/full user-assistant transcript view.
- `LoadedSession.compacted_history` is the load-time virtual compacted view.
- `LoadedSession.compacted_history_source` explains whether the compacted view came from raw fallback or a compact record.
- If no valid compact-derived view exists, `compacted_history` must fall back to `history`.
- Required compact record fields:

```json
{
  "record_type": "compact",
  "version": 1,
  "session_id": "...",
  "timestamp": "...",
  "cwd": "...",
  "trigger": "manual",
  "summary": "...",
  "original_message_count": 2,
  "summarized_message_count": 1,
  "kept_message_count": 1
}
```

- When continuation history contains synthetic compact artifacts, `run_prompt_with_recording()` must append one compact record before recording the continuation prompt.
- The next persisted message index after compacted continuation must use `original_message_count` from the compact metadata, not the count of preserved synthetic history messages.

#### Load-Time Compacted History View

- `JsonlSessionStore.load_session()` must derive `LoadedSession.compacted_history` from the newest compact record that yields a valid compact-derived view.
- The compacted view must be:
  1. compact boundary message
  2. compact summary message
  3. preserved tail messages
- Tail start is derived as:

```python
keep_from = original_message_count - kept_message_count
```

- Tail derivation is clamped to `[0, len(raw_history)]`.
- Compact records must be scanned from newest to oldest.
- If the latest compact record's derived tail is empty or invalid, the loader must try the next earlier compact record.
- If no compact record yields a valid compact-derived view, `compacted_history` must fall back to the raw history.
- `compacted_history_source.mode` must be:
  - `"compact"` when a compact record produces the selected view
  - `"raw"` when no compact view is selected
- `compacted_history_source.reason` must distinguish at least:
  - `"no_compacts"`
  - `"latest_valid_compact"`
  - `"no_valid_compact"`
- `compacted_history_source.compact_index` is the zero-based index into `LoadedSession.compacts` when `mode == "compact"`.
- Compact-aware resume selectors should use `compacted_history` rather than re-derive compact semantics ad hoc.

#### Memory Quality

- `save_memory` writes only through `runtime.store`.
- Before writing, it must call `evaluate_memory_quality(record, existing_records=...)`.
- It must reject:
  - normalized duplicates in the same namespace
  - obvious transient task/session state
  - trivially short low-value content
- It must return `"Memory not saved: ..."` when rejecting, and must not write to the store.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| `sessions resume SESSION_ID` | prints recovery brief and continuation hint |
| `--session-memory` without `--prompt` | Click error; run path is not called |
| `--compact-summary` without `--prompt` | Click error; run path is not called |
| `--generate-compact-summary` without `--prompt` | Click error; run path is not called |
| `--compact-instructions` without `--generate-compact-summary` | Click error; run path is not called |
| `--compact-summary` and `--generate-compact-summary` together | Click error; run path is not called |
| blank `--session-memory` | session-memory validation error; run path is not called |
| blank compact summary | `ValueError` from compaction helper, surfaced as Click error |
| summarizer returns only `<analysis>` or blank text | `ValueError("compact summarizer returned an empty summary")` |
| compact tail starts with `tool_result` | include matching previous `tool_use` message when present |
| resume context history is recorded to transcript | synthetic resume context is not persisted as a message record |
| compacted history is recorded to transcript | synthetic compact artifacts are not persisted as message records; one compact record is appended |
| compacted history preserves only recent tail | next real message index starts at compact `original_message_count` |
| multiple valid compact records exist | `LoadedSession.compacted_history` uses the newest valid compact record |
| latest compact record is invalid but an earlier compact record is valid | `LoadedSession.compacted_history` uses the earlier valid compact record |
| compact record exists and derived tail is valid | `LoadedSession.compacted_history` contains boundary + summary + preserved tail |
| no compact record yields a valid derived tail | `LoadedSession.compacted_history` falls back to raw history |
| selected compacted view comes from compact record at index N | `compacted_history_source == compact/latest_valid_compact/N` |
| selected compacted view falls back to raw history | `compacted_history_source == raw/<reason>/None` |
| valid current session-memory artifact | recovery brief renders `Session memory:` with `[current]`; generated compact summary may receive assist text |
| stale session-memory artifact | recovery brief renders `Session memory:` with `[stale]`; generated compact summary ignores assist text |
| invalid session-memory artifact in snapshot | load succeeds and artifact is ignored |
| missing session-memory artifact after generated compact summary | artifact is initialized from generated summary |
| stale-enough session-memory artifact after generated compact summary | artifact is refreshed from generated summary |
| token/tool-call pressure exceeds session-memory thresholds | artifact is refreshed from generated summary |
| current/recent session-memory artifact after generated compact summary | artifact is not refreshed |
| duplicate memory save | returns "Memory not saved" and store remains unchanged |
| verification evidence with `plan_id` and `verdict` metadata | recovery brief includes concise `(plan=...; verdict=...)` provenance |
| non-verification evidence with metadata | recovery brief does not render arbitrary metadata |

### 5. Good / Base / Bad Cases

#### Good

```bash
coding-deepgent sessions resume session-1 \
  --prompt "continue" \
  --generate-compact-summary \
  --compact-instructions "Focus on code changes and failed tests." \
  --compact-keep-last 4
```

Expected:
- Generated summary goes through `generate_compact_summary()`.
- Continuation history starts with recovery brief, compact boundary, compact summary, then recent messages.
- Transcript only records the new user prompt and assistant result from the continuation path.

#### Base

```bash
coding-deepgent sessions resume session-1 --prompt "continue"
```

Expected:
- Continuation history is recovery brief + loaded history.
- No compact artifact is inserted.

#### Bad

```bash
coding-deepgent sessions resume session-1 \
  --prompt "continue" \
  --compact-summary "manual" \
  --generate-compact-summary
```

Expected:
- Reject with a Click error before model construction or run prompt.

### 6. Tests Required

Required focused tests:

- `coding-deepgent/tests/test_cli.py::test_sessions_resume_uses_recovery_brief_continuation_history`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_can_use_manual_compact_summary`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_can_generate_manual_compact_summary`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_rejects_manual_and_generated_compact_together`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_rejects_compact_options_without_prompt`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_rejects_compact_instructions_without_generation`
- `coding-deepgent/tests/test_cli.py::test_run_once_records_new_and_resumed_session_transcript`
- `coding-deepgent/tests/test_cli.py::test_run_once_records_compact_metadata_without_message_index_skew`
- `coding-deepgent/tests/test_cli.py::test_selected_continuation_history_uses_loaded_compacted_history`
- `coding-deepgent/tests/test_cli.py::test_sessions_resume_defaults_to_latest_compacted_continuation_when_available`
- `coding-deepgent/tests/test_compact_artifacts.py`
- `coding-deepgent/tests/test_compact_summarizer.py`
- `coding-deepgent/tests/test_message_projection.py`
- `coding-deepgent/tests/test_sessions.py::test_compact_record_roundtrip_does_not_enter_history`
- `coding-deepgent/tests/test_sessions.py::test_load_session_ignores_invalid_compact_records`
- `coding-deepgent/tests/test_sessions.py::test_load_session_compacted_history_falls_back_to_raw_history_on_invalid_tail_range`
- `coding-deepgent/tests/test_sessions.py::test_load_session_compacted_history_uses_newest_valid_compact_record`
- `coding-deepgent/tests/test_sessions.py::test_load_session_compacted_history_uses_latest_valid_compact_record`
- `coding-deepgent/tests/test_sessions.py::test_recovery_brief_renders_verification_provenance_only`
- `coding-deepgent/tests/test_memory.py::test_memory_quality_policy_rejects_transient_and_duplicate_entries`
- `coding-deepgent/tests/test_memory_integration.py::test_save_memory_tool_rejects_transient_memory_via_create_agent_runtime`

Required assertion points:

- generated compact summary uses a fake summarizer in tests
- fake summarizer receives original loaded history plus compact prompt message
- `<analysis>` is absent from compact artifact summary text
- compact summary artifact is not merged by `project_messages()`
- compact transcript records are separated from `LoadedSession.history`
- compacted history view is derived at load time and kept separate from raw history
- persisted transcript `message_index` values remain contiguous for real persisted messages only
- compacted continuation uses compact `original_message_count` as the next real message index baseline
- rejected compact CLI combinations do not call `run_prompt`
- rejected memory writes do not mutate LangGraph store

### 7. Wrong vs Correct

#### Wrong

```python
history = [
    {"role": "user", "content": f"Summary: {summary}"},
    *loaded.history[-keep_last:],
]
```

Why wrong:
- Plain same-role user messages can be merged by `project_messages()`.
- No compact boundary exists.
- Recovery brief is lost.
- Tool result tails can be orphaned from their tool use.

#### Correct

```python
history = cli_service.generated_compacted_continuation_history(
    loaded,
    summarizer=summarizer,
    keep_last=4,
    custom_instructions="Focus on code changes.",
)
```

Why correct:
- Reuses the recovery brief.
- Reuses the Stage 13 compact boundary and summary artifact shape.
- Formats generated summary through the Stage 13C seam.
- Keeps compaction explicit and non-destructive.

#### Wrong

```python
middleware=[SummarizationMiddleware(model="gpt-4.1-mini", trigger=("tokens", 4000))]
```

Why wrong for the current stage:
- It introduces automatic lifecycle summarization and persistent state replacement.
- The current product contract is explicit manual compaction only.

#### Correct

```python
if generate_compact_summary:
    history = cli_service.generated_compacted_continuation_history(...)
```

Why correct:
- Model construction and summarization happen only after explicit user opt-in.
- No automatic transcript or state mutation is introduced.

