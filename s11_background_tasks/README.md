# s11: Background Tasks — Slow Operations Go to the Background

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s09 → s10 → `s11` → [s12](../s12_cron_scheduler/) → s13 → ... → s16 → s17

> *"Slow operations go to the background, the Agent Loop continues"* — Background threads run commands, and later turns collect completed results.
>
> **Harness Layer**: Background — Async execution, doesn't block the main loop.

---

## The Problem

Reading a file or running `git status` usually returns quickly, so synchronous execution causes little noticeable delay. Installing dependencies, running a full test suite, or building a project can take several minutes. Until the command returns, the Harness cannot process the next tool call in the current response or start the next model turn.

If later work does not depend on that command, there is no need to block it. For example, after starting a full test suite, the Agent could inspect documentation or organize other files while the tests run.

S11 addresses this by running slow Bash commands in the background, allowing the Agent Loop to continue and collect completed results on a later turn.

---

## The Solution

![Background Tasks Overview](images/background-tasks-overview.en.svg)

This chapter sends slow operations to background threads. The current tool call first returns a placeholder `tool_result`, allowing the Agent Loop to continue. At the start of a later turn, completed results are collected and added to the conversation as notifications.

Sync vs Background:

| | Sync (s04) | Background (s11) |
|---|---|---|
| Slow operations | Current tool call blocks | Background thread executes |
| Agent Loop | Waits for the command to return | Continues after the placeholder result |
| Result | Returned after the command finishes | Returns `bg_id` first; collects the result on a later turn |
| Decision criteria | — | bash `run_in_background` parameter |

---

## How It Works

### should_run_background: Explicit Request

The model requests background execution through the bash tool's `run_in_background` parameter. Only bash calls with the parameter explicitly set to `true` enter this path. Other calls still run synchronously.

```python
def should_run_background(tool_name: str, tool_input: dict) -> bool:
    return (
        tool_name == "bash"
        and tool_input.get("run_in_background") is True
    )
```

The Harness no longer guesses from keywords such as `install`, `build`, or `test`. The tool call chooses the execution mode explicitly.

### BackgroundManager: Background Execution and Lifecycle

`BackgroundManager` owns task state and the completion queue. `start()` registers a task, starts a daemon thread, and returns `bg_id` immediately:

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self.results = {}
        self._ready = []
        self._lock = threading.Lock()

    def start(self, block) -> str:
        # Register task, then run _run() in a daemon thread.
        ...

    def _run(self, task_id: str, command: str):
        output, exit_code = _run_bash_process(command)
        status = "completed" if exit_code == 0 else "failed"
        with self._lock:
            self.tasks[task_id]["status"] = status
            self.results[task_id] = _format_bash_result(output, exit_code)
            self._ready.append(task_id)
```

A non-zero exit code or worker exception becomes `failed`. The shell starts in its own process group. When the command finishes, times out, or the Agent exits through the normal or `SIGTERM` path, the runtime stops that original group. This is lifecycle cleanup, not a sandbox: a process that creates another session can leave the group.

### collect_background_results: Notification Collection

At the start of a later turn, `collect()` removes completed results from the queue and formats them as `<task_notification>` messages:

```python
def collect_background_results() -> list[str]:
    return BACKGROUND.collect()
```

Notifications don't reuse the original `tool_use_id`. The original tool call was already answered with a placeholder `tool_result`; when the completed result is collected, it is added as an independent event in `task_notification` format. One `tool_use` still gets exactly one `tool_result`.

### Loop Integration

Before each LLM call, the Agent Loop collects completed background results. `execute_tool()` still runs `PreToolUse` on the main thread before choosing synchronous or background execution:

```python
while True:
    inject_background_results(messages)
    response = client.messages.create(...)

def execute_tool(block) -> str:
    blocked = trigger_hooks("PreToolUse", block)
    if blocked is not None:
        return str(blocked)
    if should_run_background(block.name, block.input):
        task_id = start_background_task(block)
        output = f"[Background task {task_id} started]"
    else:
        output = call_tool(block)
    trigger_hooks("PostToolUse", block, output)
    return output
```

Slow operations first return a placeholder tool_result with `bg_id`. A completed task does not wake the Agent by itself; `inject_background_results()` collects it the next time the Agent Loop runs.

### Putting It Together

```
Turn 1:
  LLM → bash "npm install" (run_in_background=true)
  → start_background_task → bg_0001
  → tool_result: "[Background task bg_0001 started]..."
  → LLM: "OK, I'll check later. Let me also read the config."

Turn 2:
  LLM → read_file "package.json" (fast, sync)
  → tool_result: file content

Turn 3:
  → collect bg_0001 as <task_notification>
  → LLM sees: config file + install notification in one message
```

While npm install ran in the background, the Agent Loop continued with read_file.

---

## What s11 Adds

| Component | s04 Kernel | s11 |
|-----------|-------------|-------------|
| Execution model | All synchronous | Slow ops to background thread + notification injection |
| bash schema | `command` | `command` + `run_in_background` |
| New functions | — | `should_run_background`, `start_background_task`, `collect_background_results`, `inject_background_results` |
| New types | — | `BackgroundManager` |
| Notification format | — | `<task_notification>` (doesn't reuse tool_use_id) |
| Loop behavior | Tools execute synchronously | Explicit background execution, completed results collected on later turns |
| Tools | 5 | 5 (one parameter added to the bash schema) |

---

## Try It

```sh
cd learn-claude-code
python s11_background_tasks/code.py
```

Try these prompts:

1. `Run pip list in the background and find all Python files in this directory`
2. `Run npm install (use run_in_background) and while waiting, read package.json`
3. `Run a short sleep in the background, then list all Markdown files`

What to observe: After explicitly setting `run_in_background`, is the command dispatched to the background? Is a `bg_id` returned? Are completed results collected in `<task_notification>` format on a later turn?

---

## What's Next

Background tasks solved "slow operations don't block." But what if you want to do something on a schedule? Like "run tests every morning at 9am" or "check server status every 5 minutes."

s12 Cron Scheduler → Give the agent an alarm clock.


<!-- translation-sync: zh@v7, en@v7, ja@v7 -->
