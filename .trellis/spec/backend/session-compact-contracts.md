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
    start_message_id: str,
    end_message_id: str,
    covered_message_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path: ...

def append_collapse(
    context: SessionContext,
    *,
    trigger: str,
    summary: str,
    start_message_id: str,
    end_message_id: str,
    covered_message_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path: ...

class SessionMessage:
    message_id: str
    created_at: str
    role: str
    content: str
    metadata: dict[str, Any] | None = None

class SessionSidechainMessage:
    created_at: str
    agent_type: str
    role: str
    content: str
    subagent_thread_id: str
    parent_message_id: str | None = None
    parent_thread_id: str | None = None
    metadata: dict[str, Any] | None = None

class LoadedSession:
    history: list[SessionMessage]
    sidechain_messages: list[SessionSidechainMessage]
    compacted_history: list[dict[str, Any]]
    compacted_history_source: CompactedHistorySource
    collapsed_history: list[dict[str, Any]]
    collapsed_history_source: CollapsedHistorySource
    state: dict[str, Any]
    evidence: list[SessionEvidence]
    compacts: list[SessionCompact]
    summary: SessionSummary
    collapses: list[SessionCollapse]

class RuntimeContext:
    session_context: SessionContext | None = None

class CompactedHistorySource:
    mode: Literal["raw", "compact"]
    reason: str
    compact_index: int | None = None

class RawTranscriptMessageView:
    message_id: str
    role: str
    content: str
    model_visible: bool
    hidden_by_event_ids: tuple[str, ...]

class ProjectionMessageView:
    role: str
    content: Any
    source: Literal[
        "raw",
        "compact_boundary",
        "compact_summary",
        "collapse_boundary",
        "collapse_summary",
    ]
    message_id: str | None
    event_id: str | None
    covered_message_ids: tuple[str, ...]

class CompressionTimelineEvent:
    event_id: str
    event_type: str
    created_at: str
    trigger: str | None
    summary: str
    affected_message_ids: tuple[str, ...]
    affected_tool_call_ids: tuple[str, ...]
    source: str | None

class CompressionView:
    raw_messages: tuple[RawTranscriptMessageView, ...]
    model_projection: tuple[ProjectionMessageView, ...]
    timeline: tuple[CompressionTimelineEvent, ...]
    projection_mode: Literal["selected", "raw", "compact", "collapse"]

def build_compression_view(
    loaded: LoadedSession,
    *,
    projection_mode: Literal["selected", "raw", "compact", "collapse"] = "selected",
) -> CompressionView: ...

def append_sidechain_message(
    context: SessionContext,
    *,
    agent_type: str,
    role: str,
    content: str,
    subagent_thread_id: str,
    parent_message_id: str | None = None,
    parent_thread_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path: ...
```

### 3. Contracts

#### Resume Continuation History

- `continuation_history(loaded)` must return:
  1. one system resume context message from `build_resume_context_message(loaded)`
  2. all `loaded.history` messages in original order
- The resume context message content starts with `RESUME_CONTEXT_MESSAGE_PREFIX`.
- Persisted raw message records must carry stable deterministic `message_id`
  values, and `LoadedSession.history` must preserve those IDs through load.
- `continuation_history()` must project `SessionMessage` into model-visible
  `{"role", "content"}` dictionaries instead of leaking storage fields into the
  runtime message list.
- When `run_prompt_with_recording()` creates or resumes a recorded session and
  the agent callable accepts `session_context`, it must pass the active
  `SessionContext` into runtime invocation context so tools can append bounded
  evidence records to the same session ledger.
- `render_recovery_brief()` must render concise provenance for verification
  evidence when available, using stable short fields such as `plan=<plan_id>`
  and `verdict=<verdict>`.
- `render_recovery_brief()` must not dump arbitrary evidence metadata for
  runtime or verification evidence.
- User-facing recovery brief may show product-level rules, long-term memory, and
  current-session memory as separate sections.
- Model-facing resume context should only carry the recovery layer and must not
  duplicate project rules, long-term memory, or current-session memory when
  those layers are already injected earlier in the runtime assembly order.
- When `LoadedSession.state["session_memory"]` contains a valid artifact,
  `render_recovery_brief()` must render it in a dedicated `Current-session memory:`
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

- Compact events are persisted as append-only JSONL records with
  `record_type == "transcript_event"` and `event_kind == "compact"`.
- Compact records must be loaded into `LoadedSession.compacts`.
- Compact records must increment `SessionSummary.compact_count`.
- Compact records must not appear in `LoadedSession.history`.
- Compact records must not replace or delete any message/state/evidence record.
- `LoadedSession.history` is the raw/full typed `SessionMessage` transcript view.
- `LoadedSession.compacted_history` is the load-time virtual compacted view.
- `LoadedSession.compacted_history_source` explains whether the compacted view
  came from projected raw history or a compact record.
- If no valid compact-derived view exists, `compacted_history` must fall back
  to the projected raw history view.
- Required compact record fields:

```json
{
  "record_type": "transcript_event",
  "version": 1,
  "session_id": "...",
  "timestamp": "...",
  "event_kind": "compact",
  "payload": {
    "trigger": "manual",
    "summary": "...",
    "start_message_id": "msg-000000",
    "end_message_id": "msg-000001",
    "covered_message_ids": ["msg-000000", "msg-000001"],
    "metadata": {"source": "generated"}
  }
}
```

- When continuation history contains synthetic compact artifacts,
  `run_prompt_with_recording()` must append one compact transcript event before
  recording the continuation prompt.
- Persisted raw message IDs after compacted continuation must continue the next
  append-order `msg-######` sequence from the existing raw message ledger, not
  from the count of synthetic compact projection messages.

#### Collapse Transcript Records

- Live collapse persistence uses the same append-only transcript-event ledger as
  manual compact, but with `event_kind == "collapse"`.
- Collapse records must be loaded into `LoadedSession.collapses`.
- Collapse records must increment `SessionSummary.collapse_count`.
- Collapse records must not appear in `LoadedSession.history`.
- Collapse records must not replace or delete raw message, compact, state, or
  evidence records.
- Collapse records must reference raw transcript messages through stable message
  IDs even though the collapse itself was decided from a live model-facing
  projection.
- When a recorded runtime invocation has transcript-projection lineage for the
  current model-facing history, live collapse may persist a collapse
  transcript-event record whose payload contains:
  - `trigger`
  - `summary`
  - `start_message_id`
  - `end_message_id`
  - optional `covered_message_ids`
  - optional bounded `metadata`
- If a live collapse projection contains no recoverable raw message coverage,
  the runtime must fail open and skip collapse-record persistence rather than
  inventing implicit indexes.

#### Subagent Sidechain Transcript Records

- Subagent sidechain transcript entries must be persisted in the same parent
  session JSONL ledger as `transcript_event` records with
  `event_kind == "subagent_message"`.
- Sidechain entries must not appear in `LoadedSession.history`.
- Sidechain entries must not appear in selected compacted/collapsed/main-model
  projections unless a future contract explicitly reopens that behavior.
- `LoadedSession.sidechain_messages` is the audit/read-model surface for child
  transcript entries.
- Each sidechain entry must carry bounded linkage fields:
  - `agent_type`
  - `role`
  - `content`
  - `subagent_thread_id`
  - optional `parent_message_id`
  - optional `parent_thread_id`
- Fork sidechain entries may also carry bounded continuity metadata, for example:
  - `fork_run_id`
  - `tool_pool_fingerprint`
  - `placeholder_layout_version`
- Sidechain transcript stays inside the parent ledger; no per-agent transcript
  directory is part of the current contract.

#### Load-Time Collapsed History View

- `JsonlSessionStore.load_session()` must derive
  `LoadedSession.collapsed_history` from raw `LoadedSession.history` plus valid
  `LoadedSession.collapses`.
- The collapsed view is a separate model-facing projection; raw transcript
  remains complete in `LoadedSession.history`.
- Collapse replay must use stable message references only:
  - `start_message_id`
  - `end_message_id`
  - optional exact `covered_message_ids`
- Invalid collapse references must not synthesize indexes or legacy fallbacks.
  Invalid events are skipped and the projected raw history remains available.
- Overlapping collapse records are deterministic: newer valid records win and
  older overlapping records are skipped.
- `LoadedSession.collapsed_history_source.mode` must be:
  - `"collapse"` when at least one collapse event contributes to the selected
    projection
  - `"raw"` when no valid collapse projection exists
- Compact and collapse coexist as projection event families over raw
  transcript. Selected continuation should prefer a valid collapse projection
  over compact projection to avoid stacking duplicate synthetic summaries.

#### Compression Visualization Read Model

- `build_compression_view(loaded)` is the backend data-readiness seam for future
  UI/API work. It must not mutate `LoadedSession` or persisted JSONL records.
- `CompressionView.raw_messages` must expose every raw `SessionMessage` with:
  - stable `message_id`
  - role/content
  - whether it is model-visible in the selected projection
  - which compression event IDs hide/summarize it, if any
- `CompressionView.model_projection` must expose the selected model-facing
  projection with source metadata:
  - raw messages use `source == "raw"` and carry `message_id`
  - compact synthetic messages use `compact_boundary` / `compact_summary`
  - collapse synthetic messages use `collapse_boundary` / `collapse_summary`
  - synthetic messages carry `event_id` and `covered_message_ids`
- `CompressionView.timeline` must merge available compression-related facts into
  a stable chronological timeline:
  - compact transcript events
  - collapse transcript events
  - runtime-pressure `runtime_event` evidence
- Timeline entries must include event type, trigger when available, affected
  message IDs when available, affected tool-call IDs when available, summary,
  source, and bounded metadata.
- The read model must support explicit `projection_mode == "raw"` so callers can
  inspect the full transcript without compression filters.

#### Load-Time Compacted History View

- `JsonlSessionStore.load_session()` must derive `LoadedSession.compacted_history`
  from the newest compact record that yields a valid compact-derived view.
- The compacted view must be:
  1. compact boundary message
  2. compact summary message
  3. preserved tail messages
- For the current manual-compact path, the compact event covers a contiguous
  prefix of the raw transcript:
  - `start_message_id` must resolve to the first raw message in the session
  - `end_message_id` must resolve to the last summarized raw message
  - when `covered_message_ids` is present, it must match that covered prefix
- Compact records must be scanned from newest to oldest.
- If the latest compact record's message references are invalid, the loader
  must try the next earlier compact record.
- If no compact record yields a valid compact-derived view,
  `compacted_history` must fall back to the projected raw history.
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
- Long-term memory type is a closed set: `user`, `feedback`, `project`, `reference`.
- Recovery/resume must show long-term memory and current-session memory as two
  separate sections.
- Before writing, it must call `evaluate_memory_quality(record, existing_records=...)`.
- It must reject:
  - normalized duplicates in the same memory type
  - obvious transient task/session state
  - project-memory entries that are derivable from repository structure or code
  - project-memory entries that use relative time instead of absolute dates
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
| compacted history is recorded to transcript | synthetic compact artifacts are not persisted as message records; one compact transcript event is appended |
| compacted continuation appends new raw messages | next real message ID continues the append-order `msg-######` sequence |
| multiple valid compact records exist | `LoadedSession.compacted_history` uses the newest valid compact record |
| latest compact record is invalid but an earlier compact record is valid | `LoadedSession.compacted_history` uses the earlier valid compact record |
| compact record exists and derived tail is valid | `LoadedSession.compacted_history` contains boundary + summary + preserved tail |
| no compact record yields a valid derived tail | `LoadedSession.compacted_history` falls back to projected raw history |
| live collapse runs during recorded session and raw projection lineage exists | one collapse transcript event is appended and loaded into `LoadedSession.collapses` |
| live collapse runs without recoverable raw message coverage | model-facing collapse still succeeds; collapse record persistence is skipped |
| valid collapse records exist | `LoadedSession.collapsed_history` contains collapse boundary + summary + preserved raw messages |
| invalid collapse refs exist | invalid events are skipped; collapsed view falls back to raw projection if none are valid |
| overlapping collapse records exist | newest non-overlapping valid records define the deterministic projection |
| compact and collapse records both exist | selected continuation uses collapse projection without stacking compact and collapse summaries |
| sidechain transcript events exist | `LoadedSession.history` and selected continuation stay unchanged; child entries load through `sidechain_messages` only |
| fork sidechain transcript events exist | child entries stay in `sidechain_messages`; bounded fork continuity metadata roundtrips without entering main projections |
| compression view selected projection hides raw messages | hidden raw messages have `model_visible == False` and `hidden_by_event_ids` |
| compression view forced raw projection | all raw messages remain model-visible and projection entries use `source == "raw"` |
| runtime pressure evidence includes affected tool IDs | timeline exposes `affected_tool_call_ids` when metadata contains them |
| selected compacted view comes from compact record at index N | `compacted_history_source == compact/latest_valid_compact/N` |
| selected compacted view falls back to raw history | `compacted_history_source == raw/<reason>/None` |
| valid long-term memory snapshot in runtime state | recovery brief renders `Long-term memory:` with bounded saved entries |
| missing long-term memory snapshot in runtime state | recovery brief renders `Long-term memory:` with `- none` |
| valid current session-memory artifact | recovery brief renders `Current-session memory:` with `[current]`; generated compact summary may receive assist text |
| stale session-memory artifact | recovery brief renders `Current-session memory:` with `[stale]`; generated compact summary ignores assist text |
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

- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_uses_recovery_brief_continuation_history`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_can_use_manual_compact_summary`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_can_generate_manual_compact_summary`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_rejects_manual_and_generated_compact_together`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_rejects_compact_options_without_prompt`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_rejects_compact_instructions_without_generation`
- `coding-deepgent/tests/cli/test_cli.py::test_run_once_records_new_and_resumed_session_transcript`
- `coding-deepgent/tests/cli/test_cli.py::test_run_once_records_compact_metadata_without_message_index_skew`
- `coding-deepgent/tests/cli/test_cli.py::test_selected_continuation_history_uses_loaded_compacted_history`
- `coding-deepgent/tests/cli/test_cli.py::test_selected_continuation_history_prefers_loaded_collapsed_history`
- `coding-deepgent/tests/cli/test_cli.py::test_sessions_resume_defaults_to_latest_compacted_continuation_when_available`
- `coding-deepgent/tests/compact/test_compact_artifacts.py`
- `coding-deepgent/tests/compact/test_compact_summarizer.py`
- `coding-deepgent/tests/compact/test_message_projection.py`
- `coding-deepgent/tests/sessions/test_sessions.py::test_compact_record_roundtrip_does_not_enter_history`
- `coding-deepgent/tests/sessions/test_sessions.py::test_collapse_record_roundtrip_does_not_enter_history`
- `coding-deepgent/tests/sessions/test_sessions.py::test_sidechain_message_roundtrip_stays_out_of_parent_history`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_collapsed_history_uses_newest_non_overlapping_collapses`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_collapsed_history_falls_back_to_raw_on_invalid_refs`
- `coding-deepgent/tests/sessions/test_sessions.py::test_compression_view_exposes_raw_projection_and_timeline`
- `coding-deepgent/tests/sessions/test_sessions.py::test_compression_view_can_force_raw_projection`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_ignores_invalid_compact_records`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_compacted_history_falls_back_to_raw_history_on_invalid_tail_range`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_compacted_history_uses_newest_valid_compact_record`
- `coding-deepgent/tests/sessions/test_sessions.py::test_load_session_compacted_history_uses_latest_valid_compact_record`
- `coding-deepgent/tests/sessions/test_sessions.py::test_recovery_brief_renders_verification_provenance_only`
- `coding-deepgent/tests/compact/test_runtime_pressure.py::test_runtime_pressure_middleware_persists_collapse_record_when_projection_exists`
- `coding-deepgent/tests/memory/test_memory.py::test_memory_quality_policy_rejects_transient_and_duplicate_entries`
- `coding-deepgent/tests/memory/test_memory_integration.py::test_save_memory_tool_rejects_transient_memory_via_create_agent_runtime`

Required assertion points:

- generated compact summary uses a fake summarizer in tests
- fake summarizer receives original loaded history plus compact prompt message
- `<analysis>` is absent from compact artifact summary text
- compact summary artifact is not merged by `project_messages()`
- compact transcript records are separated from `LoadedSession.history`
- collapse transcript records are separated from `LoadedSession.history`
- collapsed history view is derived at load time and kept separate from raw history
- compression view exposes raw visibility, selected projection source metadata,
  and timeline events
- compacted history view is derived at load time and kept separate from raw history
- persisted transcript `message_id` values remain contiguous append-order IDs
- compacted continuation persists `start_message_id` / `end_message_id` and
  optional `covered_message_ids` into the compact transcript event payload
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

## Scenario: Projection Repair Tombstone Observability

### 1. Scope / Trigger

- Trigger: changes touching `project_messages(...)`,
  `project_messages_with_stats(...)`, or agent-loop message normalization.
- Applies when model-facing projection contains orphaned structured
  `tool_result` blocks without a previously visible matching `tool_use`.

### 2. Signatures

```python
ORPHAN_TOOL_RESULT_TOMBSTONE = (
    "[Orphaned tool_result tombstoned: missing matching tool_use]"
)

class ProjectionRepairStats:
    orphan_tombstoned: int = 0
    reason: str | None = None

class ProjectMessagesResult:
    messages: list[dict[str, Any]]
    repair_stats: ProjectionRepairStats

def project_messages_with_stats(
    messages: list[dict[str, Any]],
    *,
    max_chars_per_message: int | None = None,
) -> ProjectMessagesResult: ...
```

### 3. Contracts

- Projection repair must replace orphaned `tool_result` blocks with a bounded
  text tombstone instead of passing raw orphaned tool material to the model.
- Matched `tool_use` / `tool_result` blocks must remain unchanged.
- Agent-loop normalization must emit one bounded `orphan_tombstoned` runtime
  event when repair happens.
- When a recorded session context exists, `orphan_tombstoned` evidence metadata
  may include only bounded fields such as `reason`, `tombstoned_count`, and
  `message_count`.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| `tool_result` has no prior matching `tool_use` | content block is replaced with `ORPHAN_TOOL_RESULT_TOMBSTONE` and event metadata includes `reason == "missing_tool_use"` |
| `tool_result` has a prior matching `tool_use` | structured content is preserved unchanged and no repair event is emitted |

### 5. Tests Required

- `coding-deepgent/tests/compact/test_message_projection.py`
- `coding-deepgent/tests/runtime/test_agent_runtime_service.py`
