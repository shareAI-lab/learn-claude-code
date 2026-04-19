# R2: Split Subagent Domain Responsibilities

## Goal

拆分 `subagents` domain 的职责边界，避免 `subagents/tools.py` 同时承担 definition/catalog、execution、fork payload、resume/sidechain、tool wrappers 和 background lifecycle，为后续 H13/H14 提供可组合的稳定内部 API。

## Dependencies

* Depends on R1 runtime role and agent factory seam.

## Requirements

* 将 `subagents/tools.py` 按真实职责拆分为更小模块。
* 保持 public tool names、tool schemas、`subagents/__init__.py` exports 稳定。
* 不引入 compatibility bridge 保护旧内部模块布局。
* 不改变 H11/H12 user-visible behavior。

## Acceptance Targets

* [ ] `subagents/tools.py` 不再是所有 subagent/fork/resume/sidechain 逻辑的集中承载文件。
* [ ] Public tools: `run_subagent`、`run_fork`、`resume_subagent`、`resume_fork`、background controls 保持 schema 不变。
* [ ] Internal modules 有清晰 ownership：definitions、execution、forking、resume、sidechain、tool wrappers。
* [ ] Existing focused subagent/fork/background tests pass.

## Planned Features

* 拆分职责模块，例如：
  * `definitions.py`
  * `execution.py`
  * `forking.py`
  * `resume.py`
  * `sidechain.py`
  * `tool_wrappers.py`
* 更新 imports 和 tests。

## Detailed Implementation Plan

### Target Module Ownership

Use concrete module ownership to prevent `subagents/tools.py` from becoming the coordination dumping ground again:

* `subagents/definitions.py`
  * Built-in definitions, local/plugin definition resolution, validation, child tool allowlists.
* `subagents/execution.py`
  * Synchronous child execution and result metrics for standard subagents.
* `subagents/forking.py`
  * Fork-specific payload construction, prompt/tool fingerprinting, placeholder layout, recursion guard, fork execution.
* `subagents/sidechain.py`
  * Parent ledger sidechain persistence, sidechain metadata merge, message reconstruction helpers.
* `subagents/resume.py`
  * Resume task flows for subagents and forks, including workdir/prompt/tool fingerprint checks.
* `subagents/tool_wrappers.py`
  * LangChain `@tool` wrappers and public JSON envelope shaping.
* `subagents/background.py`
  * Keep background service here until R3; do not fold it into `tool_wrappers.py`.

Exact filenames may adjust during implementation, but each final module must have one strong responsibility.

### Required Code Changes

* Move internal helpers out of `subagents/tools.py` by responsibility.
* Keep `subagents/__init__.py` as the stable public export layer.
* Keep public tool names and Pydantic schemas stable.
* Keep behavior for built-in definitions, local repo definitions, plugin definitions, verifier plan requirement, sidechain recording, fork recursion guard, and resume hardening.
* Update imports in tests to use public exports or new internal modules only when the test is specifically about that internal module.

### Anti-Regression Rules

* Do not create compatibility alias modules that exist only to preserve old internal imports.
* Do not move background execution into the same module as public tool wrappers.
* Do not hide sidechain persistence in sessions or runtime packages; it remains subagent-owned but writes through the session store seam.
* Do not change public JSON envelope field names.

### Focused Verification

* `pytest -q coding-deepgent/tests/subagents/test_subagents.py`
* `pytest -q coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Import smoke checks through `coding_deepgent.subagents`.
* `ruff check <touched subagent/test files>`
* `mypy <touched subagent/test files>` where practical.

### Checkpoint Requirements

At R2 checkpoint, record:

* Final subagent module map and ownership.
* Public exports that remained stable.
* Tests proving schemas/envelopes did not change.
* Any behavior that became clearer or any residual large module that should be split later.

## Planned Extensions

* Future `teams/` or `orchestration/` package should depend on stable internal APIs, not `subagents/tools.py` internals.

## Definition of Done

* Focused subagent tests pass.
* Ruff/mypy pass for touched files.
* Checkpoint documents module ownership.

## Out of Scope

* 不改变 runtime role/factory contract unless R1 left a concrete gap.
* 不实现 H13/H14.
* 不 add compatibility alias modules solely for old internal imports.
* 不 rewrite background run semantics; R3 owns that.
* 不 introduce team/coordinator package.

## Technical Notes

* Parent: `.trellis/tasks/04-19-runtime-architecture-refactor-plan/prd.md`
* Key files likely touched:
  * `coding-deepgent/src/coding_deepgent/subagents/`
  * `coding-deepgent/tests/subagents/test_subagents.py`

## Checkpoint: R2

State:
* verifying

Verdict:
* APPROVE

Implemented:
* Extracted subagent definition/catalog ownership to `subagents/definitions.py`.
* Extracted subagent/fork result dataclasses and `ChildAgentFactory` to `subagents/results.py`.
* Extracted fork-specific fingerprint, placeholder layout, payload, recursion guard, and prompt/tool projection helpers to `subagents/forking.py`.
* Updated `subagents/__init__.py` to keep public exports stable.

Verification:
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Result: `59 passed`

Architecture:
* primitive used: domain module split by ownership inside `subagents`.
* why no heavier abstraction: R2 moves stable responsibilities without changing public tool schemas or adding a new runtime layer.

Boundary findings:
* `subagents/tools.py` still owns execution, resume, sidechain, and public tool wrappers. It is smaller and no longer owns catalog/fork payload, but deeper sidechain/resume extraction remains a possible future cleanup.
* No compatibility alias modules were added for old internal imports.
* No H13/H14 behavior was introduced.

Decision:
* continue

Reason:
* The high-risk catalog/fork-payload ownership has been removed from `tools.py`, focused tests pass, and R3 can proceed against stable public/background APIs.
