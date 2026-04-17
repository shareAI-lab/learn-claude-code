# stable message ids for compression projection

## Goal

在实现 durable collapse projection replay、compression timeline、和未来 cc-style selective snip 之前，为 persisted raw transcript 增加稳定 `message_id`。这样 collapse records、timeline、以及 UI explanation 可以引用明确消息，而不是继续依赖隐式 `message_index`。

## What I already know

* 用户明确要求这里按长期基础设施来做，不只追求当前最小改动。
* 用户最新明确要求：这里**不需要优先兼容旧方案/旧设计**，应优先长期架构、边界清晰、代码优雅。
* 用户进一步明确：当前实际上没有需要保留的旧数据，因此这里可以完全不做旧数据兼容。
* 当前 message records 只有：
  * `record_type == "message"`
  * `timestamp`
  * `role`
  * `content`
  * 可选 `message_index`
  * 可选 `metadata`
* `JsonlSessionStore.load_session()` 当前把 raw transcript 装成 `LoadedSession.history: list[dict[str, str]]`，只保留 `role/content`，不会保留 record-level metadata。
* 现有 compact/view 逻辑仍然依赖 `message_index` / message count：
  * `run_prompt_with_recording()` 录制时继续分配 contiguous `message_index`
  * compact tail replay 用 `original_message_count - kept_message_count`
* 这对现有 compact tail 足够，但对未来的 collapse records / projection replay 不够：
  * collapse record 需要指向具体 raw messages
  * timeline / UI explanation 需要稳定引用
  * selective snip/microcompact/collapse 未来会需要 “哪些消息被隐藏/摘要” 的稳定 key
* 当前 Stage 3 已被合法 split，原因就是这里还没有稳定消息 ID。

## Assumptions (temporary)

* `message_id` 应该是 append-time persisted field，而不是 load-time 临时计算值。
* 既然当前选择走 Approach A，`LoadedSession.history` 会被扩成富结构；设计目标应优先服务 future collapse/timeline/projection，而不是只为了减少当下改动。
* 旧 session/旧读取形状不是当前主导约束；如果和长期设计冲突，应优先长期设计。

## Open Questions

* `transcript_event` 本身应该采用什么记录形状？

## Requirements (evolving)

* Add stable `message_id` to persisted session message records.
* Keep raw transcript append-only.
* Upgrade `LoadedSession.history` to `list[SessionMessage]`.
* Do not pull `compacted_history` into the same type migration in this prerequisite.
* Future collapse records must be able to reference covered messages/ranges through stable message identity, not ad hoc replay indexes.
* Current compact record shape should be redesigned away from count/index semantics rather than preserved as the long-term foundation.
* The new session/compact foundation does not need to support legacy transcript or legacy compact schemas.

## Acceptance Criteria (evolving)

* [ ] New persisted message records include stable IDs.
* [ ] `LoadedSession.history` is typed as `SessionMessage`.
* [ ] Session tests cover the new typed raw transcript boundary.
* [ ] Runtime/session contracts are updated with executable field-level details.
* [ ] Collapse record/projection work can reference message IDs without inventing implicit indexes.
* [ ] New compact replay/load path only targets the new message-reference schema.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Collapse record implementation itself
* Collapse replay implementation itself
* Frontend visualization/timeline implementation
* Physical deletion of transcript records

## Research Notes

### What similar systems need

* Durable projection/timeline systems need a stable reference key for each raw message.
* Load-time derived hashes are tempting, but they are weaker for future schema evolution and harder to reason about in mixed old/new session transcripts.
* Keeping compatibility usually means:
  * persist the new field in raw records,
  * keep old aggregate/read APIs stable,
  * add a richer read surface in parallel for new consumers.

### Constraints from our repo/project

* `LoadedSession.history` is currently a simple `list[dict[str, str]]`; many tests and resume paths assume this.
* Existing compact replay depends on count/index math and should not be broken.
* Future collapse/timeline work needs message-level references, not just counts.
* Old JSONL sessions already exist and must remain loadable.

