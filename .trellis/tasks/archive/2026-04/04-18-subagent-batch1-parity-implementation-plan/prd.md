# subagent batch1 parity implementation plan

## Goal

把“第一批最值得先做的子 agent / fork 能力”拆成可执行 Trellis 任务，并明确实现顺序、依赖关系、和本批次边界。

## Requirements

* 本批次只覆盖第一批功能点：
  * `max_turns` 真正生效
  * per-agent model routing
  * 更多 built-in subagent
  * local custom subagent definitions
  * 更完整的 fork continuity
  * subagent / fork resume foundation
* 先补已经声明过但未兑现的 contract，再扩展新 surface。
* 保持当前 H11/H12 主线边界，不在本批次内重开：
  * mailbox / SendMessage
  * coordinator runtime
  * background multi-agent orchestration
  * plugin-provided agents
  * write-capable coder agents
* 复用现有 `subagents`, `runtime`, `sessions`, `tasks` seam，不增加桥接层。

## Acceptance Criteria

* [x] 父任务存在并挂到 `04-18-compare-subagent-vs-cc-gap/` 下。
* [x] 第一批实现被拆成 5 个有 PRD 的子任务。
* [x] 每个子任务都写明目标、范围、验收标准、依赖。
* [x] 执行顺序明确，且第一执行入口清晰。

## Task Breakdown

### L1-a: H11 subagent max_turns and model routing

先补 contract debt，让已声明能力真正生效。

### L1-b: H11 built-in subagent catalog expansion

在稳定的 turn/model contract 上扩 built-in catalog。

### L2-a: H11 local custom subagent definitions

在 built-in catalog 之上开放 repo-local custom agents。

### L2-b: H12 fork continuity contract closeout

把当前 fork 从 minimal lineage metadata 推进到更完整的 continuity contract。

### L2-c: H11/H12 subagent and fork resume foundation

在 custom agent + fork continuity 基础上补 resume。

## Execution Order

1. `L1-a` first
2. `L1-b` after `L1-a`
3. `L2-a` after `L1-b`
4. `L2-b` after `L1-a`
5. `L2-c` after `L2-a` and `L2-b`

## Out of Scope

* Plugin-provided agents
* Background/async child lifecycle
* Progress UI / notifications
* Mailbox / coordinator / team runtime

## Context Sources

* `.trellis/tasks/04-18-compare-subagent-vs-cc-gap/prd.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
* `.trellis/spec/backend/task-workflow-contracts.md`
