# brainstorm: deerflow-inspired cli web decoupling

## Goal

借鉴 DeerFlow 的 Harness/App/Gateway/Client/Web 分层，重新规划 `coding-deepgent` 的 CLI 与未来 HTML/Web 解耦方式：保留当前 React/Ink CLI 成果，同时建立可扩展到 Web/SSE 的 backend runtime/event 架构，避免 Web 复用 CLI 进程或解析 terminal output。

## What I already know

* 用户要求“规划仿 deerflow 优化”。
* 已源码研究 `bytedance/deer-flow`，包括：
  * `backend/docs/STREAMING.md`
  * `backend/docs/HARNESS_APP_SPLIT.md`
  * `backend/packages/harness/deerflow/client.py`
  * `backend/packages/harness/deerflow/runtime/runs/worker.py`
  * `backend/packages/harness/deerflow/runtime/stream_bridge/*`
  * `backend/app/gateway/services.py`
  * `backend/app/gateway/routers/thread_runs.py`
  * `frontend/src/core/threads/hooks.ts`
  * `frontend/src/core/api/stream-mode.ts`
* DeerFlow 的核心不是“CLI/Web 共用 UI”，而是：
  * Harness/runtime 共享
  * Web 走 Gateway/SSE/SDK
  * Embedded client 走 in-process stream
  * 不同 transport 相似但不强行合并
* 当前 `coding-deepgent` 已有：
  * Python runtime/domain packages under `coding-deepgent/src/coding_deepgent`
  * React/Ink CLI under `coding-deepgent/frontend/cli`
  * Python JSONL bridge under `coding_deepgent.frontend`
  * Protocol types/events for CLI
  * Typer CLI fallback commands
* 当前 `web/` 仍是 reference/tutorial layer，不是 product Web。
* 当前 worktree 有大量其它脏改，规划不应假设能直接提交。

## Assumptions (temporary)

* `coding-deepgent` 不需要像 DeerFlow 一样立刻物理拆成 publishable harness package，但需要先形成同等边界。
* CLI 和未来 Web 应该共享 runtime/event producer，不共享 transport。
* 当前 JSONL protocol 可以作为 CLI transport v1，但 Web 不应该复用 stdio bridge。
* Web 启动前应先补一个 Gateway/SSE adapter 或至少明确 HTTP stream contract。

## Open Questions

* 是否采用“先抽 runtime stream producer + adapters”作为下一阶段架构主线？

## Requirements (evolving)

* 不让 Web 依赖 React/Ink CLI。
* 不让 runtime/domain 层 import CLI/Web/Gateway。
* 保留当前 `coding-deepgent ui` / `ui-bridge` CLI 成果。
* 建立 DeerFlow 风格的多 consumer 模型：
  * CLI: stdio JSONL adapter
  * Web: future SSE/HTTP adapter
  * tests/scripts: in-process/embedded adapter
* Streaming mode 命名必须按协议层显式翻译，不用一个常量假装所有层相同。
* HITL/permission 不应伪造；没有安全 pause/resume seam 前只能声明 UI/protocol ready。

## Acceptance Criteria (evolving)

* [x] 明确 DeerFlow 架构模式如何映射到 `coding-deepgent`。
* [x] 明确目标目录/模块边界。
* [x] 明确 staged implementation plan。
* [x] 明确哪些现在做、哪些留给 Web/HTML 阶段。
* [x] 形成一个可以进入 Task Workflow 的计划。

## Definition of Done

* Planning doc is source-backed.
* Acceptance targets, planned features, planned extensions are explicit.
* Risks and stop conditions are recorded.
* No code implementation in this brainstorm.

## Out of Scope

* 本 brainstorm 不实现代码。
* 不直接引入 DeerFlow 代码。
* 不启动 HTML/Web 实现。
* 不把 `coding-deepgent` 物理拆包为 publishable package，除非后续单独批准。

## Research Notes

### DeerFlow patterns to reuse

**1. Harness/App split**

DeerFlow 将可复用 agent 能力放在 `backend/packages/harness/deerflow`，把 FastAPI Gateway 和 channels 放在 `backend/app`。规则是 App imports Harness，Harness never imports App。

映射到 `coding-deepgent`：

