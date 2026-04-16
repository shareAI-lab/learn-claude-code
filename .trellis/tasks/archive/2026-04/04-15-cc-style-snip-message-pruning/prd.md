# brainstorm: cc-style snip message pruning

## Goal

设计并实现 cc-style `Snip`：让 agent 或用户能选择性移除不再需要的旧消息区间，而不是只做 recent-tail trim。重点难点是定义“哪些消息可以被废弃/删减”的判断机制，并确保该机制安全、可恢复、可测试，且符合 `coding-deepgent` 的 LangChain-native runtime 边界。

## What I already know

* 用户希望实现更接近 cc 的 `Snip`，核心疑问是 agent 如何判断哪些消息可以被废弃删减。
* 当前 `coding-deepgent` 已有 runtime pressure pipeline：`Snip -> MicroCompact -> Collapse -> AutoCompact`。
* 当前 `Snip` 是 threshold + recent-tail projection trim，默认关闭，不是 cc-style selective removal。
* 当前 `MicroCompact` 已实现 `[Old tool result content cleared]` 旧工具结果清理。
* cc-haha 可见线索显示 `HISTORY_SNIP` 在 `microcompact` 前运行，且有 `SnipTool`、`/force-snip`、message id tags、removedUuids replay、resume filtering 等机制。
* LangChain 官方支持 transient model-context trimming、persistent message deletion、summarization middleware；但 cc-style selective snip 需要项目自己的策略和记录层。

## Assumptions (temporary)

* MVP 不追求完整复制 cc 内部 `snipCompact.ts` 算法，而是实现本项目可验证的 selective snip semantics。
* agent 不应该无约束删除上下文；必须有保守规则、可解释记录、可恢复边界。
* JSONL transcript 应保持 append-only；Snip 应通过 boundary/metadata 在 load/resume 时过滤 model-facing history，而不是物理删除历史。

## Open Questions

* MVP 里 agent 判断可删消息的策略应采用：用户/模型显式选择、规则建议 + 用户确认，还是自动策略？

## Requirements (evolving)

* 设计 cc-style Snip 的消息选择机制。
* 支持选择性移除中间旧消息，而不是只保留 recent tail。
* 保留 session transcript append-only。
* Snip 决策应可解释、可测试、可恢复。
* 保持 tool-call/tool-result pairing 和消息序列合法。
* 不引入自定义 query loop，优先使用 LangChain middleware/tool/runtime seams。

## Acceptance Criteria (evolving)

* [ ] 明确 MVP 的 Snip 决策策略。
* [ ] 明确哪些消息永远不能自动 snip。
* [ ] 明确 Snip boundary/metadata 的持久化和 resume replay 方式。
* [ ] 明确验证矩阵和 focused tests。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 不做 cc-haha line-by-line clone。
* 不实现 UI scrollback 或 IDE visual selection。
* 不物理删除 JSONL transcript 原始消息。
* 不让 agent 无记录、无边界地静默删除任意历史。

## Technical Notes

* Candidate implementation surfaces:
  * `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
  * `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  * `coding-deepgent/src/coding_deepgent/sessions/records.py`
  * `coding-deepgent/src/coding_deepgent/tool_system/*`
  * `coding-deepgent/src/coding_deepgent/settings.py`
* Existing contract surface:
  * `.trellis/spec/backend/runtime-pressure-contracts.md`
  * `.trellis/spec/backend/session-compact-contracts.md`

## Research Notes

### What cc-haha visibly does

* `HISTORY_SNIP` is feature-gated and runs before `microcompact` in `query.ts`.
* `snipCompactIfNeeded(messagesForQuery)` returns rewritten messages, `tokensFreed`, and optionally a boundary message.
* `snipTokensFreed` is passed into `autoCompact`, so autocompact thresholding accounts for tokens already removed by snip.
* `SnipTool` is feature-gated in `tools.ts`, and `/force-snip` is feature-gated in `commands.ts`.
* API-bound user messages receive `[id:...]` tags so Claude can reference messages when calling the snip tool.
* Session load applies snip removals by reading `snipMetadata.removedUuids` from boundary records. JSONL remains append-only; active history is filtered and parent links are relinked.
* This checkout references `snipCompact.js`, `snipProjection.js`, `SnipTool`, and
  `force-snip`, but their implementation files are not present in the local
  public tree. Therefore exact candidate-selection heuristics are not available
  to copy line-for-line from this checkout.
* Visible attachments logic has a context-efficiency nudge that appears after
  token growth without a snip; it nudges the agent toward using Snip but does not
  prove fully automatic deletion.

### What LangChain provides

* LangChain supports transient message trimming before model calls through middleware / trim helpers.
* LangChain supports persistent deletion with `RemoveMessage`, but that mutates graph state and requires reducer/state assumptions.
* LangChain `SummarizationMiddleware` is not Snip: it summarizes with an LLM and persistently replaces old messages with a summary.
* For this project, cc-style Snip should remain a project-specific tool/session contract rather than directly adopting SummarizationMiddleware.

### What opencode does

* `packages/opencode/src/session/compaction.ts` has `SessionCompaction.prune()`.
* `prune()` walks backward through messages/parts after at least two user turns,
  stops at an assistant summary or already compacted tool part, protects `skill`
  tool outputs, counts completed tool outputs, keeps roughly
  `PRUNE_PROTECT = 40_000` tokens of recent tool output, and marks older tool
  parts with `time.compacted` only when at least `PRUNE_MINIMUM = 20_000`
  tokens would be freed.
* `MessageV2.toModelMessagesEffect()` turns compacted tool outputs into
  `[Old tool result content cleared]`.
* opencode therefore has a concrete rule-based tool-output pruning strategy,
  not a cc-style selective message SnipTool. It answers part of the question:
  old completed tool outputs beyond a protected recent-token budget are safe
  candidates, except protected tools and already summarized/compacted regions.
