# h12 completion pack implementation plan

## Goal

把 H12 从当前 `implemented-minimal` 推进到一个更完整、可长期维持的本地完成形态，并保持单一显式 `run_fork` 入口，不为旧方案/旧数据保留兼容层。

## Requirements

* 继续只保留显式 `run_fork` 入口，不新增隐式 fork 入口。
* 本包必须一起覆盖：
  * background fork workers
  * cache-safe summary / fork reuse
  * abort / cleanup / kill semantics
  * resume / path / worktree hardening
* 可以直接替换旧局部设计，不要求桥接旧方案或旧数据。
* 不把 mailbox / coordinator / team semantics 混入本包。
* 本次按**单批收尾**执行：
  * 不允许先把 H12 宣称 close，再把剩余 cache-safe summary/reuse 留到下一轮
  * 不允许把 stop/cleanup/resume hardening 拆成“后续小修”
* H12 只有在下述 gate 同时满足时才能视为完成：
  * explicit `run_fork` 前台/后台 contract 一致
  * background fork lifecycle 完整
  * cache-safe summary / fork reuse 落地
  * stop / cleanup / kill semantics 落地
  * resume / path / worktree hardening 落地
  * spec / tests / roadmap 状态同步

## What Is Already In Place

* explicit `run_fork` 仍是唯一 fork 入口
* `run_fork(background=true)` 已经接入背景运行面
* 后台 fork / 子 agent 已有统一状态查询与追加输入
* `subagent_stop(...)` 已有 stop-request + terminal `cancelled` contract
* fork / subagent resume 已有 thread continuity
* workdir mismatch 已有显式错误

## What Still Must Be Closed In This Batch

* H12 parent / child task 状态与 dashboard/roadmap 刷新

## Acceptance Criteria

* [x] 父任务存在并挂到 `04-19-next-subagent-planning/` 下。
* [x] H12 completion pack 已拆成 4 个子任务。
* [x] 执行顺序明确。
* [x] 入口形态明确：explicit `run_fork` only。
* [x] 单次实现批次完成后，H12 不再留下“下一轮补 fork summary/reuse”的尾巴。
* [x] 前台 fork 与后台 fork 共享同一条显式 fork surface，而不是形成两套 fork product shape。
* [x] H12 closeout 验证 bundle 一次通过。

## Technical Approach

采用**单一 integrated closeout**，不是松散 backlog：

1. 以当前 explicit `run_fork` surface 为唯一入口，不再增加新 fork 入口形态
2. 在同一轮实现里完成：
   * background fork runtime
   * cache-safe summary / fork reuse
   * abort / cleanup / kill semantics
   * resume / path / worktree hardening
3. 最后统一过：
   * focused test bundle
   * `ruff`
   * `mypy`
   * H12 spec 刷新
   * roadmap / task status 收口

## Implementation Plan (single batch)

* Batch step 1: finalize background fork runtime on the existing background-run manager
* Batch step 2: add cache-safe summary / fork reuse on the same fork continuity seam
* Batch step 3: harden stop / cleanup / kill semantics and terminal-state behavior
* Batch step 4: harden resume / path / worktree checks
* Batch step 5: run one closeout validation bundle and only then mark H12 done

## Out of Scope

* implicit fork entry
* mailbox / SendMessage
* coordinator runtime
* compatibility shims for old fork/local data shapes

## Decision (ADR-lite)

**Context**: batch1/batch2 已经把 H11 与 H12 minimal slice 做到可继续深化的阶段。用户要求这次直接把 H12 收得更完整，并且不为旧方案或旧数据保留兼容层。

**Decision**: 下一阶段采用 `H12 completion pack`，继续只保留显式 `run_fork` 入口，不新增隐式 fork 入口。

**Consequences**:

* H12 会优先朝单一 fork surface 深化，而不是双入口并存。
* 允许直接替换当前局部实现，只保留长远边界更清晰的方案。
* H13/H14 继续 deferred，不与本包并行打开。
* H12 不按“先 close 80%，再下一轮补最后 20%”的方式收尾；而是一次性完成剩余完成项后再 close。

## Verification

* `pytest -q coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_plugins.py coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check`
* `mypy`
