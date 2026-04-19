# Circle 1 Wave 2 Runtime-Exposing CLI/TUI Surfaces

## Goal

推进 `Circle 1 / Wave 2` 的首个整包：把 Wave 1 已完成的 runtime/session/compact/task/subagent 能力暴露到 CLI/TUI 可见层，避免“后台有语义，用户看不见、恢复时不可判断”的差距。

## Circle / Wave

- Circle: `Circle 1`
- Wave: `Wave 2: Runtime-Exposing CLI/TUI Surfaces`
- Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`

## Acceptance Workflows

- Workflow A: Repository Takeover And Sustained Coding
- Workflow B: Long Session Continuity
- Workflow C: Complex Task Decomposition

## Expected Effect

本轮对齐的核心效果不是复制 Claude Code UI 外观，而是让用户在本地 CLI/TUI 中看见和判断：

- 当前 resume/model-visible context 采用 raw / compact / collapse 哪一种 projection。
- 哪些 transcript message 被 compact/collapse 隐藏，哪些仍进入模型上下文。
- session memory 是 current 还是 stale。
- 当前 todo/task/subagent/runtime 事件是否已经进入用户可见层。
- permission / failed tool / recovery 状态是否可被及时定位。

如果这些信息仍只能靠读 JSONL 或内部测试判断，本轮不算完成。

## Planned Features

- Add a CLI session inspection command that renders session metadata, recovery brief, selected projection mode, compact/collapse timeline, raw transcript visibility, model projection rows, and session-memory status.
- Add a renderer-neutral frontend `context_snapshot` event carrying selected context/projection metrics after each completed run.
- Add a renderer-neutral frontend `subagent_snapshot` event carrying recent subagent sidechain/activity summary when available.
- Extend the React/Ink CLI reducer and panels to render context snapshot, task snapshot, and subagent snapshot.
- Update protocol docs/specs and tests for Python protocol, frontend bridge, reducer, CLI renderers, and session inspection.

## Non-Goals

- Full Claude Code visual clone.
- Remote control, IDE, daemon, mailbox, coordinator, or team-runtime surfaces.
- Plugin marketplace/install lifecycle.
- Reopening Wave 1 runtime semantics unless a regression is found.

## Target Claude Code Behavior

- Claude Code exposes session identity, resume behavior, permission waits, tool progress, task/background notifications, and context/compaction effects through user-facing CLI/stream surfaces rather than making them only internal records.
- Claude Code resume/internal-event paths are stateful and compaction-aware; users should not need to reason from raw transcript storage alone.

## Source Evidence

- `/root/claude-code-haha/src/cli/print.ts`
  - validates resume/rewind inputs before running
  - switches behavior around resume/session inputs
  - forwards incremental messages during turns so progress remains externally visible
  - reports session state changes, task notifications, permission waits, and post-turn summaries as system/stream events
- `/root/claude-code-haha/src/cli/transports/ccrClient.ts`
  - reads foreground internal events from the last compaction boundary for session resume
  - reads subagent internal events separately for resume continuity
- `/root/claude-code-haha/src/services/compact/grouping.ts`
  - treats API-round boundaries as safe compaction grouping points

## Alignment Matrix

| Area | Source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Session inspect | Resume/session paths are explicit and validated | user can inspect resume state before continuing | `sessions inspect` over loaded JSONL session | align | expose current local session model-view and timeline |
| Compaction visibility | internal events resume from compaction boundary | user can see selected compact/collapse projection | compression view renderer | align | use existing `build_compression_view` as source of truth |
| Task/runtime events | stream surfaces filter but preserve task/session state changes | TUI shows runtime facts without parsing logs | typed frontend events and reducer panels | partial | expose local snapshots; broader CC event taxonomy deferred |
| Subagent continuity | subagent internal events have separate resume path | user can see recent subagent activity | subagent snapshot event/panel | partial | summarize existing sidechain/evidence; no team runtime |
| UI appearance | Claude Code has richer Ink UI | better daily-driver visibility | simple panels over typed state | defer | do not copy visual details in this wave |

## Source Gap

- target behavior: exact Claude Code private UI layout and hidden collapse UI affordances.
- Claude Code public evidence: visible CLI/stream behavior and resume-oriented commands exist, but private UI implementation details are not fully public.
- `cc-haha` evidence: enough evidence exists for session/resume/events/compaction boundaries; not enough to justify pixel/UI cloning.
- why insufficient: Circle 1 benefit is runtime visibility, not visual cloning.

## Analogous OSS Review

Not needed for this pack. The required local behavior can be justified from real public CLI behavior, `cc-haha` session/stream/compact references, and existing `coding-deepgent` runtime contracts.

## Local Decision

- Keep domain facts in Python `sessions` / `frontend` protocol code.
- Keep CLI rendering in `renderers/text.py` and Typer commands.
- Keep TUI display state in TS reducer and components only.
- Use existing `build_compression_view` rather than inventing a second projection model.
- Add bounded snapshot payloads, not raw transcript dumps, to the live TUI.

## Acceptance Criteria

- [x] `coding-deepgent sessions inspect <session_id>` renders summary, recovery brief, projection mode, model projection, raw visibility, timeline, and session memory status.
- [x] The frontend bridge emits `context_snapshot` and `subagent_snapshot` after completed runs.
- [x] The React/Ink CLI renders context, task, and subagent snapshots.
- [x] Protocol validation rejects malformed new payloads.
- [x] Tests cover CLI command behavior, Python protocol/event mapping, bridge emission order, TS reducer behavior, and TS protocol parsing.
- [x] Relevant Trellis specs are updated for the new runtime-exposing surfaces.
