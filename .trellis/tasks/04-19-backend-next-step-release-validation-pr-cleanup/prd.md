# Backend Next Step Release Validation and PR Cleanup

## Goal

对当前 `coding-deepgent` 主线的 release 候选改动进行 focused validation 和必要的 PR cleanup，优先确认当前工作区中的 frontend gateway / CLI surface 相关改动是否满足质量门槛、文档是否一致、测试是否覆盖、是否存在应在合并前修正的问题。

## Requirements

- 只面向当前 `coding-deepgent/` 主线和 `.trellis/` 规范层工作。
- 不默认开启新的 backend feature family。
- 不重开 `L5-a`，除非验证中发现真实的并发/分区缺陷。
- 对当前未提交改动执行 focused review、测试、lint、typecheck 和必要清理。
- 若发现问题，优先做小范围修正与补测；不引入与当前 release 无关的重构。
- 明确记录 residual risk 和未验证项。

## Acceptance Targets

- 当前 release 候选改动的行为边界被验证，尤其是 CLI/frontend gateway 入口与测试覆盖。
- README / CLI help / 实际命令面一致，不存在误导性文档。
- 相关 focused checks 运行完成，失败项被修复或明确记录。
- 最终结论明确：可继续进入 PR 收口，或应先修复具体问题。

## Planned Features

- 审查当前工作区改动与推荐主线方向是否一致。
- 补全与当前改动直接相关的 Trellis task context。
- 运行 focused Python tests、frontend checks、静态检查和必要的 smoke validation。
- 在需要时做最小 PR cleanup，包括测试、文档或薄层 CLI wiring 修正。

## Planned Extensions

- 新的 runtime feature family。
- Web/HTML 正式产品化。
- 广泛的全量回归，除非 focused checks 暴露更大范围耦合风险。

## Technical Notes

- 当前主线推荐动作来自 `.trellis/project-handoff.md`：`release validation / PR cleanup for Approach A MVP`。
- 当前工作区已有未提交改动，验证时必须把这些改动视为候选范围，不回滚无关用户改动。
- 本任务是 `fullstack`：Python backend + `frontend/cli` + gateway transport seam。
