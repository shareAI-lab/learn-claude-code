# Runtime Pressure Contracts

> Executable contracts for live snip, microcompact, context collapse, auto/reactive compact, restoration, and runtime pressure evidence.

## Scenario: Progressive Live Pressure Pipeline

### 1. Scope / Trigger

- Trigger: changes touching `RuntimePressureMiddleware.wrap_model_call()` ordering
  or any helper that rewrites live model-call messages.
- Applies when `Snip`, `MicroCompact`, `Collapse`, and `AutoCompact` should run
  as a staged model-call preparation pipeline.

### 2. Signatures

```python
class RuntimePressureMiddleware(AgentMiddleware):
    snip_threshold_tokens: int | None
    collapse_threshold_tokens: int | None
    auto_compact_threshold_tokens: int | None
```

### 3. Contracts

- Runtime pressure handling must remain LangChain middleware-level request
  rewriting through `wrap_model_call()`.
- The live pressure order is:
  1. `snip_messages`
  2. `microcompact_messages`
  3. `maybe_collapse_messages`
  4. `maybe_auto_compact_messages`
  5. model call
- These live rewrites must not append, delete, or replace JSONL transcript
  records. Only explicit session/manual compact paths may persist compact
  records.
- Each stage may emit bounded runtime events, but event metadata must not include
  raw prompt contents or raw summaries.
- Later stages operate on the current model-facing projection returned by earlier
  stages.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| all four thresholds are crossed | runtime events appear in order: `snip`, `microcompact`, `context_collapse`, `auto_compact` |
| a stage does not cross threshold | stage is skipped without blocking later eligible stages |
| live rewrite happens during recorded session | evidence records are bounded summaries only |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_app.py`

Required assertion points:

- middleware pipeline order is stable
- settings values are wired into `RuntimePressureMiddleware`
- live rewrites do not depend on tutorial/reference modules

## Scenario: Live Snip

### 1. Scope / Trigger

- Trigger: changes touching `snip_messages(...)`, snip thresholds, or live
  model-facing projection trimming.
- Applies when old messages should be hidden from the current model call before
  heavier summarization or compaction is attempted.

### 2. Signatures

```python
def snip_messages(
    messages: Sequence[BaseMessage],
    *,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_SNIP,
) -> list[BaseMessage]: ...
```

### 3. Contracts

- `snip_messages(...)` must be deterministic and model-call local.
- If `threshold_tokens is None`, messages must remain unchanged.
- Default product settings may keep snip disabled with
  `snip_threshold_tokens == None` because snip is a lossy projection-only stage.
  Enable it only when a concrete pressure threshold is configured.
- If estimated message tokens are below `threshold_tokens`, messages must remain
  unchanged.
- If the threshold is crossed, the model-facing projection becomes:
  1. one live snip boundary `SystemMessage`
  2. preserved recent tail messages
- The snip boundary must expose bounded counts such as `hidden_messages` and
  `kept_messages`, not hidden prompt contents.
- If the preserved tail starts with a `ToolMessage`, the helper must include the
  matching prior `AIMessage` tool call when present.
- Existing live pressure artifact messages should not be stacked repeatedly.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| estimated tokens below threshold | history unchanged |
| threshold crossed | boundary + recent tail returned |
| preserved tail starts with tool result | matching tool-call AI message is preserved |
| `threshold_tokens < 1` | `ValueError` |
| `keep_recent_messages < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`

Required assertion points:

- older messages are hidden from model-facing projection
- input messages are not mutated
- tool-call/tool-result tail pairing is preserved

## Scenario: Live Microcompact

### 1. Scope / Trigger

- Trigger: changes touching `coding_deepgent.compact.runtime_pressure`,
  middleware ordering, capability metadata for compactable tools, or live
  message-history pressure handling.
- Applies when older tool results can be cleared before a model call to reduce
  live context pressure without performing a full compact.
- This is a cross-layer contract because tool-call metadata, middleware history
  rewriting, capability eligibility, and runtime message invariants must agree.

### 2. Signatures

```python
def microcompact_messages(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
) -> list[BaseMessage]: ...

class RuntimePressureMiddleware(AgentMiddleware):
    registry: CapabilityRegistry
