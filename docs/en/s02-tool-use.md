# s02: Tool Use

`s01 > [ s02 ] > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- How to build a dispatch map (a routing table that maps tool names to handler functions)
- How path sandboxing prevents the model from escaping its workspace
- How to add new tools without touching the agent loop

If you ran the s01 agent for more than a few minutes, you probably noticed the cracks. `cat` silently truncates long files. `sed` chokes on special characters. Every bash command is an open door -- nothing stops the model from running `rm -rf /` or reading your SSH keys. You need dedicated tools with guardrails, and you need a clean way to add them.

## The Problem

With only `bash`, the agent shells out for everything. There is no way to limit what it reads, where it writes, or how much output it returns. A single bad command can corrupt files, leak secrets, or blow past your token budget with a massive stdout dump. What you really want is a small set of purpose-built tools -- `read_file`, `write_file`, `edit_file` -- each with its own safety checks. The question is: how do you wire them in without rewriting the loop every time?

## The Solution

The answer is a dispatch map -- one dictionary that routes tool names to handler functions. Adding a tool means adding one entry. The loop itself never changes.

```
+--------+      +-------+      +------------------+
|  User  | ---> |  LLM  | ---> | Tool Dispatch    |
| prompt |      |       |      | {                |
+--------+      +---+---+      |   bash: run_bash |
                    ^           |   read: run_read |
                    |           |   write: run_wr  |
                    +-----------+   edit: run_edit |
                    tool_result | }                |
                                +------------------+

The dispatch map is a dict: {tool_name: handler_function}.
One lookup replaces any if/elif chain.
```

## How It Works

**Step 1.** Each tool gets a handler function. Path sandboxing prevents the model from escaping the workspace -- every requested path is resolved and checked against the working directory before any I/O happens.

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    if limit and limit < len(lines):
        lines = lines[:limit]
    return "\n".join(lines)[:50000]  # hard cap to avoid blowing up the context
```

**Step 2.** The dispatch map links tool names to handlers. This is the entire routing layer -- no if/elif chain, no class hierarchy, just a dictionary.

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

**Step 3.** In the loop, look up the handler by name. The loop body itself is unchanged from s01 -- only the dispatch line is new.

```python
for block in response.content:
    if block.type == "tool_use":
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Unknown tool: {block.name}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

Add a tool = add a handler + add a schema entry. The loop never changes.

## What Changed From s01

| Component      | Before (s01)       | After (s02)                |
|----------------|--------------------|----------------------------|
| Tools          | 1 (bash only)      | 4 (bash, read, write, edit)|
| Dispatch       | Hardcoded bash call | `TOOL_HANDLERS` dict       |
| Path safety    | None               | `safe_path()` sandbox      |
| Agent loop     | Unchanged          | Unchanged                  |

## Try It

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`

## If You Start Feeling Tools Are More Than a Handler Map

Up to this point, the teaching path deliberately presents tools as:

- schema
- handler
- `tool_result`

That is the right way to learn it first.

But once the system grows, the tool layer quickly starts accumulating more:

- permission context
- current messages and app state
- MCP clients
- file read caches
- notifications and query tracking

In a more complete system, the tool layer eventually looks more like a small
"tool control plane" than a simple dispatch table.

Do not let that distract from the main line of this chapter. Master this layer
first, then continue to:

- [s02a-tool-control-plane.md](./s02a-tool-control-plane.md)

## Message Normalization

In the teaching version, the internal `messages` list is sent directly to the
API. What you see is what gets sent. But as the system becomes more complex
(tool timeouts, user cancellation, compaction/replacement), the internal
message list can drift into shapes the API will reject. Before each API call,
you need one normalization pass.

### Why It Matters

The API protocol has three hard constraints:

1. Every `tool_use` block must have a matching `tool_result` block linked by
   `tool_use_id`.
2. `user` and `assistant` messages must strictly alternate.
3. Only protocol-defined fields are accepted. Internal metadata will trigger
   400 errors.

### Implementation

```python
def normalize_messages(messages: list) -> list:
    """Normalize the internal message list into API-acceptable format."""
    cleaned = []

    for msg in messages:
        # Step 1: strip internal-only metadata fields
        clean = {"role": msg["role"]}
        if isinstance(msg.get("content"), str):
            clean["content"] = msg["content"]
        elif isinstance(msg.get("content"), list):
            clean["content"] = [
                {k: v for k, v in block.items()
                 if not k.startswith("_")}
                for block in msg["content"]
                if isinstance(block, dict)
            ]
        else:
            clean["content"] = msg.get("content", "")
        cleaned.append(clean)

    # Step 2: repair missing tool_result pairs
    existing_results = set()
    for msg in cleaned:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    existing_results.add(block.get("tool_use_id"))

    repaired = []
    for msg in cleaned:
        repaired.append(msg)

        if msg["role"] != "assistant" or not isinstance(msg.get("content"), list):
            continue

        missing_results = []
        for block in msg["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("id") not in existing_results:
                missing_results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": "(cancelled)",
                })

        if missing_results:
            repaired.append({"role": "user", "content": missing_results})

    cleaned = repaired

    # Step 3: merge consecutive same-role messages
    if not cleaned:
        return cleaned

    merged = [cleaned[0]]
    for msg in cleaned[1:]:
        if msg["role"] == merged[-1]["role"]:
            prev = merged[-1]
            prev_content = prev["content"] if isinstance(prev["content"], list) \
                else [{"type": "text", "text": str(prev["content"])}]
            curr_content = msg["content"] if isinstance(msg["content"], list) \
                else [{"type": "text", "text": str(msg["content"])}]
            prev["content"] = prev_content + curr_content
        else:
            merged.append(msg)

    return merged
```

Run it before every API call in the agent loop:

```python
response = client.messages.create(
    model=MODEL, system=system,
    messages=normalize_messages(messages),
    tools=TOOLS, max_tokens=8000,
)
```

**Key insight**: the in-memory `messages` list is the system's internal
representation. The API sees a normalized copy, not the raw internal list.

## What You've Mastered

At this point, you can:

- Wire any new tool into the agent by adding one handler and one schema entry -- without touching the loop.
- Enforce path sandboxing so the model cannot read or write outside its workspace.
- Explain why a dispatch map scales better than an if/elif chain.

Keep the boundary clean: a tool schema is enough for now. You do not need policy layers, approval UIs, or plugin ecosystems yet. If you can add one new tool without rewriting the loop, you have the core pattern down.

## What's Next

Your agent can now read, write, and edit files safely. But what happens when you ask it to do a 10-step refactoring? It finishes steps 1 through 3 and then starts improvising because it forgot the rest. In s03, you will give the agent a session plan -- a structured todo list that keeps it on track through complex, multi-step tasks.

## Key Takeaway

> The loop should not care how a tool works internally. It only needs a reliable route from tool name to handler.