### Feasible approaches here

**Approach A: Persist `message_id` and widen `LoadedSession.history` directly** (Chosen)

* How it works:
  * append `message_id` into message records
  * load `history` as richer dicts, e.g. `{"role", "content", "message_id", ...}`
* Pros:
  * simplest mental model
  * new consumers can use `history` directly
* Cons:
  * wider blast radius
  * many existing tests/consumers likely need touch-up
  * prerequisite task也会承接一部分兼容改造

**Approach B: Persist `message_id`, keep `history` stable, add parallel raw-message surface** (Recommended)

* How it works:
  * append `message_id` into message records
  * keep `LoadedSession.history` as current role/content list for compatibility
  * add a parallel richer surface, e.g. `raw_messages` / `message_records`, for future collapse/timeline consumers
* Pros:
  * lowest-risk migration path
  * preserves current compact/resume callers
  * gives future Stage 3 work an explicit stable source of truth
* Cons:
  * two read surfaces briefly coexist
  * requires discipline about which callers should migrate later

**Approach C: Do not persist IDs; derive them on load from existing fields**

* How it works:
  * synthesize an ID from session_id + message_index + timestamp/content
* Pros:
  * smallest schema change now
* Cons:
  * weaker future contract
  * mixed old/new sessions become harder to reason about
  * not ideal for durable collapse/timeline references

## Expansion Sweep

### Future evolution

* collapse records will likely want `covered_message_ids` or message-id ranges
* visualization/timeline will probably want raw transcript + model-facing projection side by side

### Related scenarios

* CLI resume and generated compact summary should continue to work unchanged
* future selective snip and collapse replay should share the same message reference primitive

### Failure & edge cases

* partially corrupt new-format transcripts
* avoiding leakage of storage-layer details into the domain surface
* choosing a reference shape that works for both compact and future collapse/timeline use

## Technical Notes