* `coding_deepgent.runtime`, `tool_system`, `sessions`, `memory`, `tasks`, `subagents`, `compact`, `permissions` 是 harness-like domain/runtime。
* `coding_deepgent.frontend` 当前混合了 protocol、JSONL bridge、runner adapter，后续应拆成更明确的 producer/adapters。
* 未来 `coding_deepgent.gateway` 或 `coding_deepgent.api` 应是 App/Gateway-like adapter，不应被 runtime import。

**2. Parallel stream paths are acceptable**

DeerFlow 明确保留两条流式路径：

* Gateway path: async `agent.astream` -> `StreamBridge` -> SSE.
* Embedded client path: sync `agent.stream` -> direct generator.

它没有强行复用，因为消费者模型不同。

映射到 `coding-deepgent`：

* CLI path: sync/process stdio JSONL is acceptable.
* Web path: async SSE/HTTP should be separate.
* Embedded/test path: direct in-process event generator is useful for tests and future scripting.

**3. Stream modes are protocol-layer translations**

DeerFlow 区分：

* Graph Python API: `messages`
* HTTP/LangGraph SDK: `messages-tuple`
* App/frontend event: consumers decide display semantics

映射到 `coding-deepgent`：

* Internal LangChain mode: `messages`
* Our runtime event: `assistant_delta`
* Future Web SSE event: either `frontend_event` with JSON payload or LangGraph-compatible `messages`/`values`
* Do not force one shared string constant across layers.

**4. StreamBridge belongs at network boundary**

DeerFlow uses `StreamBridge` for HTTP consumers because producer and consumer are different async tasks/connections, with heartbeat, replay, cleanup, and disconnect semantics.

映射到 `coding-deepgent`:

* Current CLI stdio does not need full `StreamBridge`.
* Future Web/SSE does need `RunManager` + `StreamBridge` or equivalent.
* Do not prematurely make CLI depend on HTTP Gateway.

**5. Frontend consumes a stable client API**

DeerFlow Web uses `@langchain/langgraph-sdk/react` `useStream`, not custom terminal protocol. It handles optimistic messages, thread/run metadata, reconnection, custom events, and finish callbacks.

映射到 `coding-deepgent`:

* Future Web can either consume LangGraph-compatible API or a simpler `FrontendEvent` SSE.
* If long-term Web matters, aim for LangGraph-compatible semantics where practical.

## Constraints From This Repo

* Current mainline is `coding-deepgent/`.
* `web/` is reference-only unless explicitly promoted.
* Current frontend CLI is in `coding-deepgent/frontend/cli`.
* Python protocol/bridge is in `coding_deepgent.frontend`.
* Backend specs require domain ownership and no business logic in `cli.py`, `app.py`, `containers`.
* Architecture guide prefers clean long-term boundaries over minimal compatibility shims.

## Feasible Approaches

### Approach A: Stream Producer + Adapter Split (Recommended)

How:

* Refactor `coding_deepgent.frontend` into:
  * `protocol.py`: renderer-neutral events/inputs
  * `producer.py`: in-process runtime event generator
  * `adapters/jsonl.py`: CLI stdio adapter
  * `adapters/sse.py` or future `gateway/*`: Web/SSE adapter
  * `runs.py`: optional RunManager/StreamBridge only when HTTP begins
* Current React/Ink CLI keeps using JSONL adapter.
* Future Web uses SSE adapter over the same producer/events.

Pros:

* Closest to DeerFlow principle without heavy physical package split.
* Preserves current CLI.
* Gives Web a clean start.
* Avoids runtime importing UI.

Cons:

* Some refactor before visible Web work.
* Need careful tests to avoid breaking current CLI.

### Approach B: Full DeerFlow-Style Gateway First

How:

* Add FastAPI Gateway now.
* Add RunManager + StreamBridge + SSE.
* Point Web and possibly CLI to Gateway.

Pros:

* Web-ready immediately.
* Strong network boundary.

Cons:

* Bigger dependency/surface jump.
* CLI does not need HTTP; forcing CLI through Gateway adds complexity.
* Premature before Web is implemented.

### Approach C: Physical Harness/App Package Split

How:

* Move reusable runtime into a harness package.
* Move CLI/Gateway/Web adapters into app packages.

Pros:

* Cleanest long-term library boundary.
* Strong alignment with DeerFlow.

Cons:

* High risk with current dirty worktree and active runtime refactors.
* Large import churn.
* Not necessary before Web.

### Approach D: Keep Current JSONL Bridge And Start Web Directly

How:

* Build Web around current bridge/protocol quickly.

