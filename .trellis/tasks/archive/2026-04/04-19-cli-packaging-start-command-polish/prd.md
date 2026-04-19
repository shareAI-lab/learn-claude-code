# CLI packaging start command polish

## Goal

让已经具备 streaming + HITL 的 React/Ink CLI 能通过一个明确、可测试、可文档化的产品命令启动，而不是要求用户记住 Node package 目录、`PYTHONPATH` 或开发脚本细节。

## Acceptance Targets

* 有一个产品级启动命令可以直接启动 CLI 前端。
* 命令支持 fake/demo 模式，便于无模型 key 快速验证。
* Python CLI 启动逻辑对缺失 frontend package / npm install 给出清晰错误。
* 测试覆盖新命令参数和启动脚本选择。
* 不引入 Web/HTML 实现，不改变 runtime event protocol。

## Planned Features

* 增加独立 console script 或更清晰的 Python CLI 子命令别名。
* 保留现有 `coding-deepgent ui` 入口。
* 补充 README/usage 中的启动命令说明。
* 补 CLI tests，证明 fake/real 启动参数和 cwd/env 行为稳定。

## Planned Extensions

* 打成真正 npm/pip 组合发布包。
* 预检并自动提示 `npm install` / `npm ci`。
* Web/SSE gateway product packaging。

## Requirements

* 范围只覆盖 `coding-deepgent/` 产品主线。
* 不让 TS frontend 直接承担 Python runtime 配置。
* 不把 root `web/` 或 tutorial assets 引入产品启动路径。
* 不改变 JSONL bridge protocol。

## Acceptance Criteria

* [x] 产品级 CLI 启动命令存在并可测试。
* [x] fake mode smoke 能通过新命令或等价路径验证。
* [x] `coding-deepgent ui` 旧入口继续工作。
* [x] focused Python CLI tests、TS tests/typecheck 通过。

## Technical Notes

Likely files:

* `coding-deepgent/pyproject.toml`
* `coding-deepgent/src/coding_deepgent/cli.py`
* `coding-deepgent/frontend/cli/package.json`
* `coding-deepgent/tests/cli/test_cli.py`
* `coding-deepgent/README.md`

## Resolution (2026-04-19)

Implemented a repo-local product shortcut:

* Added Python console script `coding-deepgent-ui = coding_deepgent.cli:ui_cli`.
* `coding-deepgent-ui --fake` now routes to the same React/Ink CLI path as
  `coding-deepgent ui --fake`.
* Preserved `coding-deepgent ui` as the canonical grouped Typer command.
* Added clearer startup errors for missing frontend package metadata, missing
  `node_modules`, and missing `npm`.
* Updated README usage to make `coding-deepgent-ui` the quick product command
  while keeping npm dev scripts documented for development.

## Verification (2026-04-19)

* `pytest -q tests/cli/test_cli.py` -> `32 passed`
* `ruff check src/coding_deepgent/cli.py tests/cli/test_cli.py` -> passed
* `mypy src/coding_deepgent/cli.py` -> passed
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed
* `npm --prefix coding-deepgent/frontend/cli test` -> `8 passed`
* `PYTHONPATH=src python3 - <<'PY' ... ui_cli(['--help']) ... PY` -> printed the `coding-deepgent ui` help
