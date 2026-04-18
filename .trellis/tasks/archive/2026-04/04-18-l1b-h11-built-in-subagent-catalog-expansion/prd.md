# L1-b: H11 built-in subagent catalog expansion

## Goal

把当前只有 `general` / `verifier` 的 built-in subagent catalog 扩成更有用的第一批角色集合。

## Requirements

* 在现有 built-in catalog 上新增下一批内建角色，至少覆盖：
  * `explore`
  * `plan`
* 每个 built-in agent 都必须声明：
  * description
  * when-to-use
  * tool allowlist / disallow list
  * `max_turns`
  * `model_profile`
* 本批次新增 built-in agent 仍保持 read-only，不引入 write-capable coder agent。
* `run_subagent` schema / catalog / prompts / tests 必须一起更新。

## Acceptance Criteria

* [ ] built-in catalog 至少包含 `general`, `verifier`, `explore`, `plan`。
* [ ] 模型可见的 agent type surface 与 catalog 一致。
* [ ] 新 agent 有独立 prompt 和独立 limit/profile，不只是 `general` 换名复用。
* [ ] 现有 `general` / `verifier` 回归测试继续通过。

## Dependencies

* Depends on `04-18-l1a-h11-subagent-max-turns-and-model-routing`.

## Context Sources

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`

## Out of Scope

* Local custom agents
* Plugin agents
* Write-capable built-in agents
