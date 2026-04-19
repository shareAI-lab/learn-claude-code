# R1: Runtime Role And Agent Factory Seam

## Goal

建立明确的 runtime role 与 agent factory seam，让 main/subagent/fork 的 agent construction 走统一、可测试、LangChain-native 的构造路径，为后续 H13 coordinator/worker role projection 做准备。

## Requirements

* 定义 runtime roles：`main`、`subagent`、`fork`，并为 future `coordinator`、`worker` 保留 contract 位置但不实现行为。
* 将 child/fork agent construction 从 `subagents/tools.py` 的裸 `create_agent(...)` 调用迁移到新的 runtime factory seam。
* 不保留旧 `subagents.tools.create_agent` monkeypatch/调用兼容桥接。
* 迁移相关测试到新的 factory seam。
* 保持现有 `run_subagent`、`run_fork`、`resume_subagent`、`resume_fork` public tool schema 和行为不变。

## Acceptance Targets

* [ ] main/subagent/fork agent construction 都能通过明确 factory seam 表达。
* [ ] child/fork 不再依赖 `subagents.tools.create_agent` 作为主要构造入口。
* [ ] 现有 H11/H12 行为保持不变。
* [ ] 测试不再 monkeypatch `subagents.tools.create_agent`。
* [ ] 无 mailbox/coordinator/team runtime 行为被实现。

## Planned Features

* 新增或重整 `runtime/agent_factory.py` / `runtime/roles.py` 等低层 seam。
* 为 subagent/fork 调用点接入该 seam。
* 更新 focused tests。

## Detailed Implementation Plan

### Target Design

Introduce explicit runtime construction primitives without replacing LangChain:

* `coding_deepgent.runtime.roles`
  * Define a small role contract for agent construction.
  * Required current roles: `main`, `subagent`, `fork`.
  * Reserved future roles: `coordinator`, `worker`.
  * The future roles are contract placeholders only; they must not enable H13/H14 behavior in R1.
* `coding_deepgent.runtime.agent_factory`
  * Own the single project-local path for `create_agent(...)` construction.
  * Accept a typed build request/spec containing role, name, model, tools, system prompt, middleware, context schema, state schema if needed, checkpointer, and store.
  * Delegate to official LangChain `create_agent`; do not introduce a custom query loop.
* `coding_deepgent.agent_service`
  * Main agent construction should call the same factory seam with role `main`.
* `coding_deepgent.subagents`
  * Child subagent construction should call the same factory seam with role `subagent`.
  * Fork construction should call the same factory seam with role `fork`.

### Required Code Changes

* Add runtime role/factory modules under `coding-deepgent/src/coding_deepgent/runtime/`.
* Update `runtime/__init__.py` exports only if it improves product API clarity.
* Update `agent_service.create_compiled_agent(...)` to delegate construction to the new factory.
* Update `_execute_child_subagent(...)`, `_execute_fork_subagent(...)`, `resume_subagent_task(...)`, and `resume_fork_task(...)` construction paths to use the new factory seam.
* Remove direct `subagents.tools.create_agent` dependency as a test seam.
* Update tests to monkeypatch/inject the new runtime factory seam directly.

### Test Migration Rules

* Do not keep `subagents.tools.create_agent` as a compatibility monkeypatch target.
* Tests that currently monkeypatch `subagent_tools.create_agent` must move to the new factory seam.
* Prefer tests that assert the build request role/name/tools/middleware/context rather than relying only on fake agent return text.
* Keep behavior tests for returned envelopes, thread ids, sidechain records, and resume unchanged.

### Focused Verification

* `pytest -q coding-deepgent/tests/subagents/test_subagents.py`
* `pytest -q coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/runtime/test_app.py`
* `ruff check <touched files>`
* `mypy <touched typed runtime/subagent/test files>` where practical.

### Checkpoint Requirements

At R1 checkpoint, record:

* Whether all direct subagent/fork `create_agent(...)` calls now go through the runtime factory.
* Whether tests no longer monkeypatch `subagents.tools.create_agent`.
* Whether any bridge/fallback was introduced. Expected answer: no.
* Whether R2 can safely split `subagents/tools.py` without changing the construction seam again.

## Planned Extensions

* R2 拆分 subagent domain responsibility。
* R3 background run service hardening。
* H13 coordinator/worker tool projection。

## Definition of Done

* Focused subagent/fork tests pass.
* Relevant ruff/mypy checks pass for touched files.
* PRD checkpoint records changed seams and residual risks.

## Out of Scope

* 不拆分整个 `subagents/tools.py` 文件结构。
* 不实现 mailbox、Scratchpad、Coordinator、Worker team runtime。
* 不新增旧 factory bridge/fallback。
* 不 change public tool schemas for `run_subagent`, `run_fork`, `resume_subagent`, or `resume_fork`.
* 不 introduce a separate non-LangChain runtime executor.

## Technical Notes

* Parent: `.trellis/tasks/04-19-runtime-architecture-refactor-plan/prd.md`
* Key files likely touched:
  * `coding-deepgent/src/coding_deepgent/runtime/`
  * `coding-deepgent/src/coding_deepgent/agent_service.py`
  * `coding-deepgent/src/coding_deepgent/subagents/tools.py`
  * `coding-deepgent/src/coding_deepgent/runtime/__init__.py`
  * `coding-deepgent/tests/subagents/test_subagents.py`
  * `coding-deepgent/tests/runtime/test_app.py`
  * `coding-deepgent/tests/runtime/test_agent_runtime_service.py`

## Checkpoint: R1

State:
* verifying

Verdict:
* APPROVE

Implemented:
* Added explicit runtime role contract and runtime agent factory seam.
* Main agent construction now delegates through the runtime factory seam.
* Subagent and fork construction now delegate through the runtime factory seam.
* Tests now patch `coding_deepgent.runtime.agent_factory.create_runtime_agent` instead of `subagents.tools.create_agent`.

Verification:
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/runtime/test_agent_runtime_service.py coding-deepgent/tests/runtime/test_app.py`
* Result: `62 passed`

Architecture:
* primitive used: official LangChain `create_agent` behind a project-local factory seam.
* why no heavier abstraction: R1 only normalizes construction ownership; it does not add a custom executor or graph runtime.

Boundary findings:
* No mailbox/coordinator/team runtime behavior was introduced.
* No compatibility bridge for `subagents.tools.create_agent` was retained.

Decision:
* continue

Reason:
* R1 acceptance targets are satisfied and R2 can now split `subagents/tools.py` without changing the construction seam again.
