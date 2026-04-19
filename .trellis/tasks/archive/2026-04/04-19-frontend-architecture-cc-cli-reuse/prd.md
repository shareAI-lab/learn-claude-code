# brainstorm: frontend architecture and cc cli reuse

## Goal

为 `coding-deepgent/` 设计一个尽量简单、可渐进演进的前端策略：短期优先复用或对齐 Claude Code / cc 风格的 CLI 交互体验，长期保留支持 Web 端的架构空间，避免在当前阶段引入过重 UI 工程。

## What I already know

* 用户希望前端方案“简单一点”。
* 用户倾向于“大部分移植 cc 的 CLI 前端”。
* 用户希望未来支持 Web 端。
* 用户明确可以引入 TypeScript / React 等依赖。
* 用户的核心目标是开发便捷、快速完工，而不是严格保持 Python-only。
* 当前项目主线是 `coding-deepgent/`。
* `.trellis/spec/frontend/index.md` 明确当前 `web/` 与 tutorial UI 是参考层，不是默认产品实现目标。
* 这个议题属于架构/产品形态决策，不应直接开始编码。
* `coding-deepgent/` 已经有 Typer/Rich CLI：`coding_deepgent/cli.py`、`cli_service.py`、`renderers/text.py`、`todo/renderers.py`。
* `coding-deepgent/` 已经有 runtime event seam：`runtime/events.py` 提供 `RuntimeEvent`、`RuntimeEventSink`、`QueuedRuntimeEventSink`。
* `coding-deepgent/` 已经有 session/evidence/recovery brief：`sessions/*`、`cli_service.recovery_brief_text()`。
* `/root/claude-code-haha` 的 CLI 前端主要是 React/Ink REPL，不是 Python 可直接移植的代码层。
* LangChain/LangGraph 官方 streaming/HITL 能提供未来 Web/CLI 共享的事件基础：`stream_mode=["messages", "updates", "custom"]`、`version="v2"`、interrupt/HITL resume。

## Assumptions (temporary)

* “cc” 指 Claude Code 或项目中对齐 Claude Code 的 CLI/TUI 交互体验。
* 第一阶段目标应是完整交付 CLI 前端 v1，而不是只做半成品 MVP；浏览器 Web 不并入这个 CLI 完工目标。
* 未来 Web 端更适合复用核心事件/会话/任务状态，而不是复用终端渲染代码本身。
* 如果引入 TypeScript/React，最快路径更可能是 React/Ink CLI shell，而不是 Python Rich-only 或完整 browser-first Web。

## Open Questions

* CLI 完工目标是否包括 true streaming 和 true permission pause/resume，还是只要求完成可见 UI 与协议预留？

## Requirements (evolving)

* 设计应保持简单，避免一次性建设完整 Web 前端。
* CLI 体验应尽量对齐 cc 风格。
* 架构应为未来 Web 端保留稳定边界。
* 对齐 cc 时必须先对齐“交互效果”和“运行时 contract”，而不是复制 UI/TUI 文件结构。
* 前端边界应避免把 Typer/Rich、React/Ink 或 Web 框架泄漏进 domain services。
* 允许新增 TypeScript/React/Ink 前端包，前提是 Python `coding-deepgent` runtime 保持清晰后端边界。
* 优先选择能快速复用 cc UI 思路和组件形态的方案。
* 前端实现采用选择性移植：优先搬 cc 的组件结构、交互语义、布局模式和小型纯 UI helper；不整包搬运行时、AppState、Bun feature flags、analytics、bridge/daemon/team/IDE 等复杂系统。

## Acceptance Criteria (evolving)

* [x] 明确 CLI v1 完工范围。
* [x] 明确哪些 cc CLI 行为应复用/对齐，哪些不应照搬。
* [x] 明确 CLI 与未来 Web 端共享的核心边界。
* [x] 形成可拆分的小 PR 实施计划。
* [x] PRD 记录 source-backed cc alignment matrix。
* [x] PRD 明确 Acceptance Targets / Planned Features / Planned Extensions。

