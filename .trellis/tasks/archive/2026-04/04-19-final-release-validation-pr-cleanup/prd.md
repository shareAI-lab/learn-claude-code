# Final release validation and PR cleanup

## Goal

对当前 `codex/stage-12-14-context-compact-foundation` 分支做一次最终发布前验证和 PR 状态清理，确认最近完成的 CLI frontend、HITL、task closeout 和 journal 记录没有留下明显本地问题。

## Acceptance Targets

* 工作区保持 clean。
* 当前分支对应 PR 状态已查看。
* 关键 Python / TypeScript checks 通过。
* 若发现失败，定位并修复；若是外部/CI-only blocker，记录清楚。
* 不引入新功能。

## Planned Features

* Run focused and broader validation commands for touched product areas.
* Inspect current PR metadata/check status.
* Summarize release readiness and remaining risks.

## Acceptance Criteria

* [x] `git status` clean except this validation task before archive.
* [x] Trellis active task list is controlled.
* [x] Focused and broad local validation passes.
* [x] Current PR metadata/checks inspected.
* [x] README-only merge conflict was identified and intentionally not resolved per user direction.
* [x] Task archived and session status reported.

## Technical Notes

Likely commands:

* `pytest` for CLI/frontend/tool-system/structure tests
* `ruff check`
* `mypy`
* `npm --prefix coding-deepgent/frontend/cli run typecheck`
* `npm --prefix coding-deepgent/frontend/cli test`
* `gh pr view 220 ...`
* `gh pr checks 220 ...`

## Validation Result (2026-04-19)

Local checks passed:

* `pytest -q` from `coding-deepgent/` -> `406 passed`
* `ruff check src tests` from `coding-deepgent/` -> passed
* `mypy src/coding_deepgent` from `coding-deepgent/` -> passed (`143 source files`)
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed
* `npm --prefix coding-deepgent/frontend/cli test` -> `8 passed`

PR state inspected:

* PR `#220` is `OPEN` and `draft=true`
* `mergeable=CONFLICTING`
* Checks show two Vercel failures, both `Authorization required to deploy`
* local branch is ahead of `origin/codex/stage-12-14-context-compact-foundation`

Conflict note:

* A dry merge / attempted merge from `upstream/main` showed conflicts only in
  root tutorial README files: `README.md`, `README-zh.md`, `README-ja.md`.
* Product code under `coding-deepgent/` did not conflict.
* User instructed not to handle README; merge was aborted and README conflicts
  were left unresolved for PR cleanup outside this task.
