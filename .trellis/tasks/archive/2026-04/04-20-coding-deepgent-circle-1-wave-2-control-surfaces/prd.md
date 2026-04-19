# Circle 1 Wave 2 Control Surfaces

## Goal

把 `Circle 1 / Wave 2` 从“可见”推进到“可控”：为现有 durable `tasks/plans` 与 background `subagents` 提供正式 CLI 控制入口，不重做 runtime，不新增 team-runtime/mailbox/daemon。

## Circle / Wave

- Circle: `Circle 1`
- Wave: `Wave 2`
- Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`

## Acceptance Workflows

- Workflow A: Repository Takeover And Sustained Coding
- Workflow C: Complex Task Decomposition

## Expected Effect

用户不再只能“看见 task/subagent snapshot”，而是可以直接用 product CLI：

- 创建、列出、读取、更新 durable tasks
- 保存、列出、读取 durable plans
- 启动、列出、读取、续发输入、停止 background subagent runs

如果这些能力仍只存在于模型工具面而没有正式用户控制入口，这包不算完成。

## Planned Features

- Add `coding-deepgent tasks ...` CLI group.
- Add `coding-deepgent plans ...` CLI group.
- Add active-frontend-process background subagent control through typed bridge inputs and TUI slash commands.
- Add store-level `list_plans()` support so plans can be listed deterministically.
- Add CLI renderers for task, plan, and subagent list surfaces.
- Keep implementation on top of existing `tasks.store` and `subagents.background` seams.
- Add a local file-backed runtime store backend so durable task/plan state survives process boundaries.

## Non-Goals

- No mailbox / `SendMessage`.
- No coordinator or multi-agent team runtime.
- No daemon/cron.
- No remote/IDE control plane.
- No standalone cross-process subagent control commands that pretend to manage process-local worker handles.
- No fork-start CLI surface that depends on live parent runtime state.
- No TUI command-mode redesign in this pack.

## Target Claude Code Behavior

- Claude Code exposes task/session state changes and task lifecycle through user-facing stream/control surfaces rather than only internal stores.
- `cc-haha` stream/control layer includes `task_started`, `task_progress`, `task_notification`, `session_state_changed`, and explicit `stop_task` control messages.

## Source Evidence

- `/root/claude-code-haha/src/cli/print.ts`
  - treats `task_started`, `task_progress`, `task_notification`, and `session_state_changed` as first-class streamed system/control surfaces
  - handles `stop_task` control request path
- `/root/claude-code-haha/src/entrypoints/sdk/controlSchemas.ts`
  - contains explicit `stop_task` control schema
- `/root/claude-code-haha/src/utils/sdkEventQueue.ts`
  - models task lifecycle events as SDK/runtime-facing control data, not hidden implementation details

## Alignment Matrix

| Area | Source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Task lifecycle control | task lifecycle is externally surfaced | user can inspect/update durable tasks directly | CLI `tasks` commands | align | expose local durable task store |
| Task stop/control | explicit control requests exist | user can stop or steer background work | CLI `subagents stop/send-input` | partial | apply to local background subagents only |
| Plan management | plans guide longer work | user can persist/read/list plans explicitly | CLI `plans` commands | align | add missing `list_plans()` seam |
| Rich team control | cc has broader control plane | team-runtime orchestration | mailbox/coordinator | defer | Circle 2 |
| Fork control | same-config sibling branch exists | branch control from CLI | live fork control | defer | requires active parent runtime state |

## Source Gap

- target behavior: exact Claude Code UI/control affordances for interactive task stopping and richer panel controls.
- Claude Code public evidence: task/session control is visibly surfaced.
- `cc-haha` evidence: control and SDK event shapes are visible, but local product does not have the same remote/session-ingress architecture.
- why insufficient: we can align effect and user affordance without copying transport/control topology.

## Analogous OSS Review

Not required for this pack. Existing `cc-haha` control/event evidence plus local runtime seams are enough to justify the local design.

## Local Decision

- Keep durable state ownership in `tasks.store` and `subagents.background`.
- Add user entrypoints in `coding_deepgent.cli` and CLI-facing coordination in `coding_deepgent.cli_service`.
- Add deterministic list rendering via `renderers/text.py`.
- Reuse background subagent manager directly for list/status/send/stop/start.

## Acceptance Criteria

- [x] `coding-deepgent tasks list|get|create|update` works against the durable task store.
- [x] `coding-deepgent plans list|get|save` works against the durable plan store.
- [x] active frontend/bridge process can `run_background_subagent`, `subagent_send_input`, `subagent_stop`, and `refresh_snapshots`.
- [x] `list_plans()` exists and is deterministic.
- [x] CLI errors stay at the `ClickException` boundary for invalid inputs.
- [x] Focused tests cover CLI commands, added store behavior, and frontend bridge control inputs.
- [x] Trellis specs and handoff are updated.
