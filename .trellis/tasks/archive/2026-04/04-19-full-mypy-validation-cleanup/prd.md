# Full mypy validation cleanup

## Goal

修复当前 `coding-deepgent` 主线下 `mypy coding-deepgent/src/coding_deepgent coding-deepgent/tests` 的现有类型检查失败，使 PR 说明里的已知验证缺口收口为通过状态。

## Requirements

- 只处理当前主线 `coding-deepgent/` 的类型检查失败。
- 优先修复测试中的类型问题，不借机引入运行时行为改动。
- 保持已有测试语义与覆盖目标不变。
- 不通过关闭整批检查、缩小 mypy 范围、或粗暴全局忽略来掩盖问题。
- 若必须使用 `cast` 或窄范围 `type: ignore`，应限定在最小必要位置。

## Acceptance Targets

- `mypy coding-deepgent/src/coding_deepgent coding-deepgent/tests` 通过。
- 受影响的 focused pytest 仍然通过。
- 相关 Python 文件的 `ruff check` 通过。
- PR 可移除当前 “Known Validation Gap” 中关于全量 mypy 的说明。

## Planned Features

- 逐个修复 `tests/compact/test_runtime_pressure.py`、`tests/memory/test_memory_module_closeout.py`、`tests/frontend/test_frontend_bridge.py` 中的类型问题。
- 为测试 fake / stub 补充显式类型、最小 helper 类或局部 `cast`。
- 在必要时微调测试辅助对象的构造方式，使其满足被测接口的静态类型契约。

## Planned Extensions

- 不相关的运行时/产品行为重构。
- 新 feature family。
- 广泛的测试重写。

## Technical Notes

- 当前问题来自 PR #220 中记录的已知验证缺口。
- 任务是 `fullstack`，但预期主要修改 Python 测试文件。

## Implementation Checkpoint

State:

- terminal

Verdict:

- APPROVE

Implemented:

- 将 `tests/compact/test_runtime_pressure.py` 中的测试 summarizer / request / runtime helper 收敛为静态类型可接受的形式。
- 用类型正确的 `ModelResponse`、`Runtime(...)`、局部 `cast` 和更窄的 metadata 断言替换测试里的宽松 `SimpleNamespace` 假对象。
- 修复 `tests/memory/test_memory_module_closeout.py` 中 `ToolGuardMiddleware` request fake 的静态类型问题。
- 修复 `tests/frontend/test_frontend_bridge.py` 中未注解事件列表的 mypy 报错。
- 收口 PR #220 中 “Known Validation Gap” 里记录的全量 mypy 缺口。

Verification:

- `mypy coding-deepgent/src/coding_deepgent coding-deepgent/tests` -> passed
- `ruff check coding-deepgent/src coding-deepgent/tests` -> passed
- `pytest -q coding-deepgent/tests` -> `399 passed`
- `pytest -q coding-deepgent/tests/compact/test_runtime_pressure.py coding-deepgent/tests/memory/test_memory_module_closeout.py coding-deepgent/tests/frontend/test_frontend_bridge.py` -> `53 passed`

Residual Risk:

- 本次改动只修复静态类型与测试 fake，不改变产品 runtime 行为。
- 工作树里存在与本任务无关的 `.trellis/scripts/common/git_context.py` 和 `.trellis/tests/` 变动；未纳入本任务提交。
