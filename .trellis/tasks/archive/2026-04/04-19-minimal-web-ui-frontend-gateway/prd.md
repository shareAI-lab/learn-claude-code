# minimal web ui over frontend gateway

## Goal

为 `coding-deepgent ui-gateway` 增加一个最小可用的 HTML/Web 页面，不引入复杂前端构建体系，只验证浏览器能提交 prompt、连接 SSE、并展示基础事件流。

## Requirements

* 使用现有 `FrontendRunService` / `MemoryStreamBridge` / `adapters.sse`。
* 页面应通过 `POST /api/runs` 创建 run，并通过 `EventSource` 连接 `/api/runs/{run_id}/stream`。
* 展示基础事件：
  * user message
  * assistant deltas/final message
  * tool started/finished/failed
  * runtime events
  * todo snapshot
  * recovery brief
  * permission request visibility
  * run finished / failed
* 不实现真正的 HTML/Web HITL gating。
* 不引入 Next/React 页面构建。

## Acceptance Criteria

* [x] `ui-gateway` 提供 `/ui` 页面。
* [x] 浏览器页可通过 SSE 展示基础事件。
* [x] Gateway 与 CLI 继续解耦。
* [x] Focused Python tests 覆盖 gateway health/run stream/UI route。

## Out of Scope

* 复杂浏览器应用框架。
* 认证、持久线程列表、复杂布局。
* 真正的 permission HITL 执行控制。

## Implementation Checkpoint

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Added product web shell at `coding-deepgent/frontend/web/index.html`.
* Added `coding_deepgent.frontend.web.load_web_ui_html()`.
* Added `/ui` route to the frontend gateway.
* The page now:
  * submits prompts via `POST /api/runs`
  * joins runs through `EventSource(/api/runs/{run_id}/stream)`
  * renders user, assistant, tool, runtime, todo, recovery, and permission-visibility state
* Permission display is explicitly non-authoritative in the page copy because true runtime HITL is not wired.

## Verification

* `pytest -q tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py tests/structure/test_structure.py tests/cli/test_cli.py` -> 56 passed.
* `ruff check src/coding_deepgent/frontend src/coding_deepgent/cli.py tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_sse.py tests/frontend/test_frontend_client.py tests/structure/test_structure.py tests/cli/test_cli.py` -> passed.
* `mypy src/coding_deepgent/frontend` -> passed.

## Architecture

* Browser UI consumes the SSE gateway, not the CLI JSONL adapter.
* CLI, embedded client, and browser now each have their own adapter over the shared producer/runtime foundation.