Pros:

* Fastest visible browser demo.

Cons:

* Web may accidentally depend on CLI/studio assumptions.
* No RunManager/disconnect/replay semantics.
* Likely rework.

## Recommended Direction

Choose **Approach A: Stream Producer + Adapter Split**.

This gives us DeerFlow's useful boundary without copying its full infra prematurely.

## Acceptance Targets

* Runtime/domain code does not import CLI/Web/Gateway adapters.
* A shared in-process stream producer exists and can drive both current JSONL CLI and future SSE adapter.
* Current `coding-deepgent ui` and `ui-bridge` keep working.
* Protocol naming and stream-mode translations are documented.
* Tests prove producer -> JSONL adapter behavior without React/Ink.
* Future Web can be implemented as a new adapter, not by wrapping CLI.

## Planned Features

* Split `coding_deepgent.frontend.bridge` into producer + JSONL adapter responsibilities.
* Define `FrontendEvent` as the stable renderer-neutral event contract.
* Add an embedded/in-process client helper for tests/scripts.
* Introduce adapter naming:
  * `jsonl` for CLI
  * `sse` for future Web
  * `embedded` for direct Python use/tests
* Document protocol-layer translation:
  * LangChain `messages` -> `assistant_delta`
  * LangChain `updates`/runtime events -> `tool_*`/`runtime_event`
  * future SSE `frontend_event` or LangGraph-compatible mode names
* Add tests guarding no reverse imports from runtime to frontend adapters.

## Planned Extensions

* FastAPI Gateway/SSE adapter.
* RunManager + StreamBridge with heartbeat/replay/disconnect.
* Browser Web app.
* LangGraph SDK-compatible API surface.
* Persistent HITL checkpoint/resume.
* Physical harness package split if the project later needs published embedded library usage.

## Expansion Sweep

### Future evolution

* In 1-3 months, the same producer can drive CLI, Web, IM channels, and Python scripts.
* A Gateway can be added without changing CLI internals.

### Related scenarios

* `coding-deepgent ui` stays a local CLI adapter.
* Future `coding-deepgent serve` or `coding-deepgent gateway` becomes Web adapter.
* Existing Typer commands remain backend/debug fallbacks.

### Failure and edge cases

* If producer owns too much transport behavior, Web and CLI coupling returns.
* If adapter owns runtime state, session consistency breaks.
* If stream-mode translations are hidden behind shared constants, protocol confusion increases.
* If Web starts before adapter split, it may depend on JSONL/stdio assumptions.

## Proposed Stage Plan

### Stage 1: Boundary Spec And Import Guard

* Update Trellis backend/frontend specs with producer/adapter layering.
* Add import guard test:
  * runtime/domain packages must not import `frontend.adapters`, `frontend.cli`, or future `gateway`.

### Stage 2: Extract Producer

* Move runtime stream generation from `frontend.bridge` into `frontend.producer`.
* Producer exposes in-process iterator/generator of `FrontendEvent`.
* Keep `bridge.py` as JSONL adapter wrapper for compatibility.

### Stage 3: Embedded Client

* Add `frontend.client` or `runtime.client` for direct Python scripted use.
* It should call producer directly and return events, similar to DeerFlowClient but scoped to frontend events.

### Stage 4: JSONL Adapter Hardening

* Rename/organize current bridge as `adapters/jsonl.py`.
* Keep `coding-deepgent ui-bridge` command behavior unchanged.
* Tests verify event order unchanged.

### Stage 5: Gateway/SSE Design Prep

* Add docs/interfaces for future `RunManager` and `StreamBridge`.
* Do not implement server yet unless user explicitly starts HTML/Web.

### Stage 6: Web Readiness Checkpoint

* Confirm Web can start by implementing only a new adapter.
* Record remaining decisions:
  * LangGraph SDK compatibility vs custom `FrontendEvent` SSE.
  * Auth/trust model.
  * thread/run persistence.

## Decision (ADR-lite)

**Context**: CLI is now implemented with JSONL bridge. User wants future HTML/Web, and DeerFlow shows a clean separation between reusable harness/runtime and app-specific transport/UI adapters.

**Decision**: Do not make Web reuse CLI. Refactor toward a shared runtime stream producer with separate adapters: JSONL for CLI, SSE/Gateway for Web, embedded for scripts/tests.

**Consequences**: Web starts slightly later, but avoids rework and preserves a clean long-term boundary.

