# Staged Execution 指南

> **Purpose**: 用明确 checkpoint、验证预算和安全自动推进，执行多阶段 `coding-deepgent` 工作。

---

## When To Use

当一个任务族跨多个 sub-stage，且每个阶段都需要显式 checkpoint 后再继续时，使用这份 guide。

常见场景：

- staged feature families
- roadmap closeout slices
- checkpointed infrastructure upgrades
- 长时间实现但不能漂移的任务

---

## Modes

支持两种模式：

- `lean`（默认）
- `deep`

### `lean`

- 一次做一个 sub-stage
- 优先 focused tests
- 不重复读取已稳定的大量 source/docs
- 除非风险明确，不跑 full-suite validation
- checkpoint decision 为 `continue` 时，立即进入下一个 sub-stage

### `deep`

- 可以更广泛重新定向
- 可以做更广验证
- 用户明确要求时，可以把 docs/git/PR work 合入同一轮

未明确要求 long-running all-in-one 时，默认 `lean`。

---

## Sub-stage State Machine

每个 staged run 使用一个状态：

- `planning`
- `implementing`
- `verifying`
- `checkpoint`
- `terminal`

恢复已有 stage family 时，从当前 active state 继续，不从零重跑 orientation。

---

## Before Implementation

- Trellis task 存在
- PRD 存在
- expected benefit 具体
- 需要对齐时已有 source mapping
- 需要 LangChain 时已选 primitive
- out-of-scope 明确
- focused tests 已命名

如果是新 feature band，扩展研究；否则复用最近 verified PRD/checkpoint context。

---

## Validation Budget

默认：

- `lean`
  - focused tests
  - touched-file lint/typecheck
  - 只有 contract/runtime/cross-layer 风险明确时跑更广验证
- `deep`
  - focused + broader regression

当前 `coding-deepgent` 默认：

- focused validation first
- broader validation only on cross-layer/contract/runtime risk、ambiguous focused failures、或用户明确要求

---

## Checkpoint Gate

每个 sub-stage 结束时记录：

- implemented behavior
- tests run and result
- files changed
- alignment evidence（如适用）
- architecture evidence（如适用）
- boundary issues
- next sub-stage 是否仍成立

内部 verdict：

- `APPROVE`
- `ITERATE`
- `REJECT`

执行决策：

- `APPROVE` -> `continue`
- `ITERATE` -> `adjust` or `split`
- `REJECT` -> `stop`

规则：

- `continue` -> 立即开始下一 sub-stage
- `adjust` -> 先改写下一阶段计划
- `split` -> 创建 prerequisite task，并停止主线
- `stop` -> 停下来问用户

不要仅为了总结进度而停下 `continue` 的 staged run。

---

## Checkpoint Template

```md
## Checkpoint: <sub-stage>

State:
- planning | implementing | verifying | checkpoint | terminal

Verdict:
- APPROVE | ITERATE | REJECT

Implemented:
- ...

Verification:
- ...

Alignment:
- source files inspected:
- aligned:
- deferred:
- do-not-copy:

Architecture:
- primitive used:
- why no heavier abstraction:

Boundary findings:
- ...

Decision:
- continue | adjust | split | stop

Reason:
- ...
```

---

## Stop Conditions

停止并询问用户：

- 下一阶段 scope 已经不成立
- 测试失败且修复不局限于当前 sub-stage
- alignment-critical change 缺少 source mapping
- 实现需要替换 LangChain/LangGraph runtime seam
- worktree 有冲突的用户改动
- 下一步需要新产品决策

---

## Subagent Rule

只有用户明确授权 subagent / delegation / parallel work 时使用。

- 任务必须 bounded
- 文件 ownership 不重叠
- 不把 final synthesis 交给 subagent
- critical path 不应交给非必要 subagent

---

## Current Repo Default

当前 `coding-deepgent` 主线：

- Trellis tasks + PRDs 是 stage ledger
- 使用本 guide 作为 canonical staged-execution protocol
- checkpoint 逻辑写进 Trellis docs，不依赖外部 skill wrapper
