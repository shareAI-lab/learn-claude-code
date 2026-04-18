# L1-a: H11 subagent max_turns and model routing

## Goal

补齐当前 `run_subagent` / `run_fork` 的 contract debt：让 `max_turns` 真正生效，并让不同 agent definition 能走不同模型配置。

## Requirements

* `run_subagent(max_turns=...)` 必须真正影响 child execution，而不是只通过 schema 校验。
* `run_fork(max_turns=...)` 必须真正影响 fork child execution。
* 运行时必须同时遵守：
  * 调用方请求上限
  * agent definition 自身上限
* `AgentDefinition.model_profile` 必须真正影响 child model selection。
* 现有 `general` / `verifier` 行为保持兼容，除本任务明确修正的 turn/model 行为外不回退。

## Acceptance Criteria

* [ ] `run_subagent(max_turns=1)` 和更高值在测试里表现出不同的 child turn ceiling。
* [ ] `run_fork(max_turns=1)` 和更高值在测试里表现出不同的 child turn ceiling。
* [ ] agent definition 可以声明不同 `model_profile`，并在 child runtime 中生效。
* [ ] 无效 turn/model 配置会显式报错，不静默 fallback。

## Dependencies

* Depends on the existing H11/H12 baseline in:
  * `04-17-l2a-h11-h12-agent-definition-general-runtime`
  * `04-17-l3a-h11-h12-subagent-sidechain-transcript`

## Context Sources

* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Out of Scope

* Adding new agent types
* Custom agent loading
* Background execution
