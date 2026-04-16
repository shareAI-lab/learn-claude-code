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

@dataclass(frozen=True, slots=True)
class MicrocompactStats:
    cleared_tool_results: int = 0
    kept_tool_results: int = 0
    tokens_saved_estimate: int = 0
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS
    protected_recent_tokens: int | None = DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS

@dataclass(frozen=True, slots=True)
class MicrocompactResult:
    messages: list[BaseMessage]
    stats: MicrocompactStats

def microcompact_messages_with_stats(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
    protect_recent_tokens: int | None = DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS,
    min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_PRUNE_SAVED_TOKENS,
) -> MicrocompactResult: ...

@dataclass(frozen=True, slots=True)
class TimeBasedMicrocompactDecision:
    attempted: bool
    result: MicrocompactResult | None = None
    gap_minutes: int | None = None

def maybe_time_based_microcompact_messages(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    context: object,
    gap_threshold_minutes: int | None,
    now: Callable[[], datetime],
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
    min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_SAVED_TOKENS,
    main_entrypoint: str = "coding-deepgent",
    main_agent_name: str = "coding-deepgent",
) -> TimeBasedMicrocompactDecision: ...

class RuntimePressureMiddleware(AgentMiddleware):
    registry: CapabilityRegistry
    microcompact_time_gap_minutes: int | None
    microcompact_min_saved_tokens: int
    microcompact_protect_recent_tokens: int | None
    microcompact_min_prune_saved_tokens: int
    main_entrypoint: str
    main_agent_name: str
```

### 3. Contracts

- `microcompact_messages(...)` must be deterministic and model-call local. It
  must not persist transcript mutations by itself.
- Only tool results whose originating tool capability is marked
  `microcompact_eligible` may be compacted.
- Error tool results must not be compacted.
- If the number of compactable tool results is less than or equal to
  `keep_recent_tool_results`, messages must remain unchanged.
- If `microcompact_protect_recent_tokens is None`, ordinary MicroCompact uses
  the existing count-based keep policy.
- If `microcompact_protect_recent_tokens` is configured, ordinary
  MicroCompact must use token-budget protection instead of count-based
  protection:
  - walk compactable successful tool results from newest to oldest
  - keep a newest suffix whose estimated content tokens fit within the budget
  - always keep at least one newest compactable tool result even if it exceeds
    the budget
  - clear older eligible compactable tool results outside that suffix
- If token-budget pruning would save fewer than
  `microcompact_min_prune_saved_tokens`, messages must remain unchanged and no
  microcompact event should be emitted.
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
- `microcompact_messages_with_stats(...)` must use the same rewrite semantics
  as `microcompact_messages(...)` and return bounded local observability stats.
- `tokens_saved_estimate` is a deterministic local estimate derived from the
  original cleared tool-result content minus the replacement marker content. It
  is not provider billing or exact tokenizer output.
- Time-based MicroCompact must be disabled when
  `microcompact_time_gap_minutes is None`.
- Time-based MicroCompact may run only for the configured main runtime context:
  `RuntimeContext.entrypoint == main_entrypoint` and
  `RuntimeContext.agent_name == main_agent_name`.
- If no parseable timestamp exists on a prior `AIMessage`, time-based
  MicroCompact must fail open and skip.
- If `now - latest_assistant_timestamp` is below
  `microcompact_time_gap_minutes`, time-based MicroCompact must skip.
- If the time-gap trigger fires, aggressive keep-recent must floor to at least
  one recent compactable tool result: `max(1, keep_recent_tool_results)`.
- If the time-gap trigger fires but estimated saved tokens are below
  `microcompact_min_saved_tokens`, no clearing occurs and the normal count-based
  MicroCompact fallback must not run for that model call.
- MicroCompact runtime event metadata must include bounded fields:
  - `cleared_tool_results` for backward compatibility
  - `tools_cleared`
  - `tools_kept`
  - `tokens_saved_estimate`
  - `keep_recent`
- Token-budget MicroCompact runtime event metadata must additionally include:
  - `protected_recent_tokens`
- Time-based MicroCompact runtime event metadata must additionally include:
  - `trigger == "time_gap"`
  - `gap_minutes`
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
| microcompact clears older tool results | runtime event and session evidence include cleared/kept counts plus local saved-token estimate |
| token-budget mode unset | existing count-based behavior is preserved |
| token-budget mode set | recent compactable tool results within protected budget remain inline |
| latest compactable result exceeds token budget | latest compactable result remains inline; older eligible results may clear |
| token-budget estimated savings below minimum | no clearing and no event |
| time-based microcompact disabled | no time-gap evaluation or event |
| non-main runtime context | no time-based clearing |
| no assistant timestamp | no time-based clearing |
| idle gap under threshold | no time-based clearing |
| idle gap over threshold | older eligible tool results clear before count-based fallback |
| estimated savings below configured minimum | no clearing and no count-based fallback for that call |
| `keep_recent_tool_results < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_app.py`
- `coding-deepgent/tests/test_memory_integration.py`

Required assertion points:

- older eligible tool results are compacted deterministically
- recent eligible tool results remain inline
- ineligible tool results are not rewritten
- microcompact event/evidence metadata remains bounded and includes
  `tools_cleared`, `tools_kept`, `tokens_saved_estimate`, and `keep_recent`
- token-budget MicroCompact covers default compatibility, protected recent
  budget, keep-at-least-one behavior, minimum-savings skip, and
  `protected_recent_tokens` metadata
- time-based MicroCompact covers disabled, non-main, missing timestamp,
  under-threshold gap, over-threshold gap, keep-recent floor, and minimum
  savings skip cases
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
    context_window_tokens: int | None = None,
    trigger_ratio: float | None = None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
    assist_context: str | None = None,
) -> list[BaseMessage]: ...

def collapse_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
) -> list[BaseMessage]: ...

@dataclass(frozen=True, slots=True)
class LiveCompactionResult:
    boundary_message: SystemMessage
    summary_message: HumanMessage
    preserved_tail: tuple[BaseMessage, ...]
    trigger: str
    restoration_messages: tuple[SystemMessage, ...] = ()
    original_token_estimate: int = 0
    projected_token_estimate: int = 0

    @property
    def restored_path_count(self) -> int: ...
    def render(self) -> list[BaseMessage]: ...

def collapse_live_messages_with_result(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
) -> LiveCompactionResult: ...
```

