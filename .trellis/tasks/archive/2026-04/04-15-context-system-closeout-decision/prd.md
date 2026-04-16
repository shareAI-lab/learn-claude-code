# brainstorm: context system closeout decision

## Goal

判断 `coding-deepgent` 当前上下文系统是否已经覆盖原教程的核心压缩机制，并在用户决定补齐缺口后，定义 `Snip` 与 `Collapse` 的最小产品化实现范围，使四层压缩机制都通过 LangChain middleware 管线进入模型调用前上下文准备流程。

## What I already know

* 当前主线范围是 `coding-deepgent/`，教程层默认 reference-only。
* 原教程 `agents_deepagents/s06_context_compact.py` 的教学压缩流水线包含六段：`apply_tool_result_budget`、`snip_projection`、`microcompact_messages`、`context_collapse`、`auto_compact_if_needed`、`reactive_compact_on_overflow`。
* 当前 `coding-deepgent` 已实现 tool-result persistence、microcompact、auto compact、reactive compact、manual/generated compact resume、append-only compact records、load-time compacted history、recovery brief、session-memory assist/update、runtime pressure evidence。
* Focused tests 已通过：`pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_compact_artifacts.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py -q`，结果 `69 passed`。
* Roadmap 中 H05/H06/H07 已标为 implemented，当前推荐下一步是 Approach A MVP release validation / PR cleanup。

## Assumptions (temporary)

* “完成上下文系统模块”指完成 Approach A MVP 的上下文/压缩/恢复/记忆最小产品边界，而不是完整复刻 cc-haha compact runtime。
* `snip_projection` 和 `context_collapse` 可作为 future enhancement，除非用户要求完整 six-stage parity 才算完成。
* 运行中 model-visible `compact` tool 或 `/compact` 命令不是当前 MVP 必需项，因为主线已有 CLI resume manual/generated compact 与 runtime pressure auto/reactive compact。

## Open Questions

* none

## Requirements (evolving)

* 给出上下文系统机制覆盖矩阵。
* 明确哪些机制已实现、哪些是产品化替代、哪些是有意 deferred。
* 补齐 `Snip` 和 `Collapse`，使 `Snip`、`MicroCompact`、`Collapse`、`AutoCompact` 四层机制都存在于当前主线。
* 四层机制应进入 LangChain `AgentMiddleware.wrap_model_call()` 之前/之中的模型调用上下文准备链路；核心算法可保留为可单测 helper。
* 不引入自定义 query loop，不绕开 LangChain/LangGraph `create_agent` runtime。
* `Collapse` 采用 summarizer-based 方案：超过 collapse 阈值时，通过现有 fakeable summarizer seam 生成旧上下文摘要。
* `Collapse` 失败时 fail-open：保留原始 model-facing messages，继续进入后续 `AutoCompact` 判断。
* `Collapse` 生成的 live collapse artifact 只作用于当前 model call，不写入 JSONL transcript，不创建 persisted compact record。

## Acceptance Criteria (evolving)

* [x] `Snip` 在进入模型调用前可 deterministic 地缩小 model-facing projection，同时不修改 persisted transcript/session history。
* [x] `Collapse` 在进入 `AutoCompact` 前可用 summarizer 压缩旧上下文，并保留 recent tail 与 tool-call/tool-result pairing。
* [x] `Collapse` summarizer 失败或返回无效 summary 时 fail-open，不破坏后续 model call。
* [x] `MicroCompact` 与 `AutoCompact` 现有测试保持通过。
* [x] 新增 focused tests 覆盖 `Snip -> MicroCompact -> Collapse -> AutoCompact` 顺序。
* [x] 新增或更新 Trellis contract，说明四层压缩顺序、失败策略和不持久化 live rewrite 的边界。

## Definition of Done (team quality bar)

* Tests added/updated if implementation follows.
* Lint / typecheck / focused tests green if implementation follows.
* Docs/notes updated if behavior or roadmap status changes.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* 不做 cc-haha line-by-line clone。
* 不把 provider-specific token/cost/cache behavior 作为当前上下文 MVP 必需项。
* 不实现 cc-haha 完整 `snipCompact` / `contextCollapse` 内部算法复刻，只实现本地产品需要的 LangChain-native 等价语义。
* 不把 Bridge / daemon / coordinator / mailbox 拉回当前上下文模块。

## Technical Notes

* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`: runtime microcompact, auto compact, reactive compact, event/evidence.
* `coding-deepgent/src/coding_deepgent/compact/tool_results.py`: large tool result persistence and preview marker.
* `coding-deepgent/src/coding_deepgent/compact/artifacts.py`: manual compact artifact shape.
* `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`: append-only message/state/evidence/compact ledger and compacted history selection.
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`: bounded session-memory artifact, compact assist, update thresholds.
* `coding-deepgent/src/coding_deepgent/cli.py`: resume with selected compacted history, manual compact summary, generated compact summary, session-memory option.
* `agents_deepagents/s06_context_compact.py`: reference tutorial six-stage context compression pipeline.
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`: H05/H06/H07 current MVP status.

## Decision (ADR-lite)

**Context**: 当前主线已实现 `MicroCompact` 和 `AutoCompact`，但缺少 `Snip` 与 `Collapse` 两个中间 pressure stage。用户希望补齐四层机制，并确认四层都应通过 LangChain middleware 链路实现。

**Decision**: 实现 `Snip + summarizer Collapse`。`Snip` 是 deterministic projection-only rewrite；`Collapse` 使用现有 compact summarizer seam 在 `AutoCompact` 前生成 live collapse summary。两者都只影响当前 model-facing messages，不直接持久化 transcript。

**Consequences**: 相比 deterministic collapse，summarizer collapse 语义更强、更接近 cc 的上下文压缩意图；代价是会增加一次潜在模型调用，因此必须具备阈值、fail-open、focused tests 和 bounded artifact 规则。

## Implementation Summary

* `Snip -> MicroCompact -> Collapse -> AutoCompact` 已接入 `RuntimePressureMiddleware.wrap_model_call()`。
* 新增 settings-backed thresholds / kept-tail knobs：`snip_threshold_tokens`、`collapse_threshold_tokens`、`keep_recent_messages_after_snip`、`keep_recent_messages_after_collapse`。
* `Snip` 是有损 projection-only stage，默认 `snip_threshold_tokens == None`，显式配置阈值后启用；这样避免在 Collapse/AutoCompact 摘要前默认静默丢掉旧上下文语义。
* 新增 runtime events / session evidence whitelist：`snip`、`context_collapse`。
* 更新 runtime pressure contracts 和 overview index。
* 验证：
  * `pytest -q coding-deepgent/tests` -> `261 passed`
  * `ruff check ...` -> passed
  * `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/sessions/runtime_pressure.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed
