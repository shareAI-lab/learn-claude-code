# Runtime Context And Compaction Contracts

> Executable contracts for the coding-deepgent session, recovery, memory, and manual compaction seams.

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
coding-deepgent sessions resume SESSION_ID --prompt TEXT --compact-summary SUMMARY [--compact-keep-last N]
coding-deepgent sessions resume SESSION_ID --prompt TEXT --generate-compact-summary [--compact-instructions TEXT] [--compact-keep-last N]
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
) -> str: ...
```

### 3. Contracts

#### Resume Continuation History

- `continuation_history(loaded)` must return:
  1. one system resume context message from `build_resume_context_message(loaded)`
  2. all `loaded.history` messages in original order
- The resume context message content starts with `RESUME_CONTEXT_MESSAGE_PREFIX`.
- `sessions.service.run_prompt_with_recording()` must not count synthetic resume context messages when assigning persisted `message_index` values.

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
- It must not add LangChain `SummarizationMiddleware`.
- It must not delete, prune, rewrite, or compact persisted session JSONL transcript records.

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
| `--compact-summary` without `--prompt` | Click error; run path is not called |
| `--generate-compact-summary` without `--prompt` | Click error; run path is not called |
| `--compact-instructions` without `--generate-compact-summary` | Click error; run path is not called |
| `--compact-summary` and `--generate-compact-summary` together | Click error; run path is not called |
| blank compact summary | `ValueError` from compaction helper, surfaced as Click error |
| summarizer returns only `<analysis>` or blank text | `ValueError("compact summarizer returned an empty summary")` |
| compact tail starts with `tool_result` | include matching previous `tool_use` message when present |
| resume context history is recorded to transcript | synthetic resume context is not persisted as a message record |
| duplicate memory save | returns "Memory not saved" and store remains unchanged |

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

- `tests/test_cli.py::test_sessions_resume_uses_recovery_brief_continuation_history`
- `tests/test_cli.py::test_sessions_resume_can_use_manual_compact_summary`
- `tests/test_cli.py::test_sessions_resume_can_generate_manual_compact_summary`
- `tests/test_cli.py::test_sessions_resume_rejects_manual_and_generated_compact_together`
- `tests/test_cli.py::test_sessions_resume_rejects_compact_options_without_prompt`
- `tests/test_cli.py::test_sessions_resume_rejects_compact_instructions_without_generation`
- `tests/test_cli.py::test_run_once_records_new_and_resumed_session_transcript`
- `tests/test_compact_artifacts.py`
- `tests/test_compact_summarizer.py`
- `tests/test_message_projection.py`
- `tests/test_memory.py::test_memory_quality_policy_rejects_transient_and_duplicate_entries`
- `tests/test_memory_integration.py::test_save_memory_tool_rejects_transient_memory_via_create_agent_runtime`

Required assertion points:

- generated compact summary uses a fake summarizer in tests
- fake summarizer receives original loaded history plus compact prompt message
- `<analysis>` is absent from compact artifact summary text
- compact summary artifact is not merged by `project_messages()`
- persisted transcript `message_index` values remain contiguous for real persisted messages only
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