## Definition of Done (team quality bar)

* Tests added/updated where appropriate.
* Lint / typecheck / CI green if implementation follows.
* Docs/notes updated if behavior or architecture contracts change.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* 暂不默认修改 `web/` 参考层。
* 暂不默认实现完整浏览器 Web 产品。
* 暂不复制不适合本项目运行时模型的 cc 内部实现细节。
* 暂不把 React/Ink/Web 框架引入 Python domain/runtime services。
* 暂不实现远程 Bridge / IDE / daemon / Web control plane。

## Technical Notes

* Start workflow read: `.trellis/workflow.md`.
* Guidelines indexes read: `.trellis/spec/frontend/index.md`, `.trellis/spec/backend/index.md`, `.trellis/spec/guides/index.md`.
* Current git branch from context: `codex/stage-12-14-context-compact-foundation`.
* Current worktree already has unrelated/unconfirmed changes: deleted `.env.example`, untracked `.coding-deepgent/`.
* Frontend specs are currently Deferred; if product Web becomes active, `.trellis/spec/frontend/*` should be reactivated from real product code conventions.
* `/root/claude-code-haha/package.json` uses `ink`, `react`, `zod`, `chalk`, `figures`, `wrap-ansi`, and related terminal UI dependencies.
* Current reference `web/package.json` already uses Next 16, React 19, TypeScript, and `tsx`, but `web/` remains tutorial/reference unless deliberately promoted.
* cc source inspected:
  * `/root/claude-code-haha/src/entrypoints/cli.tsx`
  * `/root/claude-code-haha/src/screens/REPL.tsx`
  * `/root/claude-code-haha/src/components/App.tsx`
  * `/root/claude-code-haha/src/components/Messages.tsx`
  * `/root/claude-code-haha/src/components/Message.tsx`
  * `/root/claude-code-haha/src/components/PromptInput/PromptInput.tsx`
  * `/root/claude-code-haha/src/components/permissions/PermissionRequest.tsx`
  * `/root/claude-code-haha/src/Tool.ts`
  * `/root/claude-code-haha/src/query.ts`
  * `/root/claude-code-haha/src/tools/TodoWriteTool/TodoWriteTool.ts`
* Local source inspected:
  * `coding-deepgent/src/coding_deepgent/cli.py`
  * `coding-deepgent/src/coding_deepgent/cli_service.py`
  * `coding-deepgent/src/coding_deepgent/runtime/events.py`
  * `coding-deepgent/src/coding_deepgent/rendering.py`
  * `coding-deepgent/src/coding_deepgent/renderers/text.py`
  * `coding-deepgent/src/coding_deepgent/todo/renderers.py`
  * `coding-deepgent/src/coding_deepgent/agent_loop_service.py`
  * `coding-deepgent/tests/cli/test_cli.py`
  * `coding-deepgent/tests/runtime/test_runtime_events.py`
* Current `web/` is a Next.js tutorial/reference site, not a product agent UI.

## Research Notes

### What similar tools do

* Claude Code / cc-haha uses a large React/Ink REPL surface. `screens/REPL.tsx` owns message state, prompt input, permission queue, spinner state, streaming text/tool-use state, transcript mode, task list display, and query loop wiring.
* cc-haha splits display into message renderers (`components/Messages.tsx`, `components/Message.tsx`) and tool-specific renderers/permission UIs (`Tool.ts`, `components/permissions/*`), but this is tightly coupled to TypeScript, React, Ink, Bun feature flags, and its custom AppState.
* cc-haha's important reusable idea is an eventful UI contract: user input, assistant streaming, tool call start/result/error, permission request/decision, task/todo state, compact/recovery boundaries, spinner/progress, and transcript visibility.
* LangChain/LangGraph provides official streaming primitives that map cleanly to this need: `messages` for tokens, `updates` for graph/agent step state, `custom` for app-defined progress, and HITL interrupts for approval/resume flows.

