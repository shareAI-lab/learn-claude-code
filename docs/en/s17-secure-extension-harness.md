# s17: Secure Extension Harness

`s02 > s13 > s14 | s15 | s16 > [ s17 ]`

> *"Production harnesses aren't about more features -- they're about clear responsibilities at every layer"*
>
> **Harness layer**: Security pipeline -- composing all defense layers into one execution path.

## Problem

s13-s16 each runs as a standalone agent. Real systems need all layers working together inside a single execution pipeline. The question: how do they compose without conflicting?

## Solution

```
    LLM calls tool
         |
         v
    +---------------------+
    | [1] Pre-tool Hook   | --block--> return error
    +----------+----------+
               v
    +---------------------+
    | [2] Classifier      | --deny---> return error
    +----------+----------+
               v
    +---------------------+
    | [3] Permission      | --deny---> return error
    |                     | --ask---> user confirm?
    +----------+----------+
               v
    +---------------------+
    | [4] Execute         |  built-in handler or MCP
    +----------+----------+
               v
    +---------------------+
    | [5] Post-tool Hook  |  observe / log
    +----------+----------+
               |
               v
         return result
```

Each layer answers exactly one question:

| Layer | Question | Source |
|-------|----------|--------|
| Hook | "Should this action be intercepted?" | s15 |
| Classifier | "What is this command's intent?" | s14 |
| Permission | "Is this intent allowed?" | s13 |
| Execute | "Run and return result" | s02 + s16 |

## How It Works

1. `execute_tool()` runs the 5-layer pipeline for every tool call.

```python
def execute_tool(tool_name, tool_input, context):
    # Layer 1: Pre-tool hook
    pre = HOOKS.fire("PreToolUse", {"tool": tool_name, "input": tool_input})
    if pre and pre.get("action") == "block":
        return f"Blocked by hook: {pre['reason']}"

    # Layer 2+3: Classifier + Permission (bash only)
    if tool_name == "bash":
        allowed, cmd, reason = GUARD.check(command)
        if not allowed:
            return f"Security denied: {reason}"

    # Layer 4: Execute
    handler = TOOL_HANDLERS.get(tool_name)
    output = handler(**tool_input) if handler else MCP.call(tool_name, tool_input)

    # Layer 5: Post-tool hook
    HOOKS.fire("PostToolUse", {"tool": tool_name, "output": output})
    return output
```

2. Each layer is independent -- remove any one and the others still work.

3. REPL commands: `/security`, `/hooks`, `/mcp`, `/audit`.

## What Changed From s16

| Component | Before (s13-s16 standalone) | After (s17) |
|-----------|----------------------------|-------------|
| Security pipeline | Each chapter runs alone | Unified `execute_tool` pipeline |
| Classifier | Standalone | Embedded in Hook -> Classify -> Permission flow |
| Hooks | Standalone | First and last layer of the pipeline |
| MCP | Standalone | Part of the Execute layer |

## Try It

```sh
cd learn-claude-code
python agents/s17_secure_extension_harness.py
```

1. `list all python files` (all layers pass -> allow)
2. `run rm -rf /` (classifier deny -> blocked)
3. `write a test file and show audit log` (PostToolUse hook logs -> `/audit`)
4. `search for 'PermissionGuard' via MCP` (MCP tool called through pipeline)
5. `register a hook that blocks all pip commands` (dynamic hook registration)
