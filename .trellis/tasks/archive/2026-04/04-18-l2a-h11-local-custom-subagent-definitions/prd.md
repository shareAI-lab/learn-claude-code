# L2-a: H11 local custom subagent definitions

## Goal

支持项目本地自定义 subagent definition，让用户可以在 repo 里声明自己的 agent 并被 `run_subagent` 加载使用。

## Requirements

* 选定一个稳定的 repo-local definition source，并在本任务内固定下来。
* 支持在本地 definition 中声明：
  * agent type / name
  * description
  * when-to-use
  * prompt body or equivalent instruction content
  * tool allowlist / disallow list
  * `max_turns`
  * `model_profile`
* Built-in 和 local custom agent 的合并顺序必须稳定、可预测。
* 无效 definition 必须显式报错，不静默忽略。
* 本任务只做 local custom agents，不做 plugin-provided agents。

## Acceptance Criteria

* [ ] repo-local custom agent definitions 可被加载并进入 agent catalog。
* [ ] 自定义 agent 能通过 `run_subagent` 真实执行。
* [ ] definition validation 对非法工具、重名 agent、无效字段有覆盖测试。
* [ ] built-in catalog 不会被 custom loading 意外破坏。

## Dependencies

* Depends on `04-18-l1b-h11-built-in-subagent-catalog-expansion`.

## Context Sources

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Out of Scope

* Plugin source tiers
* Remote agent definitions
* Background agent lifecycle