* Files inspected:
  * `coding-deepgent/src/coding_deepgent/sessions/records.py`
  * `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  * `coding-deepgent/tests/test_sessions.py`
  * `coding-deepgent/tests/test_cli.py`
  * `.trellis/spec/backend/session-compact-contracts.md`
* Current likely ownership boundary:
  * append-time field definition -> `sessions/records.py`
  * widened load path -> `sessions/store_jsonl.py`
  * caller/test migration -> `tests/test_sessions.py`, `tests/test_cli.py`, `cli_service.py`
  * compact/projection payloads remain separate from raw transcript message domain objects in this prerequisite

## Decision (ADR-lite)

**Context**: Collapse replay/timeline needs stable references, and the chosen direction is to expose them directly through `LoadedSession.history` rather than adding a parallel read surface first.

**Decision**: Use Approach A — persist `message_id` and widen `LoadedSession.history` directly.

**Consequences**:

* Existing tests and callers that compare exact `{\"role\", \"content\"}` dicts will need updating or can be dropped if they only preserve the old shape.
* This creates a simpler long-term model for Stage 3 collapse replay.
* `LoadedSession.history` should no longer stay as bare dicts.
* The remaining design question is `SessionMessage` 的最终字段边界，以及后续边界转换放在哪一层。

## Decision (ADR-lite) - Local Representation

**Context**: `sessions.records` already uses frozen dataclasses for session-level domain objects. Message-level identity is currently the missing domain object.

**Decision**: Represent `SessionMessage` as a frozen dataclass in `sessions.records`, then convert explicitly at CLI/runtime/helper boundaries where dict payloads are still needed.

**Consequences**:

* This matches the existing `sessions.records` style better than TypedDict or Pydantic.
* It gives Stage 3 collapse/timeline work a stronger domain boundary.
* Existing callers such as `cli_service` and some tests will need explicit conversion helpers instead of `dict(message)` on plain dicts.
* 用户优先级要求这里更偏向“把基础设施立住”，因此后续决策会偏向长期可扩展性，而不是最小 blast radius。

## Decision (ADR-lite) - Field Boundary

**Context**: The chosen direction is to build long-lived transcript infrastructure, not just patch current collapse prerequisites. At the same time, compact/projection payloads already have a different shape and should not be folded into the same migration.

**Decision**: Use the balanced domain shape for `SessionMessage`:

* `message_id`
* `message_index`
* `created_at`
* `role`
* `content`
* `metadata: dict[str, Any] | None`

Apply this only to raw `LoadedSession.history` in this prerequisite. Keep `LoadedSession.compacted_history` and compact artifact payloads on their current projection-oriented dict shape for now.

**Consequences**:

* Raw transcript becomes a proper typed domain surface for future collapse/timeline work.
* `compacted_history` can be redesigned later as `ProjectionMessage` or similar instead of being forced into the raw-message model now.
* Current CLI/resume callers must adapt from bare dicts to explicit conversion helpers.

## Decision (ADR-lite) - Index Semantics

**Context**: The user explicitly prefers long-term architecture and code elegance over carrying forward old infrastructure. The previous model used `message_index` and count-based compact replay because stable message identity did not exist yet.

**Decision**: `message_index` should not remain a first-class domain field in `SessionMessage`.

`SessionMessage` should expose only:

* `message_id`
* `created_at`
* `role`
* `content`
* `metadata`

Transcript order should come from append order, and future replay/timeline work should prefer stable `message_id` references over index math.

**Consequences**:

* The raw transcript domain model stays clean.
* The next design question is the concrete reference shape for compact/collapse records.

## Decision (ADR-lite) - Compact Record Direction

**Context**: The current compact record schema still uses count/index semantics:

* `original_message_count`
* `summarized_message_count`
* `kept_message_count`

That model predates stable message identity and does not fit the new long-term transcript architecture.

**Decision**: Redesign compact records now toward stable message references instead of preserving count/index semantics as the future foundation.

**Consequences**:

* Existing compact replay logic should be treated as an old boundary to be replaced, not carried forward as the canonical design.
* Future compact/collapse/timeline work can share one message-reference model.
* The remaining design question is whether current compact replay/load path should migrate now or in the next step.

## Decision (ADR-lite) - Message Reference Shape

**Context**: Compact/collapse/timeline all need message references, but the future system may include both contiguous transcript spans and more selective/non-contiguous hiding.

**Decision**: Use a hybrid message-reference model:

* primary range semantics:
  * `start_message_id`
  * `end_message_id`
* optional explicit list for precise/non-contiguous cases:
  * `covered_message_ids`

This means:

* contiguous compact/collapse can use range boundaries cleanly
* future selective/snipped/non-contiguous views can still attach exact IDs
* timeline and UI explanation can render both broad span and exact coverage

**Consequences**:

* This is more future-proof than pure range.
* This is more efficient and readable than always storing only explicit ID lists.
* Future compact/collapse record schemas should converge on the same reference primitive rather than inventing per-feature variants.

## Decision (ADR-lite) - Migration Scope

**Context**: The user explicitly prefers long-term infrastructure over preserving old compact/count semantics. Leaving current compact replay on the old count-based model would keep the old design alive right at the moment the new transcript foundation is introduced.

**Decision**: In this prerequisite, migrate the current compact replay/load path to the new message-reference model at the same time as introducing `SessionMessage`.

This means the work scope now includes:

* new persisted `message_id`
* typed `SessionMessage`
* redesigned compact record schema using message references
* `load_session()` compact replay based on stable message references

**Consequences**:

* The prerequisite becomes larger, but the transcript/compact foundation stays coherent.
* Stage 3 collapse work can build on one reference model instead of crossing old/new compact semantics.
* The remaining design question is the minimal long-term compact record shape.

## Decision (ADR-lite) - Legacy Compact Records

**Context**: The user explicitly prefers architecture clarity over carrying old compact/count semantics forward. Legacy compact records are based on count/index math and do not match the new stable message-reference foundation.

**Decision**: Do not support legacy transcript or legacy compact schemas in the new foundation.

Behavior:

* new `load_session()` / replay path targets only the new typed transcript + new compact schema
* no fallback to raw-history-as-compacted-view for legacy compact data
* no synthetic legacy `message_id` generation
* unsupported old data formats may fail fast instead of entering dual-read compatibility paths

**Consequences**:

* No dual-read compatibility branch is needed.
* No offline migration tool is required.
* The new transcript/compact replay path stays clean and reference-based from day one.

## Decision (ADR-lite) - Compact Record Shape

**Context**: With stable `message_id` and no legacy-compatibility burden, compact records should become durable transcript-reference events rather than count/index summaries.

**Decision**: Use this new compact record shape as the long-term foundation:

* `record_type: "compact"`
* `version`
* `session_id`
* `timestamp`
* `trigger`
* `summary`
* `start_message_id`
* `end_message_id`
* optional `covered_message_ids`
* optional `metadata`

**Consequences**:

* Compact replay can move to stable message references immediately.
* The same reference primitive can be reused by future collapse/timeline work.
* The remaining design question is whether raw messages should also move into the same event family now.

## Decision (ADR-lite) - Transcript Event Family

**Context**: The user wants a long-term clean foundation for compact/collapse/timeline rather than separate feature-local record types.

**Decision**: Use one transcript event family with multiple concrete event kinds, instead of separate long-term record type families for compact and collapse.

Proposed direction:

* one transcript-event family
* `event_kind` distinguishes:
  * `compact`
  * `collapse`
  * future `snip` / related projection events if needed

**Consequences**:

* compact/collapse/timeline can share one event ingestion and replay model
* future projection features do not need to invent new per-feature persistence shapes
* the remaining design question is whether events should use a generic envelope shape or flatter per-event fields

## Decision (ADR-lite) - Raw Messages vs Events

**Context**: Raw transcript messages and derived projection events are both durable facts, but they are not the same kind of fact. Raw messages are the source transcript primitive; compact/collapse are derived event overlays on top of that primitive.

**Decision**: Keep raw messages as a distinct primitive. Do not fold them into the transcript event family.

**Consequences**:

* `SessionMessage` remains the raw transcript domain object.
* `compact` / `collapse` / future projection events live in the transcript event family.
* Replay/timeline can operate on a clean `messages + events` model instead of one overloaded event type.

## Decision (ADR-lite) - Storage Ledger

**Context**: The user prefers a long-term clean infrastructure, but also selected a single append-only session ledger rather than splitting transcript events into a second file.

**Decision**: Store raw messages and transcript events in the same append-only JSONL ledger.

This means the session ledger may contain multiple durable record families, for example:

* raw message records
* transcript event records
* state snapshots
* evidence

**Consequences**:

* event/message ordering stays naturally aligned in one time-ordered ledger
* timeline/replay does not need cross-file merge logic
* the remaining design question is the concrete `transcript_event` record shape

## Decision (ADR-lite) - Message ID Generation

**Context**: The user wants long-lived infrastructure rather than a minimal local patch. For future collapse replay, timeline, and debugging, IDs should be readable, deterministic, and aligned with the current append-only session model.

**Decision**: Use session-scoped deterministic message IDs generated from append order / `message_index`, not random UUIDs or content hashes.

Expected shape:

* stable per session
* deterministic at append time
* readable in logs/tests/debugging

Examples:

* `msg-000000`
* `msg-000001`

or equivalent deterministic formatting.

**Consequences**:

* New messages get stable IDs without introducing randomness.
* The ID model remains aligned with the current append-only / contiguous-index recording flow.
* Since legacy compatibility is no longer the leading constraint, we can redesign transcript loading around the new typed model instead of preserving the old dict shape.