### Constraints from our repo/project

* Mainline is Python `coding-deepgent/`; current dependencies already include `typer` and `rich`.
* User now accepts TypeScript/React dependencies when that speeds delivery.
* The roadmap explicitly says the product should not become a UI/TUI clone.
* Existing renderer boundary is intentionally simple and terminal-compatible.
* Existing runtime event sink is local and queued, but not yet a full UI event bus or Web transport.
* Future Web support should not reuse terminal rendering strings as its source of truth; it should consume typed events/state snapshots and render independently.

### Feasible approaches here

**Approach A: React/Ink CLI shell over Python event backend** (Recommended after user clarified speed/dev-convenience priority)

* How it works: add a small TypeScript frontend package that uses React/Ink for the interactive CLI shell. It talks to `coding-deepgent` through a simple newline-delimited JSON event protocol or subprocess bridge. The Python side emits typed run/session/tool/todo/permission events; the TS side owns prompt input, message list, spinner/progress, and future component reuse.
* Pros: fastest path to cc-like UX, easiest to borrow cc component structure, keeps Python runtime intact, and creates event contracts Web can consume later.
* Cons: introduces Node/TS build tooling and a cross-process protocol earlier.

**Approach B: Python CLI-first event contract**

* How it works: keep Typer/Rich as the shipping UI, add a typed `FrontendEvent`/`RunEvent` envelope and an adapter from runtime/session/tool/todo updates to that envelope. CLI renders these events with Rich; future Web consumes the same stream over an API/SSE/WebSocket later.
* Pros: simplest now, fits Python/LangChain, avoids React/Ink port, creates the right Web seam early.
* Cons: less cc-like, slower to build rich prompt/input/permission UX, and less reusable with future React Web.

**Approach C: Direct cc-style TUI clone**

* How it works: introduce a richer Python TUI layer, likely Textual or equivalent, and try to mirror cc's full-screen REPL, prompt input, permission dialogs, spinner, and transcript layout.
* Pros: closest visual/interaction parity.
* Cons: much larger scope, pulls UI state deeply into runtime, likely conflicts with roadmap's no UI/TUI clone rule, delays core product quality.

**Approach D: Web-first control plane**

* How it works: create a backend API and browser app now; CLI becomes secondary.
* Pros: future Web starts immediately.
* Cons: highest product-scope expansion, requires frontend specs activation, API/auth/session transport decisions, and risks building UI before core runtime contracts are stable.

## Expected effect

Aligning with cc CLI should improve user-visible responsiveness, safety visibility, and session continuity. The local effect should be: users can see what the agent is doing, what tools/permissions/state changed, and how to resume, without needing a full Web app or cloned TUI.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| REPL shell | `screens/REPL.tsx` coordinates prompt input, streaming, messages, permissions, spinner | one coherent CLI run/session view | TS React/Ink shell + Python event bridge | partial | align effect and component shape, not copy full app |
| Message rendering | `components/Messages.tsx`, `components/Message.tsx` render user/assistant/system/tool messages | stable transcript/recovery display | TS message components over typed events | partial | align categories and layout |
| Tool rendering | `Tool.ts` exposes render hooks and `setToolJSX` | tool start/result/error are visible and typed | Python `ToolCapability` + TS render components | partial | align contract, not JSX in Python |
| Permission UX | `components/permissions/PermissionRequest.tsx` maps tools to approval dialogs | approval/reject/edit surfaces can pause/resume execution | Python permission/HITL events + TS approval UI | defer | event shape first, richer approval next |
| Todo/task status | `TodoWriteTool`, `TaskListV2`, spinner active forms | visible plan/task progress | TS todo/task components consuming state snapshots | partial | align now for CLI; Web later reuses data contracts |
| Streaming | `query.ts` yields assistant/tool/progress events | live feedback instead of final-only response | LangChain/LangGraph `stream(..., version="v2")` path | defer | add after CLI event envelope |
| Web/remote | Bridge/daemon/Web-heavy paths | browser UI can follow same runs later | future API/SSE/WebSocket adapter | defer | not in CLI v1 |