## One Question

是否按推荐的 **Approach A: Stream Producer + Adapter Split** 作为下一阶段架构优化方向？

1. **Yes, do producer/adapter split first** — 推荐；先把 DeerFlow 式边界打稳，再做 Web。
2. **Go straight to Gateway/SSE** — 更快进入 Web 后端，但范围更大。
3. **Go straight to Web UI** — 最快看到浏览器，但后续重构风险最高。

## Implementation Checkpoint: Producer / Adapter Split

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Added `coding_deepgent.frontend.producer` as the renderer-neutral runtime event producer.
* Added `coding_deepgent.frontend.adapters.jsonl` as the stdio JSONL transport adapter.
* Added `coding_deepgent.frontend.client.FrontendClient` as an embedded in-process consumer of `FrontendEvent`.
* Converted `coding_deepgent.frontend.bridge` into a backward-compatible import shim.
* Preserved existing `ui-bridge` behavior and tests through compatibility imports.
* Added an import guard to ensure runtime/domain code does not import frontend transport adapters.
* Updated backend/frontend specs and protocol docs with the producer/adapter boundary.

Verification:

* `pytest -q tests/frontend/test_frontend_client.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py` -> 19 passed.
* `ruff check src/coding_deepgent/frontend tests/frontend/test_frontend_client.py tests/frontend/test_frontend_bridge.py tests/structure/test_structure.py` -> passed.
* `mypy src/coding_deepgent/frontend` -> passed.
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed.
* `npm --prefix coding-deepgent/frontend/cli test` -> passed.
* `PYTHONPATH=src python3 -m coding_deepgent ui-bridge --fake` JSONL smoke -> passed.

## Implementation Checkpoint: RunManager / StreamBridge / SSE Foundation

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Added `coding_deepgent.frontend.stream_bridge.MemoryStreamBridge` with replayable per-run event logs and heartbeat/end sentinels.
* Added `coding_deepgent.frontend.runs.FrontendRunManager`, `RunRecord`, and `FrontendRunService` for background run lifecycle.
* Added `coding_deepgent.frontend.adapters.sse` with `format_sse` and `sse_consumer`.
* Reused existing `frontend.producer.BridgeSession` as the worker-side runtime event source.
* Preserved current CLI transport; no CLI-to-HTTP migration was introduced.
* Updated package exports and docs/specs for the new web foundation layers.

Verification:

* `pytest -q tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py` -> 24 passed.
* `ruff check src/coding_deepgent/frontend tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/structure/test_structure.py` -> passed.
* `mypy src/coding_deepgent/frontend` -> passed.

Architecture:

* We now have three adapter classes:
  * JSONL for CLI
  * embedded client for scripts/tests
  * SSE foundation for future Web
* `FrontendRunService` is transport-neutral orchestration; it publishes into `MemoryStreamBridge`.

Boundary findings:

* No HTTP server framework has been added yet; this is gateway-ready foundation only.
* Future HTML/Web can now start from SSE transport rather than wrapping CLI or JSONL.
* Real disconnect/cancel semantics remain intentionally minimal compared with DeerFlow's fuller async Gateway.

Architecture:

* Runtime-facing event generation is now separated from JSONL transport.
* Current CLI continues to use JSONL.
* Embedded Python consumption now exists without going through JSONL.
* Future Web can add SSE/Gateway adapter without wrapping CLI.

Boundary findings:

* Physical harness package split remains deferred.
* Gateway/SSE and HTML/Web remain deferred.
* `frontend.bridge` remains only for backwards compatibility; new imports should prefer `producer` or `adapters.jsonl`.

## Final Closeout (2026-04-19)

This brainstorm is complete. The recommended producer/adapter split and
RunManager/StreamBridge/SSE foundation have already been implemented:

* shared producer: `coding_deepgent.frontend.producer`
* CLI JSONL adapter: `coding_deepgent.frontend.adapters.jsonl`
* embedded client: `coding_deepgent.frontend.client`
* run lifecycle: `coding_deepgent.frontend.runs`
* replayable event bridge: `coding_deepgent.frontend.stream_bridge`
* SSE adapter/gateway foundation: `coding_deepgent.frontend.adapters.sse` and
  `coding_deepgent.frontend.gateway`

Remaining Web work should start from a new focused task, such as a gateway HITL
resume endpoint or browser UI, rather than keeping this architecture brainstorm
active.