```

### 3. Contracts

- `microcompact_messages(...)` must be deterministic and model-call local. It
  must not persist transcript mutations by itself.
- Only tool results whose originating tool capability is marked
  `microcompact_eligible` may be compacted.
- Error tool results must not be compacted.
- If the number of compactable tool results is less than or equal to
  `keep_recent_tool_results`, messages must remain unchanged.
- Older compactable tool results beyond the kept recent tail may have their
  `ToolMessage.content` replaced, but must preserve:
  - `tool_call_id`
  - `status`
  - `artifact`
  - message ordering
- If a compacted tool result artifact contains a persisted output `path`, the
  replacement content must keep that path model-visible.
- Recent compactable tool results within the kept tail must remain unchanged.
- Ineligible tool results must remain unchanged.
- `RuntimePressureMiddleware.wrap_model_call()` may replace request messages for
  the current model call only. It must not introduce a custom query runtime.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| 4 eligible compactable tool results with keep-last=2 | first 2 older tool results are compacted; last 2 remain unchanged |
| eligible tool result with persisted-output artifact path | compacted content keeps the path visible |
| eligible tool result without persisted artifact | compacted content uses the generic cleared marker |
| ineligible tool result | unchanged |
| error tool result | unchanged |
| `keep_recent_tool_results < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_app.py`
- `coding-deepgent/tests/test_memory_integration.py`

Required assertion points:

- older eligible tool results are compacted deterministically
- recent eligible tool results remain inline
- ineligible tool results are not rewritten
- app/container middleware chain includes runtime pressure middleware before tool guard

## Scenario: Live Context Collapse

### 1. Scope / Trigger

- Trigger: changes touching `maybe_collapse_messages(...)`, collapse thresholds,
  collapse summary artifacts, or summarizer use before auto-compact.
- Applies when older live context should be summarized before the heavier
  auto-compact stage.
- This is a cross-layer contract because summarizer usage, message rewriting,
  recent-tail preservation, restoration hints, settings, and runtime evidence
  must agree.

### 2. Signatures

```python
def maybe_collapse_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
    assist_context: str | None = None,
) -> list[BaseMessage]: ...

def collapse_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
) -> list[BaseMessage]: ...
```

### 3. Contracts

- Context collapse must remain middleware-level request rewriting. It must not
  introduce a custom query runtime.
- If `threshold_tokens is None`, messages must remain unchanged.
- If estimated message tokens are below `threshold_tokens`, messages must remain
  unchanged.
- If the threshold is crossed, the helper may call the existing compact
  summarizer seam through the provided model-like `.invoke()` path.
- If current session-memory assist text is available, collapse may pass it to
  the summarizer as bounded assist text.
- Summarizer failure or invalid summary must fail open: the original
  model-facing messages must be preserved so auto-compact and the model call can
  still proceed.
- `collapse_live_messages_with_summary(...)` must produce:
  1. one live collapse boundary `SystemMessage`
  2. one live collapse summary `HumanMessage`
  3. optional restoration `SystemMessage` for collapsed-away persisted-output
     paths
  4. preserved recent tail messages
- If the preserved tail starts with a `ToolMessage`, the helper must include the
  matching prior `AIMessage` tool call when present.
- Collapse summaries are live artifacts only and must not be persisted as
  session compact records.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| estimated tokens below threshold | history unchanged |
| threshold crossed and summarizer succeeds | live collapse boundary + summary + preserved tail returned |
| current session-memory artifact exists | summarizer request may receive bounded assist text |
| compacted-away persisted output path exists | restoration message includes the path |
| preserved tail starts with tool result | matching tool-call AI message is preserved |
| summarizer raises or returns invalid summary | original history preserved |
| `threshold_tokens < 1` | `ValueError` |
| `keep_recent_messages < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_compact_summarizer.py`
- `coding-deepgent/tests/test_app.py`

Required assertion points:

- threshold crossing triggers summarizer-backed context collapse
- collapse fail-open preserves original messages
- collapsed history shape includes boundary and summary messages
- restoration message includes collapsed-away persisted-output paths when present
- tool-call/tool-result tail pairing is preserved
- collapse runs before auto-compact in the middleware pipeline

## Scenario: Live Auto-Compact And Restoration

### 1. Scope / Trigger

- Trigger: changes touching live compact thresholding, compact summarizer use
  during a model call, or post-compact restoration messages.
- Applies when runtime pressure handling can proactively summarize older live
  history before a model call and preserve a bounded continuation tail.
- This is a cross-layer contract because message estimation, summarizer usage,
  compact boundary shape, preserved-tail rules, and restoration hints must
  agree.

### 2. Signatures

```python
def estimate_message_tokens(messages: Sequence[BaseMessage]) -> int: ...

def maybe_auto_compact_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
) -> list[BaseMessage]: ...

def compact_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
) -> list[BaseMessage]: ...