## Acceptance Targets

* A user can run a new cc-like CLI frontend and see a simple lifecycle view: prompt, assistant text, tool/progress state, permission/status messages, todos/tasks, recovery/session summary.
* Runtime/UI boundary is typed enough that a future Web renderer can subscribe to the same event/state stream without parsing Rich text.
* The implementation keeps Python/LangChain as the runtime, while TypeScript/React owns interactive UI rendering.
* The team can finish a complete CLI v1 quickly without building full cc parity.

## Planned Features

* Define a small frontend event contract for CLI/Web consumers.
* Add a TypeScript React/Ink CLI package or app shell.
* Add a Python subprocess/JSONL bridge that can run prompts and emit typed events.
* Implement minimal TS components for prompt input, message list, spinner/progress, todo/task status, and session/recovery summary.
* Selectively adapt cc frontend pieces only when they are mostly presentational and have limited dependency drag.
* Map existing runtime events, session summaries, todo/task snapshots, and tool/permission outcomes into the event contract.
* Keep current Python command groups (`run`, `sessions`, `memory`, `doctor`, etc.) as backend/debug fallbacks while the new CLI matures.

## Planned Extensions

* LangGraph streaming adapter using `stream_mode=["messages", "updates", "custom"]`, `version="v2"`.
* HITL approval/resume flow using LangGraph interrupts or equivalent local pause/resume seam.
* Web transport: SSE first for read-only run streams; WebSocket only when bidirectional live input becomes necessary.
* Browser Web app that reuses TS domain types and consumes typed events/session snapshots.
* Full-screen TUI, IDE/remote bridge, daemon control plane, and mobile-friendly surface.

## Decision (ADR-lite, proposed)

**Context**: The user wants a simple frontend, prefers cc CLI-like behavior, wants future Web support, and accepts TypeScript/React dependencies if that speeds delivery. The repo is Python `coding-deepgent/`, but cc's fastest reusable front-end shape is React/Ink.

**Decision**: Prefer Approach A: React/Ink CLI shell over Python event backend. Reuse cc's interaction model, selected component structure, and visual semantics; keep Python as the agent/runtime owner.

**Consequences**: The first milestone is not a browser app, but it creates a React/TypeScript UI layer that can later share types/components with Web. The cost is introducing Node tooling and a Python-to-TS event bridge now.

## Implementation Bias

以“搬 cc 的前端经验”为主，不以整包复制代码为主。

* Copy/adapt candidates: simple message rows, spinner/progress display ideas, permission prompt layout, todo/task visual presentation, footer/status concepts, small pure formatting helpers.
* Build locally: event schema, Python JSONL bridge, process lifecycle, session state mapping, permission decision protocol, package scaffolding, tests.
* Do-not-copy candidates: `screens/REPL.tsx` wholesale, cc `AppState`, Bun feature flag system, analytics/telemetry, Bridge/daemon/remote/team/IDE flows, provider-specific UI branches, full command catalog.
* Practical rule: if a cc file drags more than a few local dependencies or owns runtime behavior, extract the idea and rewrite; if it is mostly presentational and small, adapt it.

## Integrated CLI Frontend Completion Plan

### Delivery Mode

直接以一个集成交付任务完成 CLI 前端 v1，不按用户可见的小迭代拆开交付。

内部仍保留 stage/checkpoint，但 checkpoint 只用于控制质量和防止方向漂移；若 checkpoint verdict 是 `APPROVE`，继续下一 stage，不停下来重新讨论。

Default validation budget: `lean`，但因为该工作引入跨语言协议和新前端包，协议层、bridge 层、关键 UI reducer 层必须有 focused tests。

