# coding-deepgent frontend protocol

The CLI frontend talks to the Python runtime over newline-delimited JSON.

Python stdout is reserved for `FrontendEvent` payloads. Python stderr is reserved
for logs and diagnostics. The TypeScript frontend writes `FrontendInput` payloads
to Python stdin.

## FrontendInput v1

```json
{"type":"submit_prompt","text":"implement the feature"}
{"type":"permission_decision","request_id":"req-1","decision":"approve"}
{"type":"permission_decision","request_id":"req-1","decision":"reject","message":"Use read-only mode."}
{"type":"interrupt"}
{"type":"exit"}
```

## FrontendEvent v1

```json
{"type":"session_started","session_id":"session-1","workdir":"/repo"}
{"type":"user_message","id":"user-1","text":"hello"}
{"type":"assistant_delta","message_id":"assistant-1","text":"partial"}
{"type":"assistant_message","message_id":"assistant-1","text":"done"}
{"type":"tool_started","tool_call_id":"call-1","name":"read_file","summary":"Reading file"}
{"type":"tool_finished","tool_call_id":"call-1","name":"read_file","status":"success","preview":"Read complete"}
{"type":"tool_failed","tool_call_id":"call-1","name":"write_file","error":"Approval required"}
{"type":"permission_requested","request_id":"req-1","tool":"write_file","description":"Write app.py","options":["approve","reject"]}
{"type":"permission_resolved","request_id":"req-1","decision":"approve"}
{"type":"todo_snapshot","items":[{"content":"Build UI","status":"in_progress","activeForm":"Building UI"}]}
{"type":"task_snapshot","items":[{"id":"task-1","content":"Ship inspect view","status":"in_progress"}]}
{"type":"context_snapshot","projection_mode":"collapse","history_messages":8,"model_messages":5,"visible_messages":4,"hidden_messages":4,"compact_count":1,"collapse_count":1,"session_memory_status":"current","latest_event":"collapse"}
{"type":"subagent_snapshot","total":1,"items":[{"created_at":"2026-04-20T00:00:00Z","agent_type":"general","role":"assistant","content":"Checked tests.","subagent_thread_id":"child-1"}]}
{"type":"runtime_event","kind":"query_error","message":"Query failed.","metadata":{}}
{"type":"recovery_brief","text":"Session: ..."}
{"type":"run_finished","session_id":"session-1","status":"completed"}
{"type":"run_failed","session_id":"session-1","error":"..."}
{"type":"protocol_error","error":"invalid JSON payload"}
```

The protocol is intentionally renderer-neutral so a future browser UI can consume
the same event stream over SSE or WebSocket.

## Producer and adapters

Runtime-facing event generation lives in `coding_deepgent.frontend.producer`.
Transport-specific code lives under `coding_deepgent.frontend.adapters`.

Current adapters:

- `adapters.jsonl` — stdio newline-delimited JSON for the React/Ink CLI.

Future adapters:

- `adapters.sse` or a Gateway package — Server-Sent Events for HTML/Web.
- embedded client — direct in-process event consumption for scripts/tests.

Runtime/domain packages should not import transport adapters. CLI and future Web
should share event semantics, not process implementations.

Current embedded consumer:

- `coding_deepgent.frontend.client.FrontendClient` — in-process Python client
  that consumes the same `FrontendEvent` stream without JSONL transport.

Current Web foundation:

- `coding_deepgent.frontend.runs.FrontendRunService` — background run lifecycle
- `coding_deepgent.frontend.stream_bridge.MemoryStreamBridge` — in-memory replayable event log
- `coding_deepgent.frontend.adapters.sse` — SSE frame formatter and consumer

## Ordering guarantees

- A prompt turn starts with `user_message`.
- `assistant_delta` may be emitted zero or more times for one `message_id`.
- `assistant_message` finalizes the assistant text for that `message_id`.
- Tool events may interleave with assistant deltas.
- Snapshot events such as `todo_snapshot`, `task_snapshot`,
  `context_snapshot`, and `subagent_snapshot` describe the latest known runtime
  state for the completed turn; consumers should replace prior snapshot state.
- `run_failed` may appear after partial deltas if execution fails mid-stream.
- `run_finished` closes a prompt turn.
- `protocol_error` describes malformed bridge input/output and does not imply the
  Python runtime failed.

## Current HITL boundary

The protocol supports `permission_requested` and `permission_decision`, and the
React/Ink CLI can render permission prompts. The current Python runtime still
needs a dedicated pause/resume seam before destructive tools can be truly held
pending approval. Until that seam exists, the UI must not claim that an approval
gated real tool execution.
