# Tool Result Storage Contracts

> Executable contracts for live large-output persistence and preview references.

## Scenario: Live Tool Result Storage

### 1. Scope / Trigger

- Trigger: changes touching `coding_deepgent.tool_system`, `coding_deepgent.compact`,
  runtime tool-result handling, or capability metadata for large-output tools.
- Applies when a live tool call may replace oversized inline tool output with a
  persisted file reference and preview for the model.
- This is a cross-layer contract because capability metadata, middleware result
  handling, runtime context/session id, workspace file paths, and tests must
  agree.
- For the broader five-factor tool protocol and safe defaults for
  `persist_large_output`, read
  [Tool Capability Contracts](./tool-capability-contracts.md).

### 2. Signatures

```python
def tool_results_dir(runtime_context: RuntimeContext) -> Path: ...

def persist_tool_result(
    content: str,
    *,
    runtime_context: RuntimeContext,
    tool_call_id: str,
    serialized_kind: str,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> PersistedToolResult: ...

def maybe_persist_large_tool_result(
    result: ToolMessage,
    *,
    runtime_context: RuntimeContext,
    max_inline_chars: int | None,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> ToolMessage: ...
```

### 3. Contracts

- Large-result persistence is a live runtime message optimization. It must not
  rewrite persisted session transcript history in this stage.
- `tool_results_dir(runtime_context)` must resolve inside the active workspace:

```text
<workdir>/.coding-deepgent/tool-results/<session_id>/
```

- For eligible tools, a successful `ToolMessage` whose serialized content length
  exceeds `max_inline_chars` must be rewritten to:
  - write the full content to a session-scoped file under `tool_results_dir(...)`
  - keep only a preview/reference message in `ToolMessage.content`
  - preserve `tool_call_id`, `status`, and other existing message metadata
- Rewritten preview content must be wrapped in:

```text
<persisted-output>
...
</persisted-output>
```

- The preview content must include the relative workspace path to the persisted
  file so a workspace read tool can reopen it later.
- A tool may remain `microcompact_eligible` even when replaying the original
  tool call would be unsafe or non-deterministic, as long as large-output
  persistence keeps a stable model-visible path to the full original output.
- Small successful results must remain unchanged.
- Error `ToolMessage` results must remain unchanged.
- Existing upstream `ToolMessage.artifact` must not be discarded. If a rewritten
  message adds storage metadata, the upstream artifact must remain reachable
  through the rewritten artifact payload.
- File naming must be deterministic from `tool_call_id` after path sanitization.
- If persistence raises an `OSError` in middleware, the middleware must fail
  open and return the original `ToolMessage` unchanged.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| large successful tool result from eligible tool | file is written; model-visible content becomes preview reference |
| small successful tool result from eligible tool | message remains unchanged |
| successful tool result from ineligible tool | message remains unchanged |
| error tool result | message remains unchanged |
| upstream artifact already present | rewritten artifact preserves upstream artifact |
| sanitized `tool_call_id` contains `:` or spaces | output filename is path-safe and deterministic |
| file write fails with `OSError` | original `ToolMessage` is returned |

### 5. Good / Base / Bad Cases

#### Good

```python
rewritten = maybe_persist_large_tool_result(
    ToolMessage(content="x" * 5000, tool_call_id="call:1"),
    runtime_context=context,
    max_inline_chars=4000,
)
```

Expected:
- writes full output under `.coding-deepgent/tool-results/<session_id>/call-1.txt`
- returns preview content wrapped in persisted-output markers

#### Base

```python
unchanged = maybe_persist_large_tool_result(
    ToolMessage(content="small", tool_call_id="call-1"),
    runtime_context=context,
    max_inline_chars=4000,
)
```

Expected:
- returns the original message object unchanged

#### Bad

```python
maybe_persist_large_tool_result(
    ToolMessage(content="x" * 5000, tool_call_id="call-1", status="error"),
    runtime_context=context,
    max_inline_chars=4000,
)
```

Expected:
- must not rewrite error results into persisted-output previews

### 6. Tests Required

- `coding-deepgent/tests/test_tool_result_storage.py`
- `coding-deepgent/tests/test_tool_system_middleware.py::test_tool_guard_persists_large_tool_output_for_eligible_tools`

Required assertion points:

- preview message contains persisted-output wrapper tags
- preview message contains a workspace-relative persisted file path
- persisted file contains full original content
- small results are unchanged
- middleware integration persists only after an allowed tool call