* `packages/opencode/src/session/compaction.ts` also has full conversation
  compaction via a dedicated `compaction` agent and summary prompt.
* `packages/opencode/src/tool/truncate.ts` stores oversized tool output to a
  file and gives the model a path plus delegation hint.

### What OpenAI Codex does

* `codex-rs/core/src/compact.rs` implements manual/auto context compaction by
  running a compact task that summarizes history, then replaces history with
  selected recent user messages plus a summary.
* If compaction itself exceeds the context window, Codex removes the oldest
  history item and retries, preserving recent messages.
* `codex-rs/core/src/context_manager/history.rs` has `remove_first_item()` and
  `remove_last_item()` helpers that also remove corresponding tool call/output
  counterparts to preserve invariants.
* Codex truncates function/tool output payloads on record with a
  `TruncationPolicy`.
* I did not find a cc-style SnipTool or selective semantic message deletion in
  Codex. Codex relies on summarization compaction, oldest-item trimming under
  pressure, and tool-output truncation/invariant-preserving removal.

### Cross-project takeaway

* cc visible design: agent/user explicit Snip with message IDs and replay.
* opencode: rule-based old tool-output pruning plus full compaction.
* Codex: full compaction plus oldest-item trim retry and tool-output truncation.
* None of the inspected public sources show a safe fully automatic semantic
  message deletion algorithm. The strongest source-backed strategy is hybrid:
  explicit SnipTool for semantic deletion plus deterministic opencode-style
  tool-output pruning as an automatic safe subset.

### Foreign community / OSS notes

* Aider community issue `Aider-AI/aider#3607` proposes manual chat-history
  selection via a `/history` markdown file with checkboxes. The motivation is
  exactly selective context control: important old messages may be summarized
  away while unimportant recent messages remain raw and noisy. This is a
  community proposal, not evidence of a merged implementation.
* Roo Code discussion `Roo-Code#544` proposes a `ContextGraph` with operations
  such as `update`, `summarize`, `elide`, and `collapse`, plus auditability and
  selective restoration. This is close conceptually to cc-style Snip, but it is
  a design discussion/proposal rather than a concrete production algorithm.
* Cline community discussion `cline#3078` emphasizes cheap-model summarization
  and user review/override. It addresses context compression, but not selective
  deletion of arbitrary old message ranges.
* These community references reinforce the same pattern: selective semantic
  pruning is treated as a user/agent-controlled operation with auditability, not
  as a silent automatic heuristic.

### Constraints from our repo/project

* Current `JsonlSessionStore` loads `history` as `list[dict[str, str]]`, losing message metadata and stable IDs.
* Message records may have `message_index`, but `LoadedSession.history` currently omits it.
* There is no persisted `snip` record type or snip boundary metadata.
* Current runtime pressure `snip_messages()` is transient recent-tail trim, not selective removal.
* Tool system can expose a strict Pydantic `SnipTool`, but the model needs stable message IDs in visible context before it can call it safely.

### Feasible approaches here

**Approach A: Explicit Snip Tool With Safety Gates** (Recommended)

* How it works:
  * Add stable model-visible message refs for eligible recent/older messages.
  * Add `snip_messages` tool that accepts explicit message refs or ranges plus a reason.
  * Tool validates refs, expands paired tool-call/tool-result ranges, rejects protected messages, and appends a snip boundary/evidence record.
  * Resume/load applies snip removals virtually to model-facing history while preserving raw transcript.
* Pros:
  * Most cc-like and keeps the agent in charge, but only through explicit auditable action.
  * Decisions are explainable because every snip has refs + reason.
  * Easy to test Good/Base/Bad cases.
* Cons:
  * Requires message identity, boundary/replay, and protected-message rules before useful behavior.

**Approach B: Rule-Based Auto Snip Suggestions**

* How it works:
  * Middleware computes candidates such as superseded file reads, failed exploration branches, old long tool outputs with persisted paths, or completed task branches.
  * It emits suggestions/evidence, but does not remove until a tool/command accepts them.
* Pros:
  * Helps answer "which messages can be deleted" without trusting the model fully.
  * Can evolve toward automatic mode later.
* Cons:
  * Harder to tune; false positives are likely without semantic context.
  * Still needs explicit apply path.

**Approach C: Fully Automatic Snip**

* How it works:
  * Middleware silently removes low-value candidates once pressure exceeds a threshold.
* Pros:
  * Maximum context savings with no user/model intervention.
* Cons:
  * High risk of deleting important rationale or constraints.
  * Hard to debug and not aligned with current project safety posture.

### Initial recommendation

Start with Approach A plus an opencode-style deterministic tool-output pruning
subset. MVP should require explicit agent/user action for semantic message
deletion. Automatic pruning may be limited to old completed tool outputs beyond
a protected recent-token budget.

After reviewing Aider/Roo/Cline community discussions, keep that recommendation:
use an explicit SnipTool and avoid automatic semantic deletion. Consider a
future manual selection UX (`/history`-style list or CLI command) after the core
message-ref + boundary/replay contract exists.

### Source-backed clarification

From visible source, cc-style Snip appears to be explicit tool/command-driven
selective removal with nudges, not a purely automatic heuristic that silently
decides and deletes messages. We can copy that product shape, but not the hidden
implementation details from this checkout.

## Status

Deferred / research captured.

Reason:

* 用户判断 cc-style selective Snip 难度较高，暂不进入实现。
* 本 PRD 保留这次方向讨论、源码线索、国外开源/社区对照和后续推荐方案。
* 如果未来重启，建议从 explicit `SnipTool(message_refs, reason)` + boundary/replay 开始，而不是自动语义删除。