### 3. Contracts

- Context collapse must remain middleware-level request rewriting. It must not
  introduce a custom query runtime.
- If `threshold_tokens is None`, messages must remain unchanged.
- If `threshold_tokens is None` and no ratio trigger is configured, messages
  must remain unchanged.
- If estimated message tokens are below `threshold_tokens` and below configured
  `estimated_tokens / context_window_tokens >= trigger_ratio`, messages must
  remain unchanged.
- If the threshold is crossed, the helper may call the existing compact
  summarizer seam through the provided model-like `.invoke()` path.
- Ratio-triggered collapse uses deterministic local token estimates and
  configured `model_context_window_tokens`; it is not provider billing/tokenizer
  accounting.
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
- Collapse summaries remain live model-facing artifacts and must not be
  persisted as session compact records.
- When the runtime has both:
  - an active `session_context`, and
  - a non-model-visible transcript-projection lineage for the current request,
  a successful live collapse may persist a separate `transcript_event` collapse
  record to the session ledger.
- Collapse-record persistence must:
  - reference raw transcript coverage through stable `message_id` fields
  - skip persistence rather than invent coverage when the current live
    projection cannot be mapped back to raw transcript messages
  - keep bounded metadata only, such as trigger, estimated token count,
    entrypoint, agent name, and whether session-memory assist was used
- `collapse_live_messages_with_result(...)` must own boundary, summary,
  restoration messages, preserved tail, trigger, and token estimates.
- `collapse_live_messages_with_summary(...)` must remain a compatibility wrapper
  returning `collapse_live_messages_with_result(...).render()`.
- `LiveCompactionResult.render()` order is stable: boundary, summary,
  restoration messages, preserved tail.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| estimated tokens below threshold | history unchanged |
| threshold crossed and summarizer succeeds | live collapse boundary + summary + preserved tail returned |
| ratio trigger crossed and token threshold is unset | live collapse boundary + summary + preserved tail returned |
| threshold crossed during recorded session with transcript projection lineage | live collapse boundary + summary returned and one collapse transcript event is appended |
| current session-memory artifact exists | summarizer request may receive bounded assist text |
| compacted-away persisted output path exists | restoration message includes the path |
| preserved tail starts with tool result | matching tool-call AI message is preserved |
| summarizer raises or returns invalid summary | original history preserved |
| `threshold_tokens < 1` | `ValueError` |
| `context_window_tokens < 1` | `ValueError` |
| `trigger_ratio` outside `[0, 1]` | `ValueError` |
| `keep_recent_messages < 0` | `ValueError` |

### 5. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- `coding-deepgent/tests/test_compact_summarizer.py`
- `coding-deepgent/tests/test_app.py`
- `coding-deepgent/tests/test_sessions.py`

