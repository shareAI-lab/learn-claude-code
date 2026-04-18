# Backend Next-Step Roadmap After MVP Closeout

## Goal

在 `coding-deepgent/` 已完成 Approach A MVP 主干后，输出一个可执行的后端下一阶段 roadmap，明确先收口什么、再补哪些 cc 核心能力、哪些边界继续保持 deferred。

## Acceptance Targets

- 当前主线状态被压缩成一份清晰判断，而不是继续沿用旧阶段口径。
- roadmap 明确区分:
  - 必须先收口的 release/contract 漂移
  - 应优先补齐的后端能力
  - 已知但继续 deferred 的能力
- 每个 roadmap 阶段都写清楚:
  - concrete benefit
  - target modules
  - verification path
  - intentionally deferred extensions
- 规划结论保持与现有 Trellis canonical docs 一致，不误把 tutorial/reference 层当作主线。

## Planned Features

- 基于 `.trellis/project-handoff.md`、canonical roadmap、deferred ADR 和当前代码/测试状态，整理真实主线现状。
- 产出一个分阶段后端 roadmap，优先覆盖:
  - release cleanup / contract lock
  - `H01` 的 ToolSearch / deferred tool discovery
  - `H11/H12` 的 subagent / fork contract consolidation
- 明确哪些能力不应现在默认重开:
  - `H13/H14`
  - `H21/H22`
  - provider-specific observability / cache / billing

## Planned Extensions

- 若后续有新的 source-backed PRD，再讨论:
  - mailbox / `SendMessage`
  - coordinator synthesis runtime
  - remote / IDE control plane
  - daemon / cron / proactive automation
  - richer telemetry / TTFT / provider-specific cost-cache instrumentation

## Requirements

- 只服务当前 product mainline: `coding-deepgent/`
- 只讨论后端/runtime/product contract，不展开 tutorial parity
- 优先给出“为什么现在做”而不是“更像 cc”

## Technical Notes

- 当前真实回归点包括:
  - `test_app.py` 中主工具列表与实际 tool surface 漂移
  - `agent_loop_service.py` 中 memory queue 默认行为触发 Redis 依赖
  - `hooks/dispatcher.py` 的 runtime evidence metadata 与测试契约漂移
- 当前高价值代码入口包括:
  - `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
  - `coding-deepgent/src/coding_deepgent/subagents/tools.py`
  - `coding-deepgent/src/coding_deepgent/subagents/background.py`
  - `coding-deepgent/src/coding_deepgent/agent_loop_service.py`
  - `coding-deepgent/src/coding_deepgent/memory/queue.py`
  - `coding-deepgent/src/coding_deepgent/hooks/dispatcher.py`
