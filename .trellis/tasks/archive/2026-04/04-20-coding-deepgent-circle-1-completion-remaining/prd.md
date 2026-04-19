# Circle 1 Completion Remaining UX And Extensions

## Goal

一次性完成 Circle 1 剩余工作：补齐 `Wave 2C/2D` 的 resume/history/projection/permission/recovery 可追溯面，补齐 `Wave 3` 的本地 extension inspect/validate/debug 面，并增加 Circle 1 acceptance harness。

## Scope

- Circle: `Circle 1`
- Waves:
  - `Wave 2C`: resume/history/projection UX
  - `Wave 2D`: permission/recovery/runtime-event history
  - `Wave 3`: usable local extension seams
  - `Final`: Circle 1 acceptance harness

## Non-Goals

- mailbox / `SendMessage`
- coordinator / team-runtime
- remote / IDE control plane
- daemon / cron / proactive automation
- marketplace install/enable lifecycle

## Acceptance Criteria

- [x] CLI exposes session history/projection/timeline/evidence/events/permissions without requiring raw JSONL reads.
- [x] CLI exposes local skills/MCP/hooks/plugins inspect/validate/debug surfaces.
- [x] Circle 1 acceptance harness covers workflow A/B/C with deterministic local checks.
- [x] Trellis roadmap/handoff/specs are updated.
- [x] Full Python and TS validation passes.
- [ ] Task is archived and session recorded.
