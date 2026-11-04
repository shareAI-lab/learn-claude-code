# s04: Hooks — Hang on the Loop, Don't Write into It

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → s02 → s03 → `s04` → [s05](../s05_todo_write/) → s06 → ... → s16 → s17

> *"Hang on the loop, don't write into it"* — Hooks inject extension logic before and after tool execution.
>
> **Harness Layer**: Hooks — Extension points that don't invade the loop.

---

## The Problem

The s03 Agent has permission checks. But every new check, "log every bash call", "auto git add after writes", requires modifying the `agent_loop` function.

The loop quickly becomes this:

```python
def agent_loop(messages):
    while True:
        # ... LLM call ...
        for block in response.content:
            if block.type != "tool_use":
                continue
            log_to_file(block)          # added a line
            check_permission(block)     # added a line
            notify_slack(block)         # added another line
            output = execute(block)
            auto_git_add(block)         # yet another line
            # ... the loop is unrecognizable
```

What you want to extend is the Agent's behavior, but what you're modifying is the loop itself. The loop should be a stable core; extensions should hang on the outside.

---

## The Solution

![Hooks Overview](images/hooks-overview.en.svg)

The s03 loop and permission logic are fully preserved. The only change is moving `check_permission()` from inside the loop body onto a hook. The loop no longer directly calls any check function. Instead it calls `trigger_hooks("PreToolUse", block)`, and the registry decides what to run.

Four events, covering a complete agent cycle:

| Event | Trigger Timing | Typical Use |
|-------|---------------|-------------|
| UserPromptSubmit | After user input, before entering LLM | Input validation, context injection |
| PreToolUse | Before tool execution | Permission checks, logging |
| PostToolUse | After tool execution | Side effects (auto git add etc.), output checking |
| Stop | When the loop is about to exit | Cleanup, decide whether the loop continues |

Extensions are added via `register_hook()`. The loop only calls `trigger_hooks()`.

---

## How It Works

**Hook registry**: a dict mapping event names to callback lists.

```python
HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
}

def register_hook(event: str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:   # return value ≠ None → hook says "stop"
            return result
    return None
```

When `PreToolUse` returns non-None, the current tool execution is blocked. When `Stop` returns non-None, the loop continues. Return values from `UserPromptSubmit` and `PostToolUse` do not affect control flow.

**UserPromptSubmit** triggers after user input and before entering the LLM. The following hook records the current working directory:

```python
def context_inject_hook(query: str) -> str | None:
    """Inject current working directory info into every prompt."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None   # return None = no modification, let prompt through

register_hook("UserPromptSubmit", context_inject_hook)
```

In the main loop, triggered right after user input:

```python
query = input("s04 >> ")
trigger_hooks("UserPromptSubmit", query)   # ← before entering LLM
history.append({"role": "user", "content": query})
agent_loop(history)
```

**PreToolUse / PostToolUse**, hooks before and after tool execution. s03's permission check logic is now wrapped as a PreToolUse hook, plus a logging hook and a large-output reminder:

```python
# PreToolUse: permission check (s03 logic, moved from loop to hook)
def permission_hook(block):
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command", ""):
                return "Permission denied by deny list"
    if block.name in ("read_file", "write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    return None

# PreToolUse: logging
def log_hook(block):
    print(f"[HOOK] {block.name}(...)")

# PostToolUse: large output reminder
def large_output_hook(block, output):
    if len(str(output)) > 100000:
        print(f"[HOOK] ⚠ Large output from {block.name}")

register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
```

**Stop** triggers when the loop is about to exit. The following hook prints a cleanup summary:

```python
def summary_hook(messages: list) -> str | None:
    """Print a summary when the loop is about to stop."""
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None   # return None = allow stop, return string = force continuation

register_hook("Stop", summary_hook)
```

In agent_loop, triggered before exit:

```python
tool_calls = [
    block for block in response.content if block.type == "tool_use"
]
if not tool_calls:
    force = trigger_hooks("Stop", messages)   # ← before exiting
    if force:
        # hook returned a message → inject it and continue
        messages.append({"role": "user", "content": force})
        continue
    return
```

**Only one change in the loop**: s03 directly called `check_permission(block)`, s04 replaces it with `trigger_hooks("PreToolUse", block)`:

```python
for block in tool_calls:
    # s03: if not check_permission(block): ...
    # s04: hooks replace hardcoding
    blocked = trigger_hooks("PreToolUse", block)
    if blocked:
        results.append({"type": "tool_result", "tool_use_id": block.id,
                        "content": str(blocked)})
        continue

    handler = TOOL_HANDLERS.get(block.name)
    output = handler(**block.input) if handler else f"Unknown: {block.name}"

    trigger_hooks("PostToolUse", block, output)

    results.append({"type": "tool_result", "tool_use_id": block.id,
                    "content": output})
```

Four hooks cover the critical nodes of the agent cycle: input → before execution → after execution → exit. The loop only calls trigger_hooks(); all logic lives in hook callbacks.

---

## Changes from s03

| Component | Before (s03) | After (s04) |
|-----------|-------------|-------------|
| Extension method | check_permission() hardcoded in the loop | HOOKS registry + trigger_hooks() |
| New functions | — | register_hook, trigger_hooks |
| Hook callbacks | — | context_inject_hook, permission_hook, log_hook, large_output_hook, summary_hook |
| Loop | Directly calls check_permission() | Calls trigger_hooks("PreToolUse", ...) |
| Exit control | None | trigger_hooks("Stop", ...) can prevent exit |
| Input interception | None | trigger_hooks("UserPromptSubmit", ...) can inject context |

---

## Try It

```sh
cd learn-claude-code
python s04_hooks/code.py
```

Try these prompts:

1. `Read the file README.md` (should pass directly, observe hook logs)
2. `Create a file called test.txt` (after creation, observe if PostToolUse fires)
3. `Delete all temporary files in /tmp` (bash + rm triggers permission hook)

What to watch for: Before each tool execution, does the `[HOOK]` log appear? When permission is denied, was it intercepted by a hook or hardcoded in the loop?

---

## What's Next

The Agent can now safely execute operations. But does it ever stop to think "what should I do first, and what next?" Given a complex task, does it jump straight in, or plan first?

→ s05 TodoWrite: Give the Agent a planning tool. Make a list first, then execute.


<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
