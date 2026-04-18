# L2-b: H12 fork continuity contract closeout

## Goal

把当前 fork 从“已有 lineage metadata 的 minimal slice”推进到更接近 Claude Code Chapter 9 的 continuity contract。

## Requirements

* 在保留独立 `run_fork` 入口的前提下，补强 fork continuity。
* 当前 `placeholder_layout` 不能只记录 paired ids，需要推进到真实可消费的 continuity seam。
* fork payload reconstruction 需要更接近完整 sibling continuity，而不是只追加 thin directive。
* 保持：
  * rendered system prompt continuity
  * visible tool snapshot continuity
  * recursion guard
* 不在本任务内引入 provider-specific cache API 或 background fork orchestration。

## Acceptance Criteria

* [ ] fork continuity state 比当前 metadata-only 版本更完整，并有结构化测试覆盖。
* [ ] 已完成 tool use / tool result 的 continuity 在 fork payload 中得到保留或重建。
* [ ] sibling fork 仍保持稳定 prompt/tool identity contract。
* [ ] recursion guard 与现有 sidechain audit 不回退。

## Dependencies

* Depends on `04-18-l1a-h11-subagent-max-turns-and-model-routing`.

## Context Sources

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Out of Scope

* Provider-specific cache tuning
* Background fork workers
* Mailbox / coordinator
