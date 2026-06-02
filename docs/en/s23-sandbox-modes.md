# s23: Sandbox Modes

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > [ s23 ]`

> *"Trust is earned, not given"* -- the harness classifies every command before running it.
>
> **Harness layer**: Sandbox enforcement -- command classification that gates execution by mode.

## Problem

By s22, the agent plans and executes in autopilot. But during autopilot, every command the model generates runs on the real machine. A "minor typo" in a git command can rebase history. A hallucinated file path can delete real data.

The harness needs a sandbox layer that classifies each command and decides: run it freely, run it in a container, ask first, or block entirely. This is the last line of defense before the agent touches the real system.

## Solution

```
Sandbox decision flow:

Model generates command
        |
        v
+---------------------+
| classify_command()  |
|                     |
| Returns: one of     |
| - safe              |
| - read-only         |
| - file-write        |
| - dangerous         |
+---------+-----------+
          |
          v
+------------------------------------------+
| Mode: unstrained                         |
|   safe        -> run                     |
|   read-only   -> run                     |
|   file-write  -> run                     |
|   dangerous   -> run (no restrictions)   |
+------------------------------------------+
| Mode: auto-sandbox                       |
|   safe        -> run                     |
|   read-only   -> run                     |
|   file-write  -> run                     |
|   dangerous   -> sandbox (Docker)        |
+------------------------------------------+
| Mode: confirmation                       |
|   safe        -> run                     |
|   read-only   -> run                     |
|   file-write  -> ask user               |
|   dangerous   -> block (always deny)     |
+------------------------------------------+
| Mode: locked                             |
|   safe        -> run                     |
|   read-only   -> run                     |
|   file-write  -> block                  |
|   dangerous   -> block                  |
+------------------------------------------+

Classification rules:
  safe:        git status, ls, cat, echo, python --version
  read-only:   grep, find, diff, head, wc, stat, ps
  file-write:  touch, cp, mv, install, write, npm install
  dangerous:   rm -rf, git push --force, chmod 777, sudo, curl|bash
```

## How It Works

1. **Classify the command.** Match against known patterns.

```python
COMMAND_CLS = {
    "safe": [
        r"^git status", r"^ls\b", r"^cat\b", r"^echo\b",
        r"^pwd\b", r"^python\s+--version", r"^printenv\b",
    ],
    "read-only": [
        r"^grep\b", r"^find\b", r"^diff\b", r"^head\b",
        r"^wc\b", r"^stat\b", r"^ps\b", r"^tail\b",
    ],
    "file-write": [
        r"^touch\b", r"^cp\b", r"^mv\b", r"npm install",
        r"pip install", r">[^>]", r">>", r"^tee\b",
    ],
    "dangerous": [
        r"rm\s+(-rf|-fr)", r"git push\s+--force",
        r"chmod\s+777", r"\bsudo\b", r"curl.*\|\s*bash",
        r"DROP\s+TABLE", r"format\s",
    ],
}

def classify_command(cmd: str) -> str:
    for cls, patterns in COMMAND_CLS.items():
        for pattern in patterns:
            if re.search(pattern, cmd):
                return cls
    return "file-write"  # default: assume writes
```

2. **Enforce the sandbox mode.** Check the classification against the current mode.

```python
SANDBOX_RULES = {
    "unstrained":     {"safe": "run", "read-only": "run", "file-write": "run", "dangerous": "run"},
    "auto-sandbox":   {"safe": "run", "read-only": "run", "file-write": "run", "dangerous": "sandbox"},
    "confirmation":   {"safe": "run", "read-only": "run", "file-write": "ask", "dangerous": "block"},
    "locked":         {"safe": "run", "read-only": "run", "file-write": "block", "dangerous": "block"},
}

def enforce_sandbox(cmd: str, mode: str) -> str:
    cls = classify_command(cmd)
    action = SANDBOX_RULES[mode][cls]

    if action == "run":
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elif action == "sandbox":
        return run_in_sandbox(cmd)
    elif action == "ask":
        return prompt_for_approval(cmd)
    elif action == "block":
        return f"Blocked: '{cmd}' is not allowed in '{mode}' sandbox"
```

3. **Run in sandbox.** Execute dangerous commands in a Docker container.

```python
def run_in_sandbox(cmd: str) -> str:
    result = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{os.getcwd()}:/work",
         "-w", "/work", "ubuntu:latest", "bash", "-c", cmd],
        capture_output=True, text=True, timeout=60
    )
    return f"[sandbox] {result.stdout}{result.stderr}"
```

4. **Set the mode.** Controlled by the user or auto-selected by context.

```python
def set_sandbox_mode(self, mode: str):
    valid = {"unstrained", "auto-sandbox", "confirmation", "locked"}
    if mode not in valid:
        raise ValueError(f"Invalid sandbox mode: {mode}")
    self.sandbox_mode = mode
    print(f"Sandbox mode set to: {mode}")
```

5. **Auto-select based on task.** Suggest a mode based on the request.

```python
def suggest_mode(self, task: str) -> str:
    if any(w in task.lower() for w in ["delete", "remove", "destroy", "drop"]):
        return "locked"
    elif any(w in task.lower() for w in ["install", "configure", "deploy"]):
        return "confirmation"
    elif any(w in task.lower() for w in ["explore", "review", "find", "search"]):
        return "unstrained"
    return "auto-sandbox"
```

## What Changed From s22

| Component       | Before (s22)              | After (s23)                       |
|-----------------|---------------------------|-----------------------------------|
| Command exec    | Run everything            | Classify + gate by sandbox mode   |
| Safety layers   | Approval policy only      | Approval + sandbox classification |
| Execution env   | Host machine              | Docker sandbox for dangerous cmds |
| Mode selection  | User-manual               | Auto-suggest based on task text   |
| Command classes | None                      | 4-tier classification (safe to dangerous) |

## Try It

```sh
cd learn-claude-code
python agents/s23_sandbox_modes.py
```

Try these:

1. Set `unstrained` mode -- run `rm -rf /tmp/test` (runs freely)
2. Set `auto-sandbox` mode -- run the same command (runs in Docker)
3. Set `confirmation` mode -- try writing a file (prompts for approval)
4. Set `locked` mode -- try writing or deleting (blocked with error)
5. Try `suggest_mode` with different task descriptions to see auto-selection