### Final CLI Target

完成后应有一个新的 cc-like CLI 入口，例如：

```text
coding-deepgent-ui
```

或开发期命令：

```text
npm --prefix coding-deepgent/frontend/cli run dev
```

用户可在一个交互式 React/Ink 界面里：

* 输入多轮 prompt。
* 看到 assistant 文本、运行状态、spinner/progress。
* 看到工具调用开始、结果、错误、权限/拒绝状态。
* 看到 TodoWrite / durable task 的当前状态快照。
* 查看/恢复 session 的 recovery brief。
* 在失败时看到清晰错误，而不是 Python traceback 或 JSONL 泄漏。

### Proposed File Layout

```text
coding-deepgent/
  frontend/
    protocol/
      README.md                 # event schema and stdin/stdout contract
      events.schema.json         # optional generated/handwritten schema
    cli/
      package.json
      tsconfig.json
      src/
        index.tsx                # bin entrypoint
        app.tsx                  # Ink root
        bridge/
          python-process.ts      # spawn + JSONL reader/writer
          protocol.ts            # TS event/input types
          reducer.ts             # event -> UI state
        components/
          prompt-input.tsx
          message-list.tsx
          message-row.tsx
          spinner.tsx
          status-footer.tsx
          permission-panel.tsx
          todo-panel.tsx
          session-panel.tsx
        styles/
          theme.ts
        __tests__/
          reducer.test.ts
          protocol.test.ts
          render-smoke.test.tsx
  src/coding_deepgent/
    frontend/
      __init__.py
      protocol.py               # Python event/input dataclasses or Pydantic models
      bridge.py                 # JSONL bridge loop
      event_mapping.py          # runtime/session/tool/todo -> frontend events
    cli.py                      # add bridge command group or hidden command
```

### Protocol Shape

Use newline-delimited JSON over stdio for first delivery.

Python stdout is reserved for frontend events. Python stderr is reserved for logs/debug. TS stdin sends user inputs and control decisions.

#### FrontendEvent v1

```json
{"type":"session_started","session_id":"...","workdir":"..."}
{"type":"user_message","id":"...","text":"..."}
{"type":"assistant_delta","message_id":"...","text":"..."}
{"type":"assistant_message","message_id":"...","text":"..."}
{"type":"tool_started","tool_call_id":"...","name":"...","summary":"..."}
{"type":"tool_finished","tool_call_id":"...","name":"...","status":"success","preview":"..."}
{"type":"tool_failed","tool_call_id":"...","name":"...","error":"..."}
{"type":"permission_requested","request_id":"...","tool":"...","description":"...","options":["approve","reject"]}
{"type":"permission_resolved","request_id":"...","decision":"approve"}
{"type":"todo_snapshot","items":[{"content":"...","status":"in_progress","activeForm":"..."}]}
{"type":"task_snapshot","items":[...]}
{"type":"runtime_event","kind":"query_error","message":"...","metadata":{}}
{"type":"recovery_brief","text":"..."}
{"type":"run_finished","session_id":"...","status":"completed"}
{"type":"run_failed","session_id":"...","error":"..."}
```

#### FrontendInput v1

```json
{"type":"submit_prompt","text":"..."}
{"type":"permission_decision","request_id":"...","decision":"approve"}
{"type":"permission_decision","request_id":"...","decision":"reject","message":"..."}
{"type":"interrupt"}
{"type":"exit"}
```

### Stage 1: Scaffolding And Protocol Contract

Goal: create the package and protocol without yet needing live LLM.

Implementation:

* Add `coding-deepgent/frontend/cli` package with `ink`, `react`, `typescript`, `tsx` or build tooling.
* Add TS protocol types and reducer.
* Add Python protocol models and JSONL helpers.
* Add fixture event streams for UI smoke tests.
* Add docs in `frontend/protocol/README.md`.

