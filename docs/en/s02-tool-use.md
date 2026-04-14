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
