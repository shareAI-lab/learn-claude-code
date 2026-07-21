# BaseAgent Live Streaming Design

## Objective

Restore true terminal streaming for the Lead Agent in
`homework/BaseAgent.py` without breaking the existing s11 error-recovery
limits, Anthropic tool pairing, compaction, memory, todo, durable Task, hook,
subagent, or background-task behavior.

The terminal and conversation history must stay consistent: text displayed to
the user is retained in `messages`, and the same request is never replayed after
any of its text has been displayed.

## Selected Strategy

Use real-time output with continuation-only recovery:

```text
8K request starts
  -> print each text chunk immediately
  -> normal completion: save the final response once
  -> max_tokens: save the partial response, switch subsequent requests to 64K,
     append CONTINUATION_PROMPT, and continue
```

Remove the current first-truncation behavior that discards the 8K response and
replays the same request with a 64K token budget. Replaying is incompatible with
true streaming because text from the discarded attempt may already be visible.

`ESCALATED_MAX_TOKENS` remains useful: it becomes the output budget for the
continuation request rather than a replay of the original request.

## Streaming Boundary

`create_message_streaming()` owns terminal delivery for the Lead Agent. It
must:

- accept `system`, `request_messages`, `model`, and `max_tokens` as it does now;
- iterate `stream.text_stream`;
- print every non-empty text chunk with `end=""` and `flush=True`;
- retain the emitted chunks for partial-stream error handling;
- return `stream.get_final_message()` after a successful stream;
- ensure the visible output ends with a newline before hooks, tool logs,
  recovery messages, or the next prompt are printed; add one only when the
  final emitted chunk does not already end with `"\n"`.

The Lead `agent_loop()` must not call `print_response_text()` for a successful
streamed response. The final Anthropic response is still appended to history
exactly once; only the duplicate terminal print is removed.

This design changes only Lead requests made through
`create_message_streaming()`. The synchronous subagent path keeps its current
printing and retry behavior unless it is separately migrated later.

## max_tokens Data Flow

The first response always uses `DEFAULT_MAX_TOKENS` and streams immediately.
When its `stop_reason` is `max_tokens`:

1. Append the returned partial assistant content to `messages`.
2. Do not call `print_response_text()` because the text is already visible.
3. Set `state.has_escalated = True`.
4. Set the next request budget to `ESCALATED_MAX_TOKENS`.
5. If `state.continuation_count` is below `MAX_CONTINUATIONS`, increment it,
   append `CONTINUATION_PROMPT`, and continue the Agent Loop.
6. If the continuation limit has been reached, retain the final partial
   response and return normally with an explicit recovery-limit diagnostic.

Every later `max_tokens` response follows the same save-and-continue path, up
to the existing continuation limit. No response that has produced visible text
is discarded.

## Stream Error Handling

Introduce a small `PartialStreamError` carrying:

- `partial_text`: the exact concatenation of chunks already printed;
- `cause`: the original exception.

`create_message_streaming()` follows two error paths:

- If no text chunk has been emitted, re-raise the original exception. Existing
  `with_retry()` behavior remains responsible for 429/529 retry and fallback,
  while the outer Agent Loop remains responsible for prompt-too-long recovery.
- If at least one text chunk has been emitted, raise `PartialStreamError` after
  completing the terminal line. `with_retry()` must immediately propagate this
  exception rather than replaying the request.

The Lead Agent Loop handles `PartialStreamError` before generic unrecoverable
errors:

1. append one assistant text message containing `partial_text`;
2. never replay the original request;
3. switch subsequent output to `ESCALATED_MAX_TOKENS`;
4. append `CONTINUATION_PROMPT` and continue when the continuation budget
   remains;
5. otherwise print a concise interruption marker, store that same marker in
   the partial assistant message, and return.

This preserves the invariant:

```text
visible assistant text == assistant text retained in messages
```

A transient 429/529 that occurs before the first chunk still uses the current
bounded retry and optional fallback model. A prompt-too-long error that occurs
before output still performs one reactive compaction and rebuilds context,
system prompt, and request messages before retrying.

## Tool and Runtime Compatibility

The final response object remains the source of truth for content blocks.
Consequently:

- successful `tool_use` blocks are appended unchanged;
- the immediately following user message still contains the matching
  `tool_result` blocks;
- streamed assistant text preceding a tool call is displayed once and remains
  in the same assistant response;
- PreToolUse and PostToolUse ordering is unchanged;
- background completions remain ordinary text notifications and never reuse a
  `tool_use_id`;
- compaction and memory extraction continue operating on saved messages;
- todo state, durable `.tasks/` state, skills, and dynamic system prompt
  assembly are unchanged.

No thread writes directly to Lead history as part of this change.

## Test Changes

Update `tests/test_homework_baseagent_error_recovery.py` to reflect the selected
streaming contract and add focused coverage for:

- chunks are printed in arrival order before `get_final_message()` completes;
- a normal response is displayed once and stored once;
- the first `max_tokens` response is stored instead of discarded;
- the next call uses `ESCALATED_MAX_TOKENS` and follows
  `CONTINUATION_PROMPT`;
- no same-request 8K-to-64K replay occurs;
- continuation remains bounded by `MAX_CONTINUATIONS`;
- 429/529 before the first chunk retains bounded retry and fallback behavior;
- an error after one or more chunks does not replay the request, stores the
  exact partial text once, and continues when allowed;
- prompt-too-long before the first chunk still compacts once and rebuilds the
  request;
- streamed responses containing tool calls keep valid tool-use/result pairing.

Use fake stream objects and deterministic events or call-order lists. Tests
must not call the live Anthropic API and must not depend on timing sleeps.

Run focused verification:

```text
uv run --with pytest pytest tests/test_homework_baseagent_error_recovery.py -q
```

Then run related regressions:

```text
uv run --with pytest pytest \
  tests/test_compaction_tool_pairs.py \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_homework_baseagent_task_system.py -q
```

Pre-existing s12 acceptance failures may remain, but this change must not add
new failures or change their causes.

## Non-Goals

- Do not add terminal cursor rewinding or ANSI-based deletion.
- Do not replay a request after visible output.
- Do not replace the Anthropic streaming API with a non-streaming call.
- Do not rewrite the Agent Loop or remove s11 recovery features.
- Do not add streaming to subagents, teammates, or background commands in this
  change.
- Do not change tool schemas, permissions, persistence formats, compaction
  thresholds, todo semantics, or Task state transitions.
