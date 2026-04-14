# s02a: Tool Control Plane

> **Deep Dive** -- Best read after s02 and before s07. It shows why tools become more than a simple lookup table.

### When to Read This

After you understand basic tool dispatch and before you add permissions.

---

> This bridge document answers another key question:
>
> **Why is a tool system more than a `tool_name -> handler` table?**

## Why This Document Exists

`s02` correctly teaches tool registration and dispatch first.

That is the right teaching move because you should first understand how the model turns intent into action.

But later the tool layer starts carrying much more responsibility:

- permission checks
- MCP routing
- notifications
- shared runtime state
- message access
- app state
- capability-specific restrictions

At that point, the tool layer is no longer just a function table.

It becomes a control plane (the coordination layer that decides *how* each tool call gets routed and executed, rather than performing the tool work itself).

## Terms First

### Tool control plane

The part of the system that decides **how** a tool call executes:

- where it runs
- whether it is allowed
- what state it can access
- whether it is native or external

### Execution context

The runtime environment visible to the tool:

- current working directory
- current permission mode
- current messages
- available MCP clients
- app state and notification channels

### Capability source

Not every tool comes from the same place. Common sources:

- native local tools
- MCP tools
- agent/team/task/worktree platform tools

## The Smallest Useful Mental Model

Think of the tool system as four layers:

```text
1. ToolSpec
   what the model sees

2. Tool Router
   where the request gets sent

3. ToolUseContext
   what environment the tool can access

4. Tool Result Envelope
   how the output returns to the main loop
```

The biggest step up is layer 3:

**high-completion systems are defined less by the dispatch table and more by the shared execution context.**

## Core Structures

### `ToolSpec`

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

### `ToolDispatchMap`

```python
handlers = {
    "read_file": read_file,
    "write_file": write_file,
    "bash": run_bash,
}
```

Necessary, but not sufficient.

### `ToolUseContext`

```python
tool_use_context = {
    "tools": handlers,
    "permission_context": {...},
    "mcp_clients": {},
    "messages": [...],
    "app_state": {...},
    "notifications": [],
    "cwd": "...",
}
```

The key point:

Tools stop receiving only input parameters.
They start receiving a shared runtime environment.

### `ToolResultEnvelope`

```python
result = {
    "ok": True,
    "content": "...",
    "is_error": False,
    "attachments": [],
}
```

This makes it easier to support:

- plain text output
- structured output
- error output
- attachment-like results

## Why `ToolUseContext` Eventually Becomes Necessary

Compare two systems.

### System A: dispatch map only

```python
output = handlers[tool_name](**tool_input)
```

Fine for a demo.

### System B: dispatch map plus execution context

```python
output = handlers[tool_name](tool_input, tool_use_context)
```

Closer to a real platform.

Why?

Because now:

- `bash` needs permissions
- `mcp__...` needs a client
- `agent` tools need execution environment setup
- `task_output` may need file writes plus notification write-back

## Minimal Implementation Path

### 1. Keep `ToolSpec` and handlers

Do not throw away the simple model.

### 2. Introduce one shared context object

```python
class ToolUseContext:
    def __init__(self):
        self.handlers = {}
        self.permission_context = {}
        self.mcp_clients = {}
        self.messages = []
        self.app_state = {}
        self.notifications = []
```

### 3. Let all handlers receive the context

```python
def run_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    handler = ctx.handlers[tool_name]
    return handler(tool_input, ctx)
```

### 4. Route by capability source

```python
def route_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    if tool_name.startswith("mcp__"):
        return run_mcp_tool(tool_name, tool_input, ctx)
    return run_native_tool(tool_name, tool_input, ctx)
```

## Key Takeaway

**A mature tool system is not just a name-to-function map. It is a shared execution plane that decides how model action intent becomes real work.**
