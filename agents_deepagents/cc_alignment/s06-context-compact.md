# s06: Context Compact — CC Alignment Progress

## Scope

`s06_context_compact.py` is the tutorial-track context-compression chapter. Its
job is to make the active model context smaller while preserving enough
canonical history and recovery metadata for continued work.

The current implementation is a **cc-haha-inspired LangChain teaching pipeline**.
It is not a production clone of Claude Code's compact runtime.

## CC reference points

Primary reference: `NanmiCoder/cc-haha` at commit
`5fa3247f9fa3ddde462185218f7e73b2dccfc956`.

Source-backed public reference points used for this chapter:

- `src/query.ts` — pre-model compression order:
  `applyToolResultBudget -> snipCompactIfNeeded -> microcompactMessages -> contextCollapse.applyCollapsesIfNeeded -> autoCompactIfNeeded`.
- `src/utils/toolResultStorage.ts` — large tool-result persistence,
  `<persisted-output>` markers, per-message budget, and replacement decisions.
- `src/services/compact/microCompact.ts` — compactable tool set, old result
  clearing, time-based/cached microcompact concepts, and microcompact boundary.
- `src/services/compact/autoCompact.ts` — threshold calculation, summary budget,
  auto-compact trigger, failure circuit breaker.
- `src/services/compact/compact.ts` and `src/commands/compact/compact.ts` —
  manual compact, summary prompt, compact boundary, prompt-too-long retry, and
  post-compact restore hooks/attachments.
- cc-haha docs describe the four high-level layers as **snip**, **micro**,
  **context collapse**, and **auto compact**.

Public-source caveat:

- `snipCompact` and `contextCollapse` internals are feature-gated references in
  the public tree; their full implementations were not available in the fetched
  source. Our s06 versions are therefore documented as teaching equivalents, not
  line-for-line reproductions.

## Aligned

These parts intentionally match the visible CC / cc-haha structure or behavior.

### 1. Stage order is explicit

Current s06 exports the same teaching order:

```python
PIPELINE_STAGE_ORDER = (
    "apply_tool_result_budget",
    "snip_projection",
    "microcompact_messages",
    "context_collapse",
    "auto_compact_if_needed",
    "reactive_compact_on_overflow",
)
```

This mirrors the cc-haha idea that compression is not one magic summary call; it
is a staged model-context preparation pipeline.

### 2. Large tool output does not flood active context

Current s06 implements:

```python
apply_tool_result_budget()
```

Aligned behavior:

- oversized tool outputs are persisted outside active context;
- model-visible content becomes a `<persisted-output>` preview marker;
- replacement decisions are tracked by tool call id;
- repeated passes re-use prior replacement decisions.

This aligns with cc-haha's large-output persistence and per-message budget
strategy, but uses a small local teaching storage path instead of production
session storage infrastructure.

### 3. Old tool results can be microcompacted

Current s06 implements:

```python
microcompact_messages()
```

Aligned behavior:

- only compactable tools are considered;
- recent tool results are preserved;
- older tool results are replaced with a placeholder;
- a microcompact boundary records what happened.

This matches the core cc-haha microcompact goal: keep old tool noise from
consuming model context.

### 4. Auto compact is threshold-triggered

Current s06 implements:

```python
auto_compact_if_needed()
```

Aligned behavior:

- estimate the model-facing context size;
- compact when it exceeds a threshold;
- generate a summary;
- keep recent context;
- record a compact boundary.

This matches cc-haha's auto-compact purpose, with deterministic summarizers in
place of live model calls for tests.

### 5. Overflow recovery tries collapse before full compact

Current s06 implements:

```python
reactive_compact_on_overflow()
```

Aligned behavior:

```text
prompt/context overflow
  -> try collapse drain first
  -> if still too large, reactive full compact
```

This mirrors cc-haha's prompt-too-long recovery shape: drain staged collapse
before falling back to reactive compact.

### 6. State keeps compression metadata visible

Current s06 uses typed state such as:

- `ContextCompressionState`
- `ContextMessage`
- `PersistedOutput`
- `CompactBoundary`
- summaries
- transitions

This aligns with the CC principle that compression must leave recoverable
metadata, not silently delete history.

## Partially aligned / teaching equivalent

### 1. Snip projection

Current s06 implements:

```python
snip_projection()
```

What it models:

- canonical history remains in `state.messages`;
- `state.model_messages` becomes the smaller model-facing view;
- a snip boundary records the projection.

Why it is partial:

- public cc-haha source exposes snip integration points, but not the full
  `snipCompact` implementation;
- our version is a LangChain-native teaching equivalent of the observed goal.

### 2. Context collapse

Current s06 implements:

```python
context_collapse()
```

What it models:

