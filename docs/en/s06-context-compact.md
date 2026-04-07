# s06: Context Compact

`s01 > s02 > s03 > s04 > s05 > [ s06 ] > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- Why long sessions inevitably run out of context space, and what happens when they do
- A four-lever compression strategy: persisted output, micro-compact, auto-compact, and manual compact
- How to move detail out of active memory without losing it
- How to keep a session alive indefinitely by summarizing and continuing

Your agent from s05 is capable. It reads files, runs commands, edits code, and delegates subtasks. But try something ambitious -- ask it to refactor a module that touches 30 files. After reading all of them and running 20 shell commands, you will notice the responses get worse. The model starts forgetting what it already read. It repeats work. Eventually the API rejects your request entirely. You have hit the context window limit, and without a plan for that, your agent is stuck.

## The Problem

Every API call to the model includes the entire conversation so far: every user message, every assistant response, every tool call and its result. The model's context window (the total amount of text it can hold in working memory at once) is finite. A single `read_file` on a 1000-line source file costs roughly 4,000 tokens (roughly word-sized pieces -- a 1,000-line file uses about 4,000 tokens). Read 30 files and run 20 bash commands, and you have burned through 100,000+ tokens. The context is full, but the work is only half done.

The naive fix -- just truncating old messages -- throws away information the agent might need later. A smarter approach compresses strategically: keep the important bits, move the bulky details to disk, and summarize when the conversation gets too long. That is what this chapter builds.

## The Solution

We use four levers, each working at a different stage of the pipeline, from output-time filtering to full conversation summarization.

```
Every tool call:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Lever 0: persisted-output]     (at tool execution time)
  Large outputs (>50KB, bash >30KB) are written to disk
  and replaced with a <persisted-output> preview marker.
        |
        v
[Lever 1: micro_compact]        (silent, every turn)
  Replace tool_result > 3 turns old
  with "[Previous: used {tool_name}]"
  (preserves read_file results as reference material)
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Lever 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Lever 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## How It Works

### Step 1: Lever 0 -- Persisted Output

The first line of defense runs at tool execution time, before a result even enters the conversation. When a tool result exceeds a size threshold, we write the full output to disk and replace it with a short preview. This prevents a single giant command output from consuming half the context window.

```python
PERSIST_OUTPUT_TRIGGER_CHARS_DEFAULT = 50000
PERSIST_OUTPUT_TRIGGER_CHARS_BASH = 30000   # bash uses a lower threshold

def maybe_persist_output(tool_use_id, output, trigger_chars=None):
    if len(output) <= trigger:
        return output                                    # small enough -- keep inline
    stored_path = _persist_tool_result(tool_use_id, output)
    return _build_persisted_marker(stored_path, output)  # swap in a compact preview
    # Returns: <persisted-output>
    #   Output too large (48.8KB). Full output saved to: .task_outputs/tool-results/abc123.txt
    #   Preview (first 2.0KB):
    #   ... first 2000 chars ...
    # </persisted-output>
```

The model can later `read_file` the stored path to access the full content if needed. Nothing is lost -- the detail just lives on disk instead of in the conversation.

### Step 2: Lever 1 -- Micro-Compact

Before each LLM call, we scan for old tool results and replace them with one-line placeholders. This is invisible to the user and runs every turn. The key subtlety: we preserve `read_file` results because those serve as reference material the model often needs to look back at.

```python
PRESERVE_RESULT_TOOLS = {"read_file"}

def micro_compact(messages: list) -> list:
    tool_results = [...]  # collect all tool_result entries
    if len(tool_results) <= KEEP_RECENT:
        return messages                                  # not enough results to compact yet
    for part in tool_results[:-KEEP_RECENT]:
        if tool_name in PRESERVE_RESULT_TOOLS:
            continue   # keep reference material
        part["content"] = f"[Previous: used {tool_name}]"  # replace with short placeholder
    return messages
```

### Step 3: Lever 2 -- Auto-Compact

When micro-compaction is not enough and the token count crosses a threshold, the harness takes a bigger step: it saves the full transcript to disk for recovery, asks the LLM to summarize the entire conversation, and then replaces all messages with that summary. The agent continues from the summary as if nothing happened.

```python
def auto_compact(messages: list) -> list:
    # Save transcript for recovery
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM summarizes
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],  # cap at 80K chars for the summary call
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
    ]
```

### Step 4: Lever 3 -- Manual Compact

The `compact` tool lets the model itself trigger summarization on demand. It uses exactly the same mechanism as auto-compact. The difference is who decides: auto-compact fires on a threshold, manual compact fires when the agent judges it is the right time to compress.

### Step 5: Integration in the Agent Loop

All four levers compose naturally inside the main loop:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Lever 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Lever 2
        response = client.messages.create(...)
        # ... tool execution with persisted-output ... # Lever 0
        if manual_compact:
            messages[:] = auto_compact(messages)       # Lever 3
```

Transcripts preserve full history on disk. Large outputs are saved to `.task_outputs/tool-results/`. Nothing is truly lost -- just moved out of active context.

## What Changed From s05

| Component         | Before (s05)     | After (s06)                |
|-------------------|------------------|----------------------------|
| Tools             | 5                | 5 (base + compact)         |
| Context mgmt      | None             | Four-lever compression     |
| Persisted-output  | None             | Large outputs -> disk + preview |
| Micro-compact     | None             | Old results -> placeholders|
| Auto-compact      | None             | Token threshold trigger    |
| Transcripts       | None             | Saved to .transcripts/     |

## Try It

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (watch micro-compact replace old results)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`

## What You've Mastered

At this point, you can:

- Explain why a long agent session degrades and eventually fails without compression
- Intercept oversized tool outputs before they enter the context window
- Silently replace stale tool results with lightweight placeholders each turn
- Trigger a full conversation summarization -- automatically on a threshold or manually via a tool call
- Preserve full transcripts on disk so nothing is permanently lost

## Stage 1 Complete

You now have a complete single-agent system. Starting from a bare API call in s01, you have built up tool use, structured planning, sub-agent delegation, dynamic skill loading, and context compression. Your agent can read, write, execute, plan, delegate, and work indefinitely without running out of memory. That is a real coding agent.

Before moving on, consider going back to s01 and rebuilding the whole stack from scratch without looking at the code. If you can write all six layers from memory, you truly own the ideas -- not just the implementation.

Stage 2 begins with s07 and hardens this foundation. You will add permission controls, hook systems, persistent memory, error recovery, and more. The single agent you built here becomes the kernel that everything else wraps around.

## Key Takeaway

> Compaction is not deleting history -- it is relocating detail so the agent can keep working.