Required assertion points:

- threshold crossing triggers summarizer-backed context collapse
- ratio crossing can trigger summarizer-backed context collapse
- recorded live collapse can persist a collapse transcript event when raw
  projection lineage is available
- collapse fail-open preserves original messages
- collapsed history shape includes boundary and summary messages
- structured collapse result render order is stable and exposes bounded
  metadata such as trigger, restored path count, and estimated token counts
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
    state: Any = None,
    ptl_retry_limit: int = 0,
) -> list[BaseMessage]: ...

@dataclass(frozen=True, slots=True)
class AutoCompactResult:
    messages: list[BaseMessage]
    attempted: bool = False
    compacted: bool = False
    failed: bool = False

def maybe_auto_compact_messages_with_status(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
    state: Any = None,
    ptl_retry_limit: int = 0,
) -> AutoCompactResult: ...

def compact_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    state: Any = None,
) -> list[BaseMessage]: ...

def compact_live_messages_with_result(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    state: Any = None,
) -> LiveCompactionResult: ...

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
- `maybe_auto_compact_messages(...)` must remain a compatibility wrapper that
  returns only messages.
- `maybe_auto_compact_messages_with_status(...)` must distinguish threshold not
  attempted, attempted-and-compacted, and attempted-and-failed-open outcomes.
- `compact_live_messages_with_result(...)` must own boundary, summary,
  restoration messages, preserved tail, trigger, and token estimates.
- `compact_live_messages_with_summary(...)` must remain a compatibility wrapper
  returning `compact_live_messages_with_result(...).render()`.
- `LiveCompactionResult.render()` order is stable: boundary, summary,
  restoration messages, preserved tail.
- Post-compact state restoration may add bounded restoration `SystemMessage`
  entries through the structured result.
- Current local restoration state includes active todos from runtime state:
  `status in {"pending", "in_progress"}`.
- Active todo restoration must be bounded and must not include completed todos.
- Durable plan/verifier restoration requires a stable runtime-state source and
  should not be fabricated from unrelated stores.
- `PreCompact` hooks may contribute bounded `additional_context` that is passed
  to the compact summarizer through the existing assist-context seam.
- `PostCompact` hooks may contribute bounded `additional_context` that is
  rendered as restoration messages through `LiveCompactionResult`.
- Pre/PostCompact hooks must not call tools, mutate transcript records, or own
  compact persistence.
- Blank hook context is ignored; hook context is whitespace-normalized and
  bounded before becoming model-visible.
- `RuntimePressureMiddleware` may track consecutive proactive AutoCompact
  failures on the middleware instance when `auto_compact_max_failures` is set.
- Proactive AutoCompact failures increment only when the threshold was crossed
  and summarization/compaction failed open.
- A successful proactive AutoCompact resets the consecutive failure count.
- When the failure count reaches `auto_compact_max_failures`, later model calls
  skip proactive AutoCompact and emit bounded `auto_compact` runtime metadata:
  - `trigger == "failure_circuit_breaker"`
  - `failure_count`
  - `max_failures`
- `auto_compact_max_failures is None` preserves previous fail-open behavior
  without circuit-breaker skip events.
- When the proactive compact summarizer raises a prompt-too-long style error,
  `maybe_auto_compact_messages_with_status(...)` may retry with a shortened
  summary source up to `auto_compact_ptl_retry_limit`.
- Each prompt-too-long retry must drop the oldest summary-source message group
  and keep the original model-facing message list unchanged.
- If all prompt-too-long retries are exhausted, AutoCompact fails open and the
  attempt may count toward the failure circuit breaker.
- Non prompt-too-long summarizer failures must not enter the PTL retry loop.
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
- proactive path, runtime pressure middleware may first drain existing collapse
  summaries once, then perform one reactive compact retry using the same
  summarizer seam if the drained request still fails.
- Collapse drain removes bounded collapse summary text from the model-facing
  projection only. It must not delete or rewrite persisted raw transcript or
  collapse records.
- Reactive compact must only retry once per intercepted model call in this
  stage. Non prompt-too-long failures must be re-raised unchanged.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| estimated tokens below threshold | history unchanged |