- older groups are summarized first;
- recent groups remain verbatim;
- summary metadata is retained;
- recovery can drain staged collapse before reactive compact.

Why it is partial:

- public cc-haha source exposes `contextCollapse.applyCollapsesIfNeeded()` and
  `recoverFromOverflow()` integration points, but not full internals;
- our version is a staged-summary teaching equivalent.

### 3. LangChain-native message/state boundary

Current s06 uses typed Python dataclasses and a small `build_agent()` surface.
This is intentionally smaller than cc-haha's TypeScript runtime, but keeps the
important LangChain-side boundary clear:

```text
canonical history != model-facing projection
```

## Not aligned / intentionally not copied

These are production-level CC details that s06 does **not** implement yet.

### 1. Real provider cache edits

Not copied:

- Anthropic cache edit APIs;
- `cache_deleted_input_tokens` accounting;
- prompt-cache-preserving delete operations.

Reason:

- provider cache edits are production/runtime infrastructure;
- the chapter only needs to teach the behavior: old tool results can be made
  lighter while preserving recoverability.

### 2. Full `snipCompact` internals

Not copied:

- exact snip algorithm;
- hidden feature-gated implementation details.

Reason:

- not fully available in public cc-haha source;
- implemented as honest teaching equivalent.

### 3. Full `contextCollapse` internals

Not copied:

- exact collapse store;
- full staged collapse commit log;
- production collapse projection rules.

Reason:

- not fully available in public cc-haha source;
- implemented as observable behavior equivalent.

### 4. Session memory compaction

Not copied:

- session memory extraction;
- `lastSummarizedMessageId`;
- memory-file truncation;
- resumed-session compact path.

Reason:

- this belongs to a later memory/product-runtime stage.

### 5. Pre/post compact hooks

Not copied:

- PreCompact hooks;
- PostCompact hooks;
- SessionStart hook replay;
- hook-provided summary instructions.

Reason:

- hooks are a separate subsystem and should not be pulled into s06 before its
  own chapter/stage.

### 6. Prompt-cache-sharing fork

Not copied:

- forked compact agent;
- prompt-cache-sharing parameters;
- streaming fallback retry loop.

Reason:

- production optimization, not required for a deterministic teaching version.

### 7. GrowthBook / telemetry / feature flags

Not copied:

- remote config;
- analytics events;
- experiment gates;
- circuit-break telemetry.

Reason:

- not relevant to the local teaching track.

### 8. Full token accounting and media recovery

Not copied:

- exact tokenizer budgets;
- image/document token handling;
- media-size recovery;
- model-specific context window logic.

Reason:

- s06 uses deterministic character-count budgets so tests remain no-network and
  stable.

### 9. Full UI/transcript restore system

Not copied:

- compact boundary UI components;
- transcript segment storage;
- recent file restore attachments;
- plan/skills/background-agent rehydration attachments.

Reason:

- those are product UI/runtime persistence concerns. s06 records compact
  boundaries, persisted outputs, summaries, and transitions as the teaching
  substrate.

## Tests / evidence

Current deterministic verification:

```sh
PYTHON_DOTENV_DISABLED=1 python -m pytest \
  tests/test_s06_context_compact_baseline.py \
  tests/test_deepagents_track_smoke.py \
  tests/test_stage_track_capability_contract.py -q
```

Expected result:

```text
23 passed
```

Other checks used during completion:

```sh
PYTHON_DOTENV_DISABLED=1 python -m py_compile agents_deepagents/*.py
git diff --check
git diff --name-only -- coding-deepgent
```

The s06 baseline tests assert:

- source-backed / inferred / simplification metadata exists;
- oversized tool output is persisted and replaced with a marker;
- replacement decisions are reused;
- snip projection shrinks model-facing context while preserving canonical
  history;
- microcompact keeps recent tool results and clears older ones;
- context collapse summarizes older groups and keeps recent groups;
- auto compact produces summary + recent context;
- reactive compact records collapse-before-reactive transition order;
- s06 is the first chapter exposing the `compact` capability in stage gating.

## Next alignment candidates

Future work should not add random s06 details. The most valuable next alignment
work is to connect context compression to other runtime state.

1. **TodoWrite preservation**
   - Product compact should preserve current `todos`, active todo, and recent
     completed/pending context.
2. **Subagent boundaries**
   - Decide whether child agents inherit parent compression state or get their
     own isolated context.
3. **Skill state**
   - Preserve invoked skill metadata/content across compact events.
4. **Session memory**
   - Add a real memory extraction / resumed-session compact story only after the
     memory chapter/product stage exists.
5. **Hooks**
   - Add PreCompact/PostCompact behavior only after the hook system is in scope.
6. **Product migration**
   - If this moves into `coding-deepgent/`, write a separate product-stage plan;
     do not copy the tutorial module directly as production runtime.