Focused validation:

* TS typecheck passes.
* Reducer tests prove event order updates UI state deterministically.
* Python protocol tests validate event serialization and bad event rejection.

Checkpoint:

* `APPROVE` if the TS app can render a fixture stream and Python can emit valid JSONL.

### Stage 2: Python Bridge For Existing Runtime

Goal: run real `coding-deepgent` prompts through the bridge.

Implementation:

* Add `coding-deepgent frontend bridge` or hidden `coding-deepgent ui-bridge` command.
* Bridge reads `FrontendInput` from stdin and writes `FrontendEvent` to stdout.
* First pass may use current `run_prompt_with_recording()` final response path, then emit lifecycle events around it.
* Map existing `RuntimeEventSink` snapshot and session/recovery data into `runtime_event` / `recovery_brief` events.
* Preserve Python CLI fallback commands unchanged.

Focused validation:

* Python bridge test with fake agent: `submit_prompt` -> `user_message` -> `assistant_message` -> `run_finished`.
* Bridge test verifies stderr/logs do not corrupt stdout JSONL.
* Existing `tests/cli/test_cli.py` remains passing.

Checkpoint:

* `APPROVE` if a TS bridge client can spawn Python and complete a fake prompt round trip.

### Stage 3: Interactive React/Ink CLI Shell

Goal: deliver the usable cc-like local CLI.

Implementation:

* Implement `App` with prompt input, message list, spinner, status footer, and error boundary.
* Implement subprocess bridge client with reconnect/exit handling.
* Implement multi-turn prompt loop over a persistent Python bridge process.
* Render assistant final messages first; streaming deltas can be wired after the stable bridge.
* Add keyboard shortcuts: submit, Ctrl+C interrupt/exit path, maybe `/exit`.
* Add safe fallback display when event payload is unknown.

cc adaptation:

* Borrow layout ideas from `PromptInput`, `Messages`, `Message`, `Spinner`, and permission components.
* Rewrite components locally with a small prop surface; do not import cc source wholesale.

Focused validation:

* TS reducer tests for multi-turn state.
* TS render smoke tests against fixture event streams.
* Manual command with fake Python bridge or fixture mode.

Checkpoint:

* `APPROVE` if the UI is usable with fake bridge and does not require live API keys.

### Stage 4: Tool/Todo/Session Visibility

Goal: make the UI meaningfully better than final-text-only.

Implementation:

* Map `TodoWrite` result/state into `todo_snapshot`.
* Map durable tasks into `task_snapshot` if existing task state is available without new runtime complexity.
* Map tool capability metadata and middleware outcomes into `tool_started` / `tool_finished` / `tool_failed` where available.
* Show recovery brief/session info in a session panel or startup notice.
* Show runtime evidence/query errors as status/system rows.

Focused validation:

* Python event mapping tests for todos, runtime events, query errors, recovery brief.
* TS UI tests for todo panel, runtime event rows, failed run display.

Checkpoint:

* `APPROVE` if live or fake event streams display the main cc-like work-state surfaces.

### Stage 5: Permission UX And Interrupt Readiness

Goal: add the visible approval surface even if full LangGraph HITL is deferred.

Implementation:

* Define permission request/resolution event handling in the protocol.
* Render `permission-panel.tsx` with approve/reject choices.
* If current Python permission runtime cannot truly pause yet, emit denied/ask events as visibility first and keep full pause/resume as explicit follow-up.
* If local pause is feasible without replacing runtime seams, wire `permission_decision` input into the Python permission path.

Focused validation:

* TS tests for permission request queue and decision dispatch.
* Python protocol tests for permission decision validation.
* If pause/resume is implemented, fake tool permission test proves no tool executes before approval.

Checkpoint:

* `APPROVE` if permission events render and decisions are protocol-safe.
* `ITERATE` if true pause/resume needs a separate LangGraph HITL task; keep visible permission status in CLI v1 and defer full interrupt only with explicit rationale.