| estimated tokens above threshold and summarizer succeeds | live compact boundary + summary + preserved tail returned |
| current session-memory artifact exists | summarizer request receives bounded assist text |
| successful live compact with missing/stale session memory | runtime state may refresh `session_memory` with `source=live_compact` |
| repeated proactive AutoCompact failures reach configured max | subsequent proactive AutoCompact is skipped and bounded skip event is emitted |
| proactive AutoCompact succeeds after prior failures | consecutive failure count resets |
| `auto_compact_max_failures is None` | summarizer failures continue to fail open without skip events |
| compact summarizer raises prompt-too-long and retry limit remains | oldest summary-source group is dropped and summarizer is retried |
| compact summarizer raises prompt-too-long until retry limit is exhausted | original history is preserved and the attempt fails open |
| compact summarizer raises non prompt-too-long error | no PTL retry loop; original history is preserved |
| compacted-away persisted output path exists | restoration message includes the path |
| runtime state has active todos during compact | restoration message includes bounded pending/in-progress todos |
| runtime state has completed todos only | no todo restoration message is added |
| PreCompact hook returns additional context | summarizer receives bounded assist context |
| PostCompact hook returns additional context | rendered compact projection includes bounded restoration context |
| Pre/PostCompact hook returns blank context | context is ignored |
| preserved tail starts with tool result | matching tool-call AI message is preserved |
| summarizer raises or returns invalid summary | original history preserved |
| handler raises prompt-too-long style error | one reactive compact retry is attempted |
| handler raises prompt-too-long after collapse projection exists | one collapse drain retry is attempted before reactive compact |
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
- structured compact result render order is stable and exposes bounded metadata
  such as trigger, restored path count, and estimated token counts
- restoration message includes compacted-away persisted-output paths
- active todos restore after live compact without dumping completed todos
- PreCompact and PostCompact hook additional context flows through bounded
  compact assist/restoration seams
- tool-call/tool-result tail pairing is preserved
- summarizer failures do not corrupt the live history
- failure circuit breaker skips repeated doomed proactive AutoCompact attempts
- successful proactive AutoCompact resets failure count
- prompt-too-long summarizer source retry is bounded and can succeed after
  dropping oldest context
- exhausted prompt-too-long summarizer retries fail open and can trip the
  failure circuit breaker
- prompt-too-long fallback retries only once
- collapse projection drain runs before reactive compact on prompt-too-long

## Scenario: Subagent Spawn Pressure Guard

### 1. Scope / Trigger

- Trigger: changes touching `run_subagent`, verifier child execution, runtime
  context pressure settings, or subagent evidence.
- Applies when high context pressure should block spawning child agents until
  the parent context is collapsed or compacted.

### 2. Contracts

- Spawn guard is disabled unless both `model_context_window_tokens` and
  `subagent_spawn_guard_ratio` are configured on `RuntimeContext`.
- The guard uses deterministic local token estimates over the current runtime
  state's model messages.
- If `estimated_tokens / model_context_window_tokens` is below the guard ratio,
  subagent execution proceeds unchanged.
- If the ratio is at or above the guard ratio, `run_subagent` returns a bounded
  model-visible warning and does not execute the child agent.
- The guard emits a bounded `subagent_spawn_guard` runtime event and, when an
  active `session_context` exists, appends bounded session evidence.
- Guard metadata may include only bounded pressure fields such as
  `estimated_token_count`, `context_window_tokens`, and
  `estimated_token_ratio_percent`.

### 3. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| guard settings unset | subagent execution proceeds unchanged |
| pressure below guard ratio | subagent execution proceeds unchanged |
| pressure at or above guard ratio | bounded block message is returned and child agent is not executed |
| recorded session exists | bounded `runtime_event` evidence is appended |

### 4. Tests Required

- `coding-deepgent/tests/test_subagents.py`

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
  - `subagent_spawn_guard`
- Event metadata must stay bounded and may include:
  - `source == "runtime_pressure"`
  - `strategy`
  - `hidden_messages`
  - `cleared_tool_results`
  - `tools_cleared`
  - `tools_kept`
  - `tokens_saved_estimate`
  - `keep_recent`
  - `protected_recent_tokens`
  - `trigger`
  - `gap_minutes`
  - `failure_count`
  - `max_failures`
  - `collapsed_messages`
  - `restored_path_count`
  - `used_session_memory_assist`
  - `estimated_token_count`
  - `context_window_tokens`
  - `estimated_token_ratio_percent`
  - `drained_summaries`
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
| subagent spawn guard blocks | `event_sink` receives `subagent_spawn_guard` event |
| active `session_context` exists | whitelisted runtime pressure events append `runtime_event` session evidence |
| no `session_context` exists | events may still reach `event_sink`, but evidence is not appended |

### 4. Tests Required

- `coding-deepgent/tests/test_runtime_pressure.py`
- existing runtime event tests in `coding-deepgent/tests/test_hooks.py`
- existing runtime event evidence tests in `coding-deepgent/tests/test_tool_system_middleware.py`
