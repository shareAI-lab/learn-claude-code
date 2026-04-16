# cc-style autocompact hardening

## Goal

规划实现更接近 cc Level 4 AutoCompact 的 5 个后续增强点，让当前 `coding-deepgent` 的 AutoCompact 从 MVP summary fallback 升级为更可靠、更可恢复、更可观测的长会话兜底机制。

当前只创建 Trellis planning task，不在本轮实现。

## Communication Requirement

解释或实现本任务时，优先使用具体场景描述功能价值，再映射到术语。

Example style:

* "压缩连续失败时不要一直烧 API" -> failure circuit breaker.
* "连生成摘要的请求都太长时，先丢最老历史再重试" -> compact PTL retry.
* "压缩后模型不能忘记 plan/skill/关键文件" -> post-compact restoration.

## Background

当前 `coding-deepgent` 已有 AutoCompact MVP：

* `maybe_auto_compact_messages(...)` 超阈值后调用 summarizer。
* 生成 live compact boundary + summary + recent tail。
* 可保留 compacted-away persisted output path。
* proactive summarizer failure fail-open。
* prompt-too-long 后有 `reactive_compact_messages(...)` retry。
* manual/generated resume compact records 独立于 raw history。

cc-haha 完整 AutoCompact 额外包含：

* consecutive failure circuit breaker。
* compact request prompt-too-long retry by truncating oldest API-round groups。
* structured `CompactionResult` with boundary, summary, kept messages, attachments, hook results, token counts, usage。
* post-compact restoration for files, plan, plan mode, skills, async agents, tool/agent/MCP deltas, session-start hooks。
* PreCompact/PostCompact hook lifecycle。

## Planned Feature Points

### 1. Failure Circuit Breaker

Scenario:

AutoCompact 连续失败，例如 summarizer 一直 prompt-too-long 或 provider 一直报错。系统不应该每一轮都继续尝试压缩，浪费 API 和时间。

Future behavior:

* Track consecutive AutoCompact failures in runtime/session state.
* Reset failure count on successful compact.
* Skip proactive AutoCompact after configured max failures.
* Reactive compact may still surface one bounded failure path if needed.

Acceptance:

* [ ] repeated proactive AutoCompact failures stop after max count.
* [ ] successful compact resets failure count.
* [ ] runtime evidence records circuit-breaker skip.

### 2. Compact Request Prompt-Too-Long Retry

Scenario:

历史太长，连“请 summarizer 总结这段历史”的请求本身都超上下文窗口。此时不能直接卡死，需要裁掉最老历史分组后重试摘要。

Future behavior:

* Detect prompt-too-long from compact summarizer call.
* Drop oldest API-round/message groups from summary source.
* Retry up to bounded count, e.g. 3.
* Fail with bounded error if still too long.

Acceptance:

* [ ] compact summarizer PTL retries with older groups removed.
* [ ] retry count is bounded.
* [ ] tool-call/tool-result pairing remains valid in remaining source.
* [ ] failure is surfaced without corrupting session state.

### 3. Structured Compaction Result

Scenario:

After compact, later systems need to know what was generated: boundary, summary, kept tail, restored paths, token counts, and future hook/restoration messages. Ad hoc message lists make this hard to test and extend.

Future behavior:

* Introduce a local `CompactionResult` / `LiveCompactionResult` structure.
* Fields may include:
  * boundary message,
  * summary message,
  * preserved tail,
  * restoration messages,
  * pre/post estimated token counts,
  * trigger,
  * metadata.
* Provide one function to render final model-facing messages in stable order.

Acceptance:

* [ ] AutoCompact uses structured result internally.
* [ ] final message order is tested.
* [ ] runtime evidence uses result metadata.
* [ ] current tests remain behavior-compatible.

### 4. Post-Compact State Restoration

Scenario:

Before compact, the model had important working context: current plan, active todos, loaded skill, recently read file paths, verifier evidence, or running subagent status. After compact, summary alone may omit these, causing the agent to continue incorrectly.

Future behavior:

* Add bounded post-compact restoration contributions.
* Restore only high-value state:
  * active todos,
  * durable plan reference,
  * verifier evidence summary,
  * relevant persisted output paths,
  * loaded skill names/paths if available,
  * subagent/verifier lineage if relevant.
* Keep restoration summary-only and bounded.

Acceptance:

* [ ] post-compact context includes active todos/plan when present.
* [ ] verifier evidence remains visible after compact.
* [ ] restored persisted paths are not duplicated.
* [ ] restoration does not dump raw transcript or large payloads.

### 5. PreCompact / PostCompact Hooks

Scenario:

A project or user may need to influence compact behavior. Example: "compact 时特别保留数据库 schema 讨论" or "compact 后重新注入项目约束"。

Future behavior:

* Add local deterministic PreCompact hook contribution.
* PreCompact may add bounded custom instructions to summarizer.
* Add local deterministic PostCompact contribution.
* PostCompact may add bounded model-visible restoration context.
* Hooks must not call tools or mutate transcript unexpectedly.

Acceptance:

* [ ] PreCompact contribution can add compact instructions.
* [ ] PostCompact contribution can add bounded restoration context.
* [ ] invalid/blank hook output is ignored.
* [ ] hook output is represented in structured compaction result.

## Out of Scope

* No implementation in this turn.
* No provider-specific prompt-cache sharing or fork cache optimization yet.
* No frontend progress UI yet.
* No partial compact unless separately planned.
* No physical deletion of raw transcript records.

## Technical Notes

Likely files:

* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `coding-deepgent/src/coding_deepgent/compact/artifacts.py`
* `coding-deepgent/src/coding_deepgent/sessions/contributions.py`
* `coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py`
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`
* `coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`
* `coding-deepgent/src/coding_deepgent/settings.py`
* `coding-deepgent/tests/test_runtime_pressure.py`
* `coding-deepgent/tests/test_compact_artifacts.py`
* `coding-deepgent/tests/test_session_contributions.py`
* `.trellis/spec/backend/runtime-pressure-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

cc references:

* `/root/claude-code-haha/src/services/compact/autoCompact.ts`
* `/root/claude-code-haha/src/services/compact/compact.ts`
* `/root/claude-code-haha/src/commands/compact/compact.ts`

## Suggested Stage Order

1. Failure circuit breaker.
2. Compact request PTL retry.
3. Structured compaction result.
4. Post-compact state restoration.
5. PreCompact/PostCompact hooks.

## Status

Planning-only placeholder. Ready for future staged implementation.
