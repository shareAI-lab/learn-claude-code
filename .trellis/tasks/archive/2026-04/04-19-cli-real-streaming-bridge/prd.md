# CLI real streaming bridge

## Goal

让 `coding-deepgent` 的 React/Ink CLI 从当前“等待 `run_once` 完成后一次性回放结果”升级为真实流式桥接：assistant 文本按增量流入，现有 runtime/tool/progress 事件在执行中实时显示。

## Acceptance Targets

* `coding-deepgent ui` 在真实后端路径下通过 `assistant_delta` 增量显示 assistant 文本。
* 现有 `runtime_event`、`tool_call`、`tool_result`、`todo_snapshot` 等桥接事件在运行中保持有序并继续可消费。
* `assistant_delta` 与最终 `assistant_message` 共享稳定 `message_id`。
* 非流式路径仅作为显式 fallback 或测试路径存在，不再是默认真实桥接行为。
* Python 和 TypeScript 协议/测试同步更新。

## Planned Features

* 在 Python frontend bridge 中增加真实 streaming prompt runner。
* 将 LangChain/LangGraph stream parts 映射到现有 `FrontendEvent` 联合类型。
* 保持 fake bridge 可重放、可测试。
* 更新 TS reducer 以正确处理 interleaved `assistant_delta` / final message / tool events。
* 为事件顺序、message_id 连贯性和 fallback 行为补 focused tests。

## Planned Extensions

* true HITL permission pause/resume
* Web/SSE transport
* richer tool-specific renderers
* transcript search / slash commands / command palette

## Requirements

* 保持改动范围在 `coding-deepgent/src/coding_deepgent/frontend/*`、CLI bridge/protocol/reducer，以及必要的 runtime invocation seam。
* 不引入独立自定义 query loop；优先使用 LangChain/LangGraph 官方 streaming surface。
* 不让 React 组件直接读取 subprocess stdout；桥接仍通过 typed protocol 进入 reducer。
* 协议字段必须严格、双端一致，不能在 Python/TS 两侧出现不同步事件定义。
* 若真实 streaming seam 暴露明确 blocker，必须记录边界并保留 deterministic fake mode。

## Acceptance Criteria

* [x] Python bridge 在真实路径下发出 `assistant_delta` 增量事件。
* [x] 最终 `assistant_message` 与先前增量使用同一 `message_id`。
* [x] TS reducer 正确聚合增量文本并在最终消息到达后保持稳定显示。
* [x] 现有 fake mode 和 non-streaming fallback 仍通过 focused tests。
* [x] Focused Python tests、TS tests、typecheck、smoke checks 通过。

## Code-Spec Depth Check

Target contracts to update or verify:

* `.trellis/spec/frontend/type-safety.md`
* `.trellis/spec/frontend/quality-guidelines.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

Concrete contract to define:

* `assistant_delta` / `assistant_message` ordering and shared `message_id`
* real-stream vs fallback runner selection boundary
* error surfacing when streaming setup fails

Validation matrix to prove:

* Good: streaming assistant text arrives incrementally and finalizes correctly
* Base: fake mode and explicit fallback path still render a complete assistant response
* Bad: invalid or out-of-order delta/final payload does not corrupt reducer state

## Technical Notes

Probable code surfaces:

* `coding-deepgent/src/coding_deepgent/frontend/bridge.py`
* `coding-deepgent/src/coding_deepgent/frontend/protocol.py`
* `coding-deepgent/src/coding_deepgent/frontend/event_mapping.py`
* `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
* `coding-deepgent/frontend/cli/src/app.tsx`

Out of scope for this task:

* true permission pause/resume
* HTML/Web UI
* new CLI feature family beyond the existing event surface

## Resolution (2026-04-19)

This task did not require new product-code implementation. Focused code
research plus validation confirmed the real streaming bridge is already present
in the current mainline:

* `coding-deepgent/src/coding_deepgent/frontend/producer.py`
  * `build_default_prompt_runner()` already prefers `_run_streaming_prompt()`
    by default and keeps an explicit non-streaming fallback.
  * `_run_streaming_prompt()` already maps LangChain/LangGraph stream parts into
    `assistant_delta`, tool, and runtime events while preserving a final
    `assistant_message`.
* `coding-deepgent/src/coding_deepgent/frontend/protocol.py`
  and `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
  already define `assistant_delta` / `assistant_message` with shared
  `message_id`.
* `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
  already aggregates streaming deltas into a stable assistant message.

## Verification (2026-04-19)

* `pytest -q tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_runs.py tests/frontend/test_frontend_client.py tests/frontend/test_frontend_gateway.py tests/frontend/test_stream_bridge.py`
  -> `19 passed`
* `npm --prefix coding-deepgent/frontend/cli test`
  -> `8 passed`
* `npm --prefix coding-deepgent/frontend/cli run typecheck`
  -> passed
* fake JSONL bridge smoke via `python3 -m coding_deepgent ui-bridge --fake`
  showed ordered `assistant_delta` events followed by final
  `assistant_message` with the same `message_id`
