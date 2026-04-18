# L2-c: H11 H12 subagent and fork resume foundation

## Goal

为 built-in / local custom subagent 和 fork 增加最小可用的 resume foundation，让中断后的 child execution 可以恢复。

## Requirements

* Resume 必须基于已持久化的 lineage / metadata / transcript seam，而不是凭推断重建。
* 普通 subagent resume 需要保留：
  * agent identity
  * tool surface
  * turn/model settings
* fork resume 需要保留：
  * rendered prompt continuity
  * visible tool continuity
  * fork continuity state
* 对缺失 / 损坏 / 过期 resume state，必须显式失败。
* 优先支持 built-in 与 local custom agents；不要求 background lifecycle。

## Acceptance Criteria

* [ ] subagent resume 可以恢复同一 child identity 和核心执行约束。
* [ ] fork resume 可以恢复同一 continuity contract，而不是退化成普通 subagent。
* [ ] resume 对缺失 state / worktree drift / invalid metadata 有明确错误行为。
* [ ] resume 不破坏现有 session / sidechain / evidence 边界。

## Dependencies

* Depends on `04-18-l2a-h11-local-custom-subagent-definitions`.
* Depends on `04-18-l2b-h12-fork-continuity-contract-closeout`.

## Context Sources

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/spec/backend/task-workflow-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

## Out of Scope

* Background agent resume
* Multi-agent mailbox recovery
* Coordinator workflow recovery