### Stage 6: Real Streaming Upgrade

Goal: move from final-response events to live streaming where practical.

Implementation:

* Add a LangChain/LangGraph streaming path using `stream_mode=["messages","updates","custom"]`, `version="v2"` if compatible with current agent construction.
* Map message chunks to `assistant_delta`.
* Map graph/tool updates to tool/progress events.
* Preserve non-streaming fallback only as an explicit bridge mode, not hidden duplicate logic.

Focused validation:

* Fake streaming agent test emits ordered deltas and final message.
* TS reducer coalesces deltas into a stable message.
* Non-streaming bridge test still passes.

Checkpoint:

* `APPROVE` if streaming works with fake and at least one local real path.
* `ITERATE` if LangChain runtime shape makes streaming risky; keep final-response CLI v1 only if streaming would destabilize the runtime, and record streaming as a named exception.

### Stage 7: Productization And Documentation

Goal: make the CLI easy to run and maintain.

Implementation:

* Add scripts/documentation for dev and installed usage.
* Add a wrapper command if appropriate.
* Update `coding-deepgent/README.md` with the new CLI frontend.
* Update `.trellis/spec/frontend/*` only for real conventions established by this implementation.
* Keep old Typer commands as backend/debug surface.

Focused validation:

* `npm --prefix coding-deepgent/frontend/cli run typecheck`.
* `npm --prefix coding-deepgent/frontend/cli test` if test runner is added.
* Targeted Python tests for protocol/bridge/event mapping.
* Existing relevant Python CLI/session/todo/runtime event tests.

Terminal checkpoint:

* `APPROVE` if the CLI frontend can run locally, fake-mode tests pass, targeted Python tests pass, and docs explain usage.

## CLI v1 Completion Criteria

This task counts as complete when:

* A React/Ink CLI frontend exists in `coding-deepgent/frontend/cli`.
* A Python JSONL bridge exists and can complete at least fake-agent and normal prompt flows.
* The UI supports multi-turn prompt input and renders assistant messages without corrupting terminal output.
* The UI renders at least these event classes: session start/end, user message, assistant message/delta, runtime event/error, todo snapshot, tool started/finished/failed, recovery brief.
* Permission event UI exists; true pause/resume may be accepted as outside CLI v1 only if current runtime makes it unsafe to wire in this pass.
* Focused TS and Python tests cover protocol, reducer, bridge, and key event mapping.
* Existing Python CLI fallback remains functional.

## Explicit Non-CLI-v1 Follow-Ups

* Browser Web app over the same protocol.
* SSE/WebSocket server adapter.
* Full LangGraph HITL interrupt integration if not completed in Stage 5.
* Richer cc component parity: transcript search, virtualized long history, command palette, slash commands, full task navigation, theme customization.
* Packaging polish: single installer, published npm package, binary wrappers.

## Final Closeout (2026-04-19)

This brainstorm is complete and has been implemented beyond the original CLI v1
target:

* React/Ink CLI package exists under `coding-deepgent/frontend/cli`.
* Python JSONL bridge and renderer-neutral frontend protocol exist under
  `coding_deepgent.frontend`.
* Real streaming and same-process CLI permission HITL pause/resume have been
  implemented and validated in later focused tasks.
* Product shortcut `coding-deepgent-ui` now exists.
* Future browser/Web remains an explicit follow-up over the producer/adapter
  boundary, not a reason to keep this planning task active.

## Stop Conditions For This Integrated Pass

Stop and ask only if:

* The chosen TS/Ink package setup cannot run in this repo without a major package-management decision.
* Python bridge needs to replace LangChain/LangGraph runtime seams instead of wrapping them.
* True permission pause/resume requires a product decision about HITL persistence/checkpointing.
* The worktree has conflicting user changes in files this task must modify.
* Live LLM behavior blocks validation and no fake-mode path can prove the frontend contract.

