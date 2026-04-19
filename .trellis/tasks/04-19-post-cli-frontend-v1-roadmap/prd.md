# brainstorm: post CLI frontend v1 roadmap

## Goal

在 `coding-deepgent` CLI 前端 v1 已完成后，决定下一阶段前端/交互工作的优先级：是先让现有 CLI 更实时、更安全，还是转向 Web 端、打包发布或更深 cc parity。

## What I already know

* 用户询问“后续?”，需要路线选择而不是立即实现。
* CLI frontend v1 已完成：React/Ink CLI + Python JSONL bridge + fake mode + protocol/reducer/components/tests。
* 当前 CLI v1 已支持：prompt input、message list、spinner/status、todo panel、recovery brief、permission panel 协议、runtime/tool/todo/session event rendering。
* 已验证：
  * `pytest -q tests/cli/test_cli.py tests/runtime/test_runtime_events.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py` -> 40 passed
  * `ruff check ...` -> passed
  * `mypy src/coding_deepgent/frontend src/coding_deepgent/__init__.py` -> passed
  * `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed
  * `npm --prefix coding-deepgent/frontend/cli test` -> passed
  * fake JSONL bridge smoke -> passed
  * fake React/Ink PTY smoke -> passed
* Current true gaps:
  * Real bridge still wraps existing non-streaming `run_once`; protocol/UI already supports `assistant_delta`.
  * Permission UI/protocol exists, but Python permission runtime still treats `ask` as tool error rather than true HITL pause/resume.
  * Browser Web app is not implemented.
  * CLI package is dev-run capable but not polished as a single installed binary/distribution.
  * Deeper cc parity such as transcript search, virtualized long history, slash commands, command palette, and richer tool rendering is deferred.

## Assumptions (temporary)

* CLI v1 is considered complete enough; “后续” should mean next product increment, not retroactively redefining CLI v1.
* User likely wants the highest-leverage next step, not a slow checklist.
* Since TypeScript/React is accepted, future Web can reuse TS protocol/types but should not parse terminal output.

## Open Questions

* CLI 完善阶段是否一口气覆盖 streaming + HITL + packaging + 核心 cc parity，还是分成多个内部 stage？

## Requirements (evolving)

* 后续计划必须建立在当前 JSONL protocol 和 React/Ink CLI 上。
* 不应把 Web 或 cc parity 混进一个无边界的大任务，除非用户明确要一口气做。
* 任何改变 Python runtime/session/tool boundary 的后续都必须有 focused Python tests。
* 任何改变 protocol 的后续都必须同时更新 Python protocol、TS protocol、TS reducer 和协议文档。
* 用户明确选择：先把 CLI 完善，再做 HTML/Web。
* HTML/Web 在 CLI 完善完成前不进入实现范围。

## Acceptance Criteria (evolving)

* [x] 明确下一阶段主目标：CLI 完善优先。
* [x] 明确哪些功能进入下一阶段，哪些继续排除。
* [ ] 形成可直接执行的一阶段计划。
* [ ] 识别需要更新的 specs/tests。

## Definition of Done (team quality bar)

* Tests added/updated where appropriate.
* Lint / typecheck / CI green if implementation follows.
* Docs/notes updated if behavior changes.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* 本 brainstorm 不直接实现代码。
* 不重新打开 CLI v1 的已完成范围，除非发现实际 blocker。
* HTML/Web viewer、SSE/WebSocket server、browser UI 暂不实现。

## Research Notes

### Constraints from current implementation

* Python bridge: `coding_deepgent.frontend.bridge` currently emits ordered events around existing `cli_service.run_once`.
* TS frontend: `frontend/cli/src/bridge/reducer.ts` already supports `assistant_delta` and permission queue.
* Protocol docs already reserve `permission_decision`, `assistant_delta`, `runtime_event`, `tool_*`, `todo_snapshot`, and `recovery_brief`.
* The old Python Typer CLI remains a backend/debug fallback.

### Feasible next-stage approaches

**Approach A: Real Streaming First** (Recommended)

* How: add a streaming bridge mode that maps LangChain/LangGraph `messages`, `updates`, and `custom` stream parts into existing `assistant_delta`, `tool_*`, and `runtime_event` events.
* Pros: biggest UX jump; makes CLI feel like a real cc-like frontend; benefits future Web because stream protocol becomes real.
* Cons: touches runtime invocation path and may expose LangChain streaming edge cases.

**Approach B: HITL Permission First**

* How: convert permission `ask` from “tool error visibility” into true pause/resume using LangGraph interrupts or a local pending-decision seam, then wire `permission_decision` from TS.
* Pros: biggest safety/product correctness jump; matches cc permission UX more meaningfully.
* Cons: harder boundary; requires checkpoint/persistence decision and careful tool execution ordering tests.

**Approach C: Web Read-Only Viewer First**

* How: add a minimal Web app or local server that consumes the same event stream as read-only session/run timeline.
* Pros: proves future Web direction; likely easier if it starts read-only.
* Cons: less useful than streaming/HITL if CLI still lacks real-time backend; adds server/transport scope.

**Approach D: Packaging/Install Polish First**

* How: create one command/wrapper for `coding-deepgent-ui`, lock install path, document setup, maybe wire npm script from repo root.
* Pros: low risk, makes current CLI easier to use immediately.
* Cons: does not improve runtime capability.

**Approach E: Deep cc Parity First**

* How: add transcript search, virtualized history, slash commands, command palette, richer tool renderers, themes.
* Pros: closest to Claude Code feel.
* Cons: many UI features depend on streaming/HITL and richer event data; risk of polishing around incomplete runtime feedback.

## Expansion Sweep

### Future evolution

* In 1-3 months, the same protocol can back both React/Ink CLI and browser Web.
* Streaming and HITL are the two runtime seams most worth preserving before investing in Web polish.

### Related scenarios

* CLI, Web, and future remote/IDE surfaces should all consume typed events, not terminal text.
* Existing Typer commands should remain backend/debug fallbacks.

### Failure and edge cases

* Streaming can break tool-result pairing if deltas/tool updates are mapped incorrectly.
* HITL can accidentally execute a tool before approval if permission ordering is not enforced.
* Web transport can leak local session/tool data if auth/trust boundaries are not specified.

## Proposed Recommendation

推荐顺序：

1. **CLI Completion Pack**: real streaming + HITL permission + packaging/start command + focused cc-like CLI polish.
2. **Web/HTML**: only after CLI completion pack is validated.

Within CLI Completion Pack:

1. Real Streaming: makes the CLI materially better immediately and validates event ordering.
2. HITL Permission: safety-critical and uses the already-present permission panel/protocol.
3. Packaging Polish: make the CLI easy to run once bridge shape stabilizes.
4. Core cc-like CLI polish: transcript/search/slash commands only where they rely on stable streaming/HITL data.

## Candidate Next Task: Real Streaming Bridge

### Goal

Make `coding-deepgent-ui` stream assistant tokens and tool/progress updates live instead of waiting for the final `run_once` result.

### Acceptance Targets

* Interactive CLI shows assistant text incrementally through `assistant_delta`.
* Tool/model progress appears during the run through existing event types.
* Non-streaming bridge remains available only as an explicit fallback path.
* Fake streaming tests and at least one local real bridge path validate event ordering.

### Planned Features

* Add streaming prompt runner in Python bridge.
* Map LangChain/LangGraph stream parts to `FrontendEvent`.
* Add fake streaming runner for deterministic tests.
* Extend TS reducer tests for interleaved deltas/tool events.
* Update protocol docs with ordering guarantees.

### Planned Extensions

* HITL permission pause/resume.
* Web stream transport.
* Richer tool-specific renderers.

## Decision (ADR-lite)

**Context**: CLI v1 exists and works through JSONL bridge, but real bridge is not streaming and permission approval is protocol/UI-ready only. User wants CLI completed before HTML/Web.

**Decision**: Next product work should be a CLI Completion Pack. Do not start Web/HTML until CLI has real streaming, permission handling, and productized launch path.

**Consequences**: Web waits longer, but when it starts it consumes a mature event protocol rather than forcing bridge redesign.

## CLI Completion Pack Plan

### Acceptance Targets

* Assistant output streams live in the React/Ink CLI.
* Tool/progress/runtime events are visible during a run, not only after completion.
* Permission `ask` can be surfaced as an approval interaction; if true pause/resume requires a deeper LangGraph checkpoint decision, the plan must stop and record that boundary explicitly.
* CLI can be started with a documented product command, not only a dev script.
* Existing `ui-bridge --fake` remains deterministic for tests and demos.
* Web/HTML remains out of scope.

### Planned Features

* Add real streaming bridge path with `assistant_delta`.
* Add fake streaming runner and event-order tests.
* Wire permission request/decision path as far as current runtime seam safely allows.
* Add root/package command wrapper for `coding-deepgent-ui` or equivalent.
* Improve core CLI ergonomics: clearer status footer, interrupted/failed states, unknown event fallback, useful startup diagnostics.

### Planned Extensions

* Browser Web/HTML.
* SSE/WebSocket transport.
* Deep transcript virtualization/search.
* Full slash command catalog and command palette.

## Remaining Preference Question

CLI 完善阶段你希望怎么推进？

1. **One integrated CLI Completion Pack** — 推荐；内部 stage 连续完成 streaming、permission、packaging、CLI polish。
2. **Streaming-only first** — 更稳；先把实时输出打实，再单独做 HITL/packaging。
3. **Packaging-first** — 先让当前 CLI 更容易使用，再补 runtime 能力。

## Complete Implementation Plan: CLI Completion Pack

### Execution Mode

Use one integrated task with internal checkpoints.

Mode: `lean`.

Reason: the CLI frontend foundation already exists and is validated. The next
work is strongly coupled around one protocol/bridge/UI surface, so repeatedly
splitting visible tasks would create churn. Internal checkpoints still protect
runtime boundaries.

### Final Outcome

After this pack, `coding-deepgent-ui` should feel like the default local CLI
frontend, not a prototype wrapper.

A user should be able to:

* Start the CLI with one documented product command.
* Submit multiple prompts.
* Watch assistant output stream live.
* See tool/progress/runtime events during execution.
* See todo/session/recovery state update predictably.
* Approve or reject permission requests when the runtime can safely pause.
* Exit/intercept failures without raw stack traces or corrupt terminal state.
* Continue using the old Typer commands as backend/debug fallbacks.

HTML/Web remains explicitly out of scope until this is complete.

### Acceptance Targets

* `coding-deepgent-ui` or an equivalent documented command starts the React/Ink CLI from the repo without manually setting `PYTHONPATH`.
* Real runs emit live `assistant_delta` events when the underlying runtime supports streaming.
* Tool/progress events are emitted before run completion when available, not only after `run_once`.
* Permission `ask` behavior is represented through `permission_requested`; true pause/resume is implemented only if it can be done without replacing LangChain/LangGraph seams.
* Fake bridge mode covers streaming, tool, permission, failure, and interrupt scenarios deterministically.
* Existing Python CLI command groups keep working.
* Protocol docs, Python protocol models, TS protocol types, and reducer tests stay in sync.
* Focused Python and TS validation passes.

### Planned Features

* Streaming event contract hardening:
  * define ordering guarantees for `assistant_delta` and final `assistant_message`
  * define when `run_finished` may fire
  * define error behavior for partial streams
* Python streaming bridge:
  * add a streaming-capable prompt runner alongside current `run_once`
  * map stream chunks to frontend events
  * preserve explicit non-streaming fallback
* Tool/progress visibility:
  * map model/tool updates to `tool_started`, `tool_finished`, `tool_failed`, and `runtime_event`
  * keep metadata bounded and secret-safe
* Permission handling:
  * emit `permission_requested` for ask decisions when possible
  * wire `permission_decision` to runtime only if safe pause/resume is available
  * otherwise record a precise blocker and keep visible ask/deny UI behavior
* CLI polish:
  * product command/wrapper
  * better startup diagnostics
  * clearer status footer
  * interrupted/failed states
  * unknown-event fallback row
  * lightweight slash commands that do not require runtime changes, such as `/exit`, `/clear`, `/help`
* Documentation and specs:
  * update protocol docs
  * update README usage
  * update frontend quality/spec docs if conventions change

### Planned Extensions

* HTML/Web UI.
* SSE/WebSocket transport.
* Full LangGraph HITL persistence if it is larger than this pack.
* Transcript virtualization/search.
* Full slash-command catalog.
* Command palette.
* Rich tool-specific renderers for every tool family.
* Installer/published package distribution beyond repo-local usage.

### Out Of Scope For This Pack

* Browser UI or HTML renderer.
* Remote/IDE/daemon control plane.
* Replacing LangChain/LangGraph runtime loops.
* Copying cc `REPL.tsx` wholesale.
* Provider-specific cache/cost UI.
* Solving unrelated dirty worktree changes.

## Stage Plan

### Stage 0: Preflight And Baseline Lock

Purpose: establish current green baseline and protect against unrelated dirty changes.

Files likely read:

* `coding-deepgent/src/coding_deepgent/frontend/*`
* `coding-deepgent/frontend/cli/src/*`
* `coding-deepgent/src/coding_deepgent/cli_service.py`
* `coding-deepgent/src/coding_deepgent/agent_loop_service.py`
* `coding-deepgent/src/coding_deepgent/agent_runtime_service.py`
* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `.trellis/spec/frontend/*`
* `.trellis/spec/backend/langchain-native-guidelines.md`

Actions:

* Confirm current tests still pass for frontend/bridge.
* Identify unrelated dirty files that must not be touched.
* Confirm package scripts work from repo root and package root.

Validation:

```bash
pytest -q tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py
npm --prefix coding-deepgent/frontend/cli run typecheck
npm --prefix coding-deepgent/frontend/cli test
```

Checkpoint:

* `APPROVE` if current CLI v1 baseline is still green.
* `STOP` if unrelated dirty changes directly conflict with bridge/runtime files.

### Stage 1: Protocol And Fake Streaming Contract

Purpose: make streaming behavior deterministic before touching real runtime.

Actions:

* Extend protocol docs with stream ordering:
  * `assistant_delta` can repeat for one `message_id`
  * `assistant_message` finalizes accumulated text
  * `run_failed` may follow partial deltas
  * `run_finished` closes a prompt turn
* Extend fake bridge with streaming scenario support.
* Add fake events for:
  * assistant delta accumulation
  * tool start/finish interleaving
  * runtime progress event
  * permission request/resolution
  * failed run after partial output
* Strengthen TS reducer tests for interleaved streams.

Likely files:

* `coding-deepgent/frontend/protocol/README.md`
* `coding-deepgent/src/coding_deepgent/frontend/protocol.py`
* `coding-deepgent/src/coding_deepgent/frontend/bridge.py`
* `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
* `coding-deepgent/frontend/cli/src/__tests__/reducer.test.ts`
* `coding-deepgent/tests/frontend/test_frontend_bridge.py`
* `coding-deepgent/tests/frontend/test_frontend_protocol.py`

Validation:

* Python protocol/bridge tests.
* TS protocol/reducer tests.
* Fake PTY smoke for one streaming fixture if feasible.

Checkpoint:

* `APPROVE` if fake streaming contract is deterministic and UI handles it.

### Stage 2: Real Streaming Bridge

Purpose: make real CLI runs stream into the React/Ink frontend.

Technical approach:

* Prefer official LangChain/LangGraph streaming surfaces:
  * `stream_mode=["messages", "updates", "custom"]`
  * `version="v2"` if supported by the compiled agent path
* Add a streaming prompt runner in `coding_deepgent.frontend.bridge`.
* Keep existing non-streaming runner as explicit fallback, not hidden duplicate behavior.
* Do not replace `agent_loop_service.run_agent_loop` unless the current seam cannot expose streaming.

Event mapping:

* `messages` text chunks -> `assistant_delta`
* final assistant state -> `assistant_message`
* tool/model updates -> `tool_*` or `runtime_event`
* exceptions -> `run_failed`
* state snapshot after completion -> `todo_snapshot`

Likely files:

* `coding-deepgent/src/coding_deepgent/frontend/bridge.py`
* `coding-deepgent/src/coding_deepgent/frontend/event_mapping.py`
* `coding-deepgent/src/coding_deepgent/agent_runtime_service.py`
* `coding-deepgent/src/coding_deepgent/cli_service.py`
* tests under `coding-deepgent/tests/frontend/test_frontend_bridge.py`

Validation:

* Fake streaming runner test.
* Real-ish fake compiled-agent test if current runtime can be stubbed.
* Existing `tests/cli/test_cli.py`.
* No-network tests only.

Stop condition:

* If the compiled LangChain agent cannot stream without a larger runtime refactor, stop and split a prerequisite runtime streaming seam task.

Checkpoint:

* `APPROVE` if a real bridge path emits deltas without breaking existing `run_once`.
* `ITERATE` if only a smaller streaming seam is needed locally.
* `SPLIT` if this becomes a full runtime architecture change.

### Stage 3: Tool/Progress Event Upgrade

Purpose: make tool/progress visibility useful during execution.

Actions:

* Audit current `RuntimeEvent` emissions:
  * tool guard allowed/completed/failed
  * query_error
  * token_budget
  * compact/runtime pressure events
* Map high-signal events to frontend events.
* Avoid turning every log into a UI event.
* Add UI row styles for:
  * running tool
  * completed tool
  * failed/denied tool
  * runtime warning/error

Likely files:

* `coding-deepgent/src/coding_deepgent/frontend/event_mapping.py`
* `coding-deepgent/frontend/cli/src/components/message-row.tsx`
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
* `coding-deepgent/tests/frontend/test_frontend_event_mapping.py`

Validation:

* Event mapping tests for allowed/completed/failed/permission_denied.
* Reducer tests for status transitions.

Checkpoint:

* `APPROVE` if tool/progress rows are accurate and bounded.

### Stage 4: Permission / HITL Boundary

Purpose: complete permission UX as far as current runtime safely allows.

Decision gate:

* Inspect whether permission `ask` can pause before tool execution using current middleware/runtime.
* If yes, implement a pending permission bridge flow.
* If no, do not fake approval. Emit visible ask/deny event and create a separate HITL runtime task.

Preferred implementation if feasible:

* `ToolGuardMiddleware` emits `permission_requested`.
* Python bridge waits for `permission_decision`.
* Approved decision resumes tool execution.
* Rejected decision returns model-visible bounded feedback.

Required safety invariant:

* No destructive tool executes before approval.

Likely files:

* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `coding-deepgent/src/coding_deepgent/permissions/*`
* `coding-deepgent/src/coding_deepgent/frontend/bridge.py`
* `coding-deepgent/frontend/cli/src/components/permission-panel.tsx`
* `coding-deepgent/tests/permissions/test_permissions.py`
* `coding-deepgent/tests/frontend/test_frontend_bridge.py`

Validation:

* Permission request event test.
* Approval path test if implemented.
* Rejection path test if implemented.
* Existing permission tests.

Stop condition:

* Stop if true HITL requires persistent LangGraph checkpoint/resume semantics that are not already present.

Checkpoint:

* `APPROVE` if true approval is safely implemented.
* `SPLIT` if a separate runtime HITL foundation is required.

### Stage 5: CLI Product Entry And Packaging Polish

Purpose: make the CLI easy to run after runtime behavior stabilizes.

Actions:

* Add repo-root or package-level script that starts the CLI without manual env setup.
* Decide final command shape:
  * `npm --prefix coding-deepgent/frontend/cli run dev`
  * `coding-deepgent-ui`
  * `coding-deepgent ui` wrapper
* Add startup diagnostics:
  * Node version
  * Python bridge availability
  * missing dependencies
  * non-TTY explanation
* Keep `ui-bridge --fake` for tests/demos.

Likely files:

* `coding-deepgent/frontend/cli/package.json`
* `coding-deepgent/frontend/cli/src/index.tsx`
* `coding-deepgent/frontend/cli/src/bridge/python-process.ts`
* `coding-deepgent/README.md`
* possibly root package/scripts if introduced

Validation:

* Non-TTY startup fails cleanly.
* Fake TTY smoke.
* README command works.

Checkpoint:

* `APPROVE` if a developer can start the CLI with one documented command.

### Stage 6: Core CLI UX Polish

Purpose: finish high-signal CLI polish without starting Web.

Actions:

* Improve status footer:
  * running
  * waiting for permission
  * failed
  * interrupted
  * bridge disconnected
* Add lightweight slash commands:
  * `/exit`
  * `/clear`
  * `/help`
  * possibly `/status`
* Add unknown-event fallback display.
* Improve recovery brief folding.
* Improve message list readability for long outputs.

Likely files:

* `coding-deepgent/frontend/cli/src/app.tsx`
* `coding-deepgent/frontend/cli/src/components/*`
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
* TS tests under `src/__tests__`

Validation:

* Reducer tests for failure/interrupted/clear/help states.
* TS typecheck/test.
* Fake PTY smoke.

Checkpoint:

* `APPROVE` if CLI is usable for normal local work without obvious rough edges.

### Stage 7: Final Verification And Documentation

Purpose: close CLI Completion Pack and prepare for later HTML/Web.

Actions:

* Update PRD checkpoint.
* Update README and protocol docs.
* Update Trellis frontend specs if new conventions emerged.
* Run focused final validation.

Final validation target:

```bash
pytest -q tests/cli/test_cli.py tests/runtime/test_runtime_events.py tests/permissions/test_permissions.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py
ruff check <touched-python-files>
mypy src/coding_deepgent/frontend src/coding_deepgent/__init__.py
npm --prefix coding-deepgent/frontend/cli run typecheck
npm --prefix coding-deepgent/frontend/cli test
```

Manual/PTY smoke:

```bash
npm --prefix coding-deepgent/frontend/cli run dev:fake
```

Terminal checkpoint:

* `APPROVE` if all focused checks pass and Web/HTML follow-up has a clean start point.

## Test Matrix

### Python

* `test_frontend_protocol.py`
  * strict event/input validation
  * extra fields rejected
  * new event types round-trip
* `test_frontend_bridge.py`
  * prompt -> ordered events
  * fake streaming deltas
  * partial stream failure
  * permission decision input
  * exit/interrupt behavior
* `test_frontend_event_mapping.py`
  * runtime events -> frontend events
  * tool guard phases
  * todo snapshot filtering
  * bounded metadata
* Existing:
  * `test_cli.py`
  * `test_runtime_events.py`
  * `test_permissions.py` when HITL changes

### TypeScript

* `protocol.test.ts`
  * parse/encode new events
  * unknown events rejected or surfaced safely
* `reducer.test.ts`
  * delta accumulation
  * final assistant message replacement
  * interleaved tool events
  * permission queue
  * failed/interrupted states
  * slash command state if reducer-owned

### Manual Smoke

* fake interactive prompt and exit
* non-TTY startup error
* real bridge help command
* if available, one live prompt with API credentials outside automated tests

## Risk Matrix

| Risk | Impact | Mitigation |
|---|---|---|
| LangChain compiled agent streaming is not compatible with current wrapper | Real streaming blocked | split a small runtime streaming seam task; keep fake streaming tests |
| Tool/progress events become noisy | CLI becomes unreadable | whitelist high-signal events only |
| Permission UI appears but does not actually gate execution | unsafe false confidence | do not claim true HITL unless no-execute-before-approval test passes |
| Cross-process JSONL stdout gets polluted | frontend parser breaks | keep Python stdout event-only; logs stderr-only; tests cover protocol errors |
| Packaging creates duplicated entrypoints | maintenance confusion | keep old Typer as backend/debug; document one preferred UI command |
| Web pressure leaks into CLI pack | scope creep | Web/HTML explicitly out of scope until terminal checkpoint |

## Stop Conditions

Stop and ask before continuing if:

* Real streaming requires replacing `agent_loop_service` or bypassing LangChain/LangGraph runtime seams.
* HITL requires persistent checkpoint/resume semantics not already present.
* Tests fail due to unrelated dirty subagent/runtime refactor files.
* Packaging requires choosing a repo-wide package manager/workspace policy.
* A change would make old Typer CLI commands unusable.

## Proposed Implementation Order

1. Stage 0: baseline lock.
2. Stage 1: fake streaming contract.
3. Stage 2: real streaming bridge.
4. Stage 3: tool/progress event upgrade.
5. Stage 4: permission/HITL boundary.
6. Stage 5: product command/packaging.
7. Stage 6: CLI UX polish.
8. Stage 7: final verification/docs.

## Final Confirmation

完整计划建议采用 **One integrated CLI Completion Pack**，但内部按上面 8 个 stage 执行。Web/HTML 在全部 CLI 完善验收后再启动。

如果确认，我下一步会把这个 planning task 进入 Task Workflow，并从 Stage 0 开始实施。

## Implementation Checkpoint: CLI Completion Pack

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Converted frontend bridge execution from batch-returned event lists to live event emission through an `EventEmitter`.
* Added streaming-capable prompt runner path that maps LangChain/LangGraph-style `messages`, `updates`, `custom`, and `values` stream parts to frontend events.
* Added fake streaming behavior for deterministic demos/tests: assistant deltas, tool start/finish, permission request, partial failure, todo snapshot, and recovery brief.
* Added product command `coding-deepgent ui` and `coding-deepgent ui --fake` over the React/Ink CLI package.
* Added `start` and `start:fake` package scripts.
* Added local CLI slash commands `/help`, `/clear`, and retained `/exit`.
* Improved status footer for permission/failure/status visibility.
* Added reducer support for local UI actions and streaming/tool interleaving.
* Added tests for streaming event order, partial failure, fake permission request, streaming part mapping, local commands, and product UI command invocation.
* Updated protocol docs with ordering guarantees and the current HITL boundary.
* Updated README and frontend specs with CLI completion commands and validation expectations.

Verification:

* `pytest -q tests/cli/test_cli.py tests/runtime/test_runtime_events.py tests/permissions/test_permissions.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py` -> 56 passed.
* `ruff check src/coding_deepgent/__init__.py src/coding_deepgent/frontend src/coding_deepgent/cli.py src/coding_deepgent/tool_system/middleware.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/cli/test_cli.py` -> passed.
* `mypy src/coding_deepgent/frontend src/coding_deepgent/__init__.py` -> passed.
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed.
* `npm --prefix coding-deepgent/frontend/cli test` -> passed, 8 TS tests.
* `PYTHONPATH=src python3 -m coding_deepgent ui --fake` in PTY -> prompt, streaming deltas, permission panel, approve, `/help`, `/clear`, `/exit` all worked.

Architecture:

* Streaming uses the existing frontend JSONL protocol and does not introduce HTTP/Web transport.
* The real streaming path prefers official agent `.stream(...)` with stream modes `messages`, `updates`, `custom`, and `values`.
* The old non-streaming path remains as fallback when the compiled agent stream surface is unavailable.
* Python remains the runtime/session/tool owner; TypeScript remains display state owner.

Boundary findings:

* True HITL pause/resume is not implemented in this pass because current `ToolGuardMiddleware` is synchronous and returns a `ToolMessage` on `ask`; there is no safe pending-decision seam yet.
* The UI/protocol can display and resolve permission prompts in fake mode, but real destructive-tool gating requires a dedicated runtime HITL foundation before it can be claimed.
* HTML/Web remains out of scope and now has a stronger CLI/event protocol to build on.

Decision:

* CLI completion pack is complete enough to make HTML/Web the next product family if desired.
* If safety is prioritized before Web, the next task should be dedicated runtime HITL pause/resume foundation.