def reactive_compact_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
) -> list[BaseMessage]: ...
```

### 3. Contracts

- Auto-compact must remain middleware-level request rewriting. It must not
  introduce a custom query runtime in this stage.
- `estimate_message_tokens(...)` may use local deterministic token estimates.
  It is not provider billing/tokenizer output.
- Local live compact thresholds may be settings-backed. The current local
  threshold and kept-tail counts are product config, not provider-discovered
  context-window truth.
- If estimated message tokens are below `threshold_tokens`, messages must remain
  unchanged.
- If estimated message tokens exceed `threshold_tokens`, the middleware may call
  the compact summarizer through the provided model-like `.invoke()` seam.
- If a current valid session-memory artifact is present in runtime state,
  live compact may pass it to the summarizer as bounded assist text.
- After a successful live auto-compact or reactive compact, the runtime may
  refresh `state["session_memory"]` through the existing local threshold policy.
  This refresh remains bounded and local; it is not a separate background
  extraction workflow.
- Summarizer failure must fail open in this stage: the original message history
  must be preserved so later fallback behavior can still run.
- `compact_live_messages_with_summary(...)` must produce:
  1. one live compact boundary `SystemMessage`
  2. one live compact summary `HumanMessage`
  3. optional restoration `SystemMessage` for compacted-away persisted-output
     paths
  4. preserved recent tail messages
- If the preserved tail starts with a `ToolMessage`, the helper must include the
  matching prior `AIMessage` tool call when present.
- Restoration messages may only include persisted-output paths that were
  compacted away and are not already present in the preserved tail.
- If the model call still fails with a prompt-too-long style error after the
  proactive path, runtime pressure middleware may perform one reactive compact
  retry using the same summarizer seam.
- Reactive compact must only retry once per intercepted model call in this
  stage. Non prompt-too-long failures must be re-raised unchanged.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| estimated tokens below threshold | history unchanged |
| estimated tokens above threshold and summarizer succeeds | live compact boundary + summary + preserved tail returned |
| current session-memory artifact exists | summarizer request receives bounded assist text |
| successful live compact with missing/stale session memory | runtime state may refresh `session_memory` with `source=live_compact` |
| compacted-away persisted output path exists | restoration message includes the path |
| preserved tail starts with tool result | matching tool-call AI message is preserved |
| summarizer raises or returns invalid summary | original history preserved |
| handler raises prompt-too-long style error | one reactive compact retry is attempted |
| handler raises non prompt-too-long error | error is re-raised without retry |
| `threshold_tokens < 1` | `ValueError` |
| `keep_recent_messages < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_compact_summarizer.py`
- `coding-deepgent/tests/test_app.py`

Required assertion points:

- threshold crossing triggers proactive compact
- current session-memory artifact can flow into live compact assist text
- successful live compact can refresh in-memory/session runtime `session_memory` state when due
- compacted history shape includes boundary and summary messages
- restoration message includes compacted-away persisted-output paths
- tool-call/tool-result tail pairing is preserved
- summarizer failures do not corrupt the live history
- prompt-too-long fallback retries only once

## Scenario: Runtime Pressure Recovery Summary

### 1. Scope / Trigger

- Trigger: changes touching recovery brief contributions or compact/runtime
  event aggregation across resume boundaries.
- Applies when runtime pressure activity should be summarized in recovery
  surfaces after the session is resumed.

### 2. Contracts

- Recovery brief contributions may aggregate `runtime_event` evidence with
  `event_kind in {"snip", "microcompact", "context_collapse", "auto_compact",
  "reactive_compact"}` into a bounded `Runtime pressure:` section.
- The section must remain summary-only:
  - counts by event kind are allowed
  - raw compact payloads, raw summaries, and full prompt contents are not
    allowed
- If no runtime pressure events exist, the contribution may return `None`.

### 3. Tests Required

- `coding-deepgent/tests/test_session_contributions.py`
- any focused recovery brief rendering regressions touched by the change

## Scenario: Live Runtime Pressure Observability

### 1. Scope / Trigger

- Trigger: changes touching runtime-pressure event emission, session evidence
  persistence for compact events, or event metadata for live compact behavior.
- Applies when microcompact / auto-compact / reactive compact should become
  observable through `event_sink` and, when recording is active, through
  bounded session evidence.

### 2. Contracts

- Runtime pressure middleware may emit structured `RuntimeEvent` records for:
  - `snip`
  - `microcompact`
  - `context_collapse`
  - `auto_compact`
  - `reactive_compact`
- Event metadata must stay bounded and may include:
  - `source == "runtime_pressure"`
  - `strategy`
  - `hidden_messages`
  - `cleared_tool_results`
  - `collapsed_messages`
  - `restored_path_count`
  - `used_session_memory_assist`
- Session evidence persistence for runtime pressure events must reuse the
  existing `append_runtime_event_evidence(...)` seam rather than introducing a
  second compact-specific ledger.
- Runtime pressure event evidence must remain bounded summary evidence, not raw
  transcript dumps or full summarizer payloads.

### 3. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| snip happens during live request | `event_sink` receives `snip` event |
| microcompact happens during live request | `event_sink` receives `microcompact` event |
| context collapse happens during live request | `event_sink` receives `context_collapse` event |
| auto-compact happens during live request | `event_sink` receives `auto_compact` event |
| reactive compact retry happens | `event_sink` receives `reactive_compact` event |
| active `session_context` exists | whitelisted runtime pressure events append `runtime_event` session evidence |
| no `session_context` exists | events may still reach `event_sink`, but evidence is not appended |

### 4. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- existing runtime event tests in `coding-deepgent/tests/test_hooks.py`
- existing runtime event evidence tests in `coding-deepgent/tests/test_tool_system_middleware.py`
