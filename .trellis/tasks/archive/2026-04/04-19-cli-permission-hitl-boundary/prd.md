# CLI permission HITL boundary

## Goal

把 `coding-deepgent` CLI/frontend 里的 permission `ask` 从“返回错误文本给模型和 UI”升级为真实的 human-in-the-loop pause/resume：运行在需要审批时暂停，frontend 收到待审批事件，用户决策后通过同一 LangGraph thread 恢复执行。

## Acceptance Targets

* destructive / approval-required tool calls不再直接在 frontend 中表现为最终 `ToolMessage(status="error")`，而是先暂停并发出 `permission_requested`
* frontend `permission_decision` 会通过 `Command(resume=...)` 恢复同一 run / thread
* 用户批准后，原 tool call 继续执行并最终完成当前 assistant turn
* 用户拒绝后，工具以 bounded error surface 返回，agent 继续/结束当前 turn，但不崩溃
* 真实 HITL 仅依赖 LangGraph interrupt/checkpointer seam，不引入自定义 query loop
* 当前实现边界显式限定为 frontend/CLI surface 的进程内 `memory` checkpointer；不宣称跨进程 durable resume

## Planned Features

* 在 permission `ask` 分支引入 LangGraph `interrupt()`
* 在 frontend producer/bridge 中识别 `__interrupt__` 并映射为 `permission_requested`
* 为 `permission_decision` 增加真实 resume path，使用 `Command(resume=...)`
* 在 frontend default runner 为 HITL surface 启用进程内 `memory` checkpointer
* 为 approve/reject/resume ordering、多 pending interrupt id map、fallback/non-HITL 行为补 focused tests

## Planned Extensions

* edit-tool-call style HITL
* cross-process durable HITL resume
* browser Web HITL cards / richer approval UI
* packaging/product command polish

## Requirements

* 保持 `coding-deepgent` backend runtime LangChain/LangGraph-native，不引入自定义 executor loop
* 不绕过现有 `ToolCapability` / `ToolPolicy` / `ToolGuardMiddleware` 权限语义
* protocol 变更必须双端同步：Python models、TS protocol、reducer/tests
* permission request id 必须能稳定映射到 LangGraph interrupt resume
* 默认 CLI/Typer 非 frontend surface 不需要同时支持 HITL；当前范围只覆盖 frontend bridge/client/gateway
* 若实现中发现必须依赖 durable external checkpointer 才能成立，应记录 blocker 并停止，不做假 pause/resume

## Acceptance Criteria

* [x] `ToolGuardMiddleware` 的 `ask` 分支触发可恢复 interrupt，而不是直接返回最终错误
* [x] frontend bridge 能把 interrupt 转成 `permission_requested`
* [x] `permission_decision` 能恢复同一 thread，并继续产出后续 tool/assistant events
* [x] reject 路径保持 bounded error，不破坏当前 run
* [x] frontend surface 自动具备满足 interrupt 的进程内 checkpointer
* [x] focused Python tests、TS tests、typecheck、至少一个 CLI/frontend smoke 通过

## Code-Spec Depth Check

Target contracts to update or verify:

* `.trellis/spec/backend/langchain-native-guidelines.md`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* `.trellis/spec/backend/error-handling.md`
* `.trellis/spec/frontend/type-safety.md`
* `.trellis/spec/frontend/quality-guidelines.md`

Concrete contract to define:

* `permission_requested.request_id` must map to LangGraph interrupt ids
* `permission_decision` resumes the same `thread_id`
* frontend HITL uses `memory` checkpointer only for same-process pause/resume
* reject path returns bounded tool-visible failure instead of crashing the run

Validation matrix to prove:

* Good: approval pauses, resumes, and tool completes
* Base: rejection resumes and returns bounded error
* Bad: unknown/mismatched request id does not corrupt session state or silently approve

## Technical Notes

Likely code surfaces:

* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `coding-deepgent/src/coding_deepgent/frontend/producer.py`
* `coding-deepgent/src/coding_deepgent/frontend/protocol.py`
* `coding-deepgent/src/coding_deepgent/frontend/client.py`
* `coding-deepgent/src/coding_deepgent/frontend/runs.py`
* `coding-deepgent/src/coding_deepgent/frontend/gateway.py`
* `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`

Out of scope:

* generic non-frontend CLI `run` command HITL
* Web product UI
* durable external checkpoint persistence

## Resolution (2026-04-19)

Implemented a bounded frontend-only HITL permission seam without replacing the
existing LangChain/LangGraph runtime shape:

* `ToolGuardMiddleware` now uses LangGraph `interrupt()` for
  `permission_required` decisions only when the runtime entrypoint is a frontend
  HITL surface.
* frontend bridge sessions now preserve pending permission requests and resume
  them through `Command(resume=...)` on the same LangGraph thread.
* JSONL bridge and embedded `FrontendClient` now build shared prompt/resume
  runners for HITL mode.
* frontend HITL surfaces automatically switch from `checkpointer_backend=none`
  to in-process `memory` only for the frontend runtime builder; the global
  product default remains unchanged.
* FastAPI run service / gateway was intentionally left on the old non-HITL path
  because it still lacks a resume endpoint and should not silently claim true
  approval workflows yet.

## Verification (2026-04-19)

* `python3 -m py_compile ...` on touched frontend/tool-system modules -> passed
* `pytest -q tests/frontend/test_frontend_bridge.py tests/tool_system/test_tool_system_middleware.py` -> `23 passed`
* `pytest -q tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/tool_system/test_tool_system_middleware.py` -> `36 passed`
* `npm --prefix coding-deepgent/frontend/cli test` -> `8 passed`
* `npm --prefix coding-deepgent/frontend/cli run typecheck` -> passed
* `ruff check src/coding_deepgent/frontend src/coding_deepgent/tool_system/middleware.py tests/frontend/test_frontend_bridge.py tests/tool_system/test_tool_system_middleware.py` -> passed
* `mypy src/coding_deepgent/frontend src/coding_deepgent/tool_system/middleware.py` -> passed
* manual fake frontend smoke with dynamic request id:
  * first run emitted `session_started`, `user_message`, `permission_requested`
  * resume run emitted `permission_resolved`, tool/assistant events, and final `run_finished`
