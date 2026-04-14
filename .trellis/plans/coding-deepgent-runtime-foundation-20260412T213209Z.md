<!-- Recovered on 2026-04-14 from local Codex/OMX session logs after OMX uninstall. This file is reconstructed from direct session output and is high confidence. -->
# Context Snapshot — coding-deepgent runtime foundation

Task statement: Produce consensus planning artifacts for `coding-deepgent` runtime foundation: `.omx/plans/prd-coding-deepgent-runtime-foundation.md` and `.omx/plans/test-spec-coding-deepgent-runtime-foundation.md`.

Desired outcome: A product-stage plan for turning `coding-deepgent` into a professional LangChain-native cc runtime foundation, using LangChain/LangGraph primitives first and cc-haha semantics through extension seams where LangChain does not directly match.

Known code facts:
- Product scope is `coding-deepgent/`; tests enforce no imports from `agents_deepagents` and no public `sNN` modules.
- Current product status is `stage-2-session-foundation` in `coding-deepgent/project_status.json`.
- Current app uses `langchain.agents.create_agent` with `PlanningState`, `PlanContextMiddleware`, tools `[bash, read_file, write_file, edit_file, TodoWrite]`, and a process-global `SESSION_STATE`.
- `TodoWrite` is aligned with cc-haha public contract: tool name `TodoWrite`, top-level `todos`, required `content/status/activeForm`, strict Pydantic schema, hidden `InjectedToolCallId`, `Command(update={"todos": ...})`, and parallel TodoWrite guard.
- File tools in `coding_deepgent/tools/filesystem.py` currently rely on function-signature schema inference rather than explicit Pydantic `args_schema`.
- `PlanContextMiddleware` currently uses mutable instance attribute `_updated_this_turn`, which should be replaced by graph state or deterministic message/state inspection before professional concurrency.
- `sessions.py` is a product JSONL transcript/snapshot layer, not a LangGraph checkpointer. `create_agent` supports `checkpointer`, `store`, `context_schema`, and `state_schema`.

LangChain/LangGraph docs facts:
- `create_agent` is a LangGraph-backed runtime and accepts `state_schema`, `context_schema`, `checkpointer`, and `store`.
- Tools should use Pydantic `args_schema`; `Command(update=...)` updates graph state; injected runtime/call-id fields should be hidden from the model.
- Custom state should extend `AgentState` / TypedDict. Middleware-owned state should use middleware `state_schema`; `state_schema` on `create_agent` is also supported.
- Middleware should avoid mutating instance attributes for cross-call state; graph state is scoped to thread/concurrency.
- LangGraph checkpointers persist state by `thread_id`; stores are for cross-thread memory.

cc-haha reference points already inspected:
- `/root/claude-code-haha/src/query.ts`
- `/root/claude-code-haha/src/Tool.ts`
- `/root/claude-code-haha/src/services/tools/toolOrchestration.ts`
- `/root/claude-code-haha/src/services/tools/toolExecution.ts`
- `/root/claude-code-haha/src/services/tools/StreamingToolExecutor.ts`
- `/root/claude-code-haha/src/tools/TodoWriteTool/*`
- `/root/claude-code-haha/src/utils/todo/types.ts`
- `/root/claude-code-haha/src/types/logs.ts`, `src/utils/sessionStorage.ts`, resume command/session refs.

Constraints:
- Plan only; do not implement source code in this workflow.
- No new dependency without explicit approval. Plan may identify optional future dependency for persistent checkpointer.
- Prefer LangChain/LangGraph primitives over custom loops/wrappers.
- Keep modules professional and modular: tools, middleware, state, runtime context, sessions, renderers, permissions/resources separate.
- Do not copy cc product UI/TUI, telemetry, full AppStateStore, MCP bus, plugin hook runtime, TodoV2, or verifier policy in this stage.

Likely touchpoints:
- `coding-deepgent/src/coding_deepgent/app.py`
- `coding-deepgent/src/coding_deepgent/state.py`
- `coding-deepgent/src/coding_deepgent/tools/filesystem.py`
- `coding-deepgent/src/coding_deepgent/tools/planning.py`
- `coding-deepgent/src/coding_deepgent/middleware/planning.py`
- new `coding_deepgent/runtime/*`
- possibly `coding_deepgent/tools/discovery.py`, `middleware/tool_guard.py`, `runtime/checkpointing.py`
- `coding-deepgent/tests/*`
- `coding-deepgent/docs/*`, `project_status.json`, `README.md`
