# BaseAgent Compact Tool Alignment Design

## Goal

Align `homework/BaseAgent.py` with the explicit `compact` tool in
`s20_comprehensive/code.py`, while preserving the existing automatic and
reactive compaction paths.

## Scope

The change is limited to:

1. Registering a `compact` schema in `BUILTIN_TOOLS`.
2. Handling `compact` as a harness control signal inside the main
   `agent_loop()`.
3. Adding focused regression tests for registration and explicit compaction.

The change will not:

- register `compact` in `BUILTIN_HANDLERS`;
- expose `compact` to subagents or teammates;
- replace threshold-based automatic compaction;
- replace prompt-too-long reactive compaction;
- refactor the existing compaction pipeline.

## Design

### Tool contract

Add this schema to `BUILTIN_TOOLS`:

```python
{
    "name": "compact",
    "description": (
        "Summarize earlier conversation and continue with "
        "compacted context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"focus": {"type": "string"}},
        "required": [],
    },
}
```

`focus` is accepted for compatibility with S20 but is not consumed by the
current `compact_history()` implementation, matching the reference behavior.

### Main-loop behavior

After appending the assistant response and entering the tool-use loop:

1. Initialize `compacted_now = False`.
2. When a `compact` tool-use block is encountered:
   - replace `messages` with `compact_history(messages)`;
   - append a user continuation marker;
   - set `compacted_now = True`;
   - stop processing later tool-use blocks from that response.
3. If `compacted_now` is true, immediately continue the outer agent loop
   without appending ordinary tool results.

This does not leave an orphaned `tool_use`, because `compact_history()` replaces
the history containing the assistant compact request with a summarized history.

### Handler registry

Do not add `compact` to `BUILTIN_HANDLERS`. A normal handler only receives tool
arguments, while explicit compaction must replace the complete conversation
history. Keeping it in the loop makes that control-flow responsibility explicit
and matches S20.

## Error behavior

If `compact_history()` fails, the exception follows the existing agent-loop
failure behavior. No new retry layer or fallback is introduced in this
minimal change.

## Tests

Add focused tests that first fail against the current implementation:

1. `compact` is present exactly once in `BUILTIN_TOOLS`, has optional `focus`,
   and is absent from `BUILTIN_HANDLERS`.
2. A model response containing `compact` calls `compact_history()` once,
   discards later tool calls from the same response, appends the continuation
   marker, and makes another LLM request with compacted history.
3. Existing automatic and reactive compaction tests continue to pass.

## Acceptance criteria

- The main model can request `compact`.
- Explicit compaction re-enters the same main agent loop.
- No ordinary handler is required for `compact`.
- Automatic threshold compaction still runs before LLM calls.
- Reactive compaction still runs after prompt-too-long errors.
- Focused compact tests and existing compaction pair tests pass.