## Implementation Checkpoint: CLI v1 Integrated Pass

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Added Python frontend protocol package: `coding_deepgent.frontend.protocol`, `event_mapping`, and `bridge`.
* Added `coding-deepgent ui-bridge` JSONL backend command with deterministic `--fake` mode.
* Added React/Ink frontend package at `coding-deepgent/frontend/cli`.
* Added TS protocol types, Python subprocess bridge, deterministic reducer, prompt input, message list, spinner/status footer, permission panel, todo panel, and recovery/session panel.
* Added product protocol documentation in `coding-deepgent/frontend/protocol/README.md`.
* Updated `coding-deepgent/README.md` with frontend commands.
* Reactivated frontend Trellis specs for the new product CLI frontend.
* Added lazy public package/CLI runtime imports so protocol/help-style imports do not eagerly load full runtime/subagent surfaces.
* Fixed a compact/tool_system import cycle by importing `maybe_persist_large_tool_result` from its concrete module.

Verification:

* `pytest -q tests/cli/test_cli.py tests/runtime/test_runtime_events.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py` -> 40 passed.
* `ruff check src/coding_deepgent/__init__.py src/coding_deepgent/frontend src/coding_deepgent/cli.py src/coding_deepgent/tool_system/middleware.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py` -> passed.
* `mypy src/coding_deepgent/frontend src/coding_deepgent/__init__.py` -> passed.
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed.
* `npm --prefix coding-deepgent/frontend/cli test` -> passed.
* `PYTHONPATH=src python3 -m coding_deepgent ui-bridge --fake` with JSONL input -> emitted ordered session/user/runtime/todo/assistant/recovery/run events.
* `PYTHONPATH=src python3 -m coding_deepgent --help` -> passed and lists `ui-bridge`.
* `npm --prefix coding-deepgent/frontend/cli run dev:fake` in PTY -> prompt input, fake bridge response, todo panel, recovery brief, and `/exit` path all worked.

Alignment:

* source files inspected: `/root/claude-code-haha/src/screens/REPL.tsx`, `/root/claude-code-haha/src/components/Messages.tsx`, `/root/claude-code-haha/src/components/Message.tsx`, `/root/claude-code-haha/src/components/PromptInput/PromptInput.tsx`, `/root/claude-code-haha/src/components/permissions/PermissionRequest.tsx`, `/root/claude-code-haha/src/Tool.ts`, `/root/claude-code-haha/src/query.ts`.
* aligned: React/Ink shell, prompt input, message list, spinner/progress, permission panel shape, todo/task display shape, eventful UI boundary.
* deferred: full transcript search, virtualized history, slash command catalog, command palette, true HITL pause/resume persistence, browser Web app.
* do-not-copy: cc AppState, Bun feature flags, analytics/telemetry, bridge/daemon/remote/team/IDE flows, full `REPL.tsx` wholesale.

Architecture:

* primitive used: JSONL protocol over stdio between TS frontend and Python runtime.
* why no heavier abstraction: fastest local CLI delivery; Web/SSE/WebSocket can later reuse the same event schema without forcing an HTTP server into CLI v1.

Boundary findings:

* Root `web/` remains reference-only.
* Python runtime remains the owner of session/tool/todo facts.
* TS frontend owns only display state derived from `FrontendEvent`.
* True live streaming is protocol-ready through `assistant_delta`, but the current real bridge uses existing non-streaming `run_once`; fake and reducer paths prove the UI contract.
* True permission pause/resume is protocol/UI-ready, but current Python permission runtime still converts `ask` into a tool error instead of a HITL interrupt.

Decision:

* continue only for non-CLI-v1 extensions such as browser Web, full LangGraph HITL, and richer cc parity.

Reason:

* CLI v1 frontend is implemented and validated against fake bridge plus focused Python/TS tests. Remaining work is explicitly outside the CLI v1 completion line.
