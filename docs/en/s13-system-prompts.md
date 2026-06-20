# s13: System Prompts — Dynamic Environment-Aware Assembly

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ]`

> *"The prompt knows where it runs"* — OS, paths, shell, user, all injected at runtime.
>
> **Harness layer**: Prompt — assembled from real environment state, never hardcoded.

## Problem

A system prompt that says `"You are a coding agent at /home/user/project"` works on one machine. Move to another user, another OS, another shell — and the prompt lies. The agent then suggests commands that don't exist, paths that don't resolve, tools that aren't installed.

Hardcoding environment facts causes three failure modes:

1. **Wrong OS commands** — `ls` vs `dir`, `cat` vs `type`, `/usr/bin/python3` vs `C:\Python313\python.exe`
2. **Wrong paths** — `/home/alice` vs `C:\Users\alice`, `/tmp` vs `%TEMP%`
3. **Wrong shell semantics** — bash globbing, PowerShell cmdlets, cmd.exe quirks

The system prompt must reflect the *actual* runtime environment: which OS, which shell, which user, which paths exist, which tools are on PATH.

## Solution

```
Environment probing              System prompt assembly
+-----------------------+        +-----------------------------+
| OS / platform         |        | [identity]                  |
| Python version        | -----> | [environment]               |
| Working directory     |        | [tools_available]           |
| Home / temp paths     |        | [workspace]                 |
| Shell + env vars      |        | [safety_constraints]        |
| Tools on PATH         |        +-----------------------------+
| User / hostname       |                     |
+-----------------------+                     v
                                    Printed / sent to LLM
```

Six sections, two loading strategies:

| Section           | Strategy  | Content                                  | Source                     |
|-------------------|-----------|------------------------------------------|----------------------------|
| identity          | always    | who the agent is, how to behave          | static                     |
| environment       | always    | OS, Python, shell, user, host            | `platform`, `os`, `getpass`|
| tools_available   | always    | which tools exist on PATH                | `shutil.which`             |
| workspace         | always    | cwd, home, temp, project root            | `pathlib`, `os`            |
| safety_constraints| always    | path boundaries, dangerous commands      | static rules               |
| project_context   | on-demand | git branch, project files (if any)       | `subprocess`, `pathlib`    |

Key design: every fact in the prompt is *probed at runtime*, not typed by hand. The same script produces a correct prompt on Windows, macOS, and Linux without modification.

## How It Works

### 1. Probe the OS and platform

```python
import platform, os

def probe_os() -> dict:
    return {
        "system": platform.system(),        # Windows / Darwin / Linux
        "release": platform.release(),      # 10 / 23.4.0 / 5.15.0
        "machine": platform.machine(),      # AMD64 / arm64 / x86_64
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "is_windows": os.name == "nt",
        "is_macos": platform.system() == "Darwin",
        "is_linux": platform.system() == "Linux",
    }
```

### 2. Probe paths

```python
from pathlib import Path

def probe_paths() -> dict:
    return {
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
        "temp": str(Path(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")))),
        "python_executable": sys.executable,
    }
```

### 3. Probe the shell and user

```python
import getpass

def probe_user_shell() -> dict:
    return {
        "user": getpass.getuser(),
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC", "unknown"),
        "hostname": platform.node(),
    }
```

### 4. Probe available tools on PATH

```python
import shutil

def probe_tools() -> dict:
    candidates = ["git", "python", "python3", "node", "npm", "docker", "make", "curl"]
    return {name: shutil.which(name) for name in candidates if shutil.which(name)}
```

### 5. Assemble the system prompt

```python
def assemble_system_prompt(env: dict) -> str:
    sections = [
        IDENTITY,
        format_environment(env),
        format_tools(env["tools"]),
        format_workspace(env["paths"]),
        SAFETY_CONSTRAINTS,
    ]
    if env.get("project"):
        sections.append(format_project(env["project"]))
    return "\n\n".join(sections)
```

### 6. Cache by environment fingerprint

Re-probing every turn is wasteful. Hash the environment dict; re-assemble only when it changes.

```python
def get_system_prompt(env: dict) -> str:
    key = json.dumps(env, sort_keys=True, default=str)
    if key == _last_key and _last_prompt:
        return _last_prompt  # cache hit
    _last_key = key
    _last_prompt = assemble_system_prompt(env)
    return _last_prompt
```

## What Changed From s10

s10 introduced `PROMPT_SECTIONS` and `assemble_system_prompt(context)` but the context was minimal — just `enabled_tools`, `workspace`, and `memories`. The prompt still assumed a Unix-like environment.

| Aspect              | s10                          | s13                                  |
|---------------------|------------------------------|--------------------------------------|
| OS detection        | None                         | `platform.system()` + flags          |
| Path resolution     | Hardcoded `WORKDIR`          | `Path.cwd()`, `Path.home()`, `TEMP`  |
| Shell awareness     | None                         | `SHELL` / `COMSPEC` probed           |
| Tool availability   | Static list in `TOOLS`       | `shutil.which()` probes PATH         |
| User / host         | None                         | `getpass.getuser()`, `platform.node()`|
| Project context     | None                         | git branch + project files (optional)|
| Cache key           | `json.dumps(context)`        | `json.dumps(env)` (broader fingerprint)|

## Try It

```sh
cd learn-claude-code
python s13_system_prompt_manager.py
```

What to watch for:

1. The script prints each probed environment fact as it's gathered
2. The final assembled system prompt is printed in a fenced block
3. Running on Windows shows `system: Windows`, `shell: ...powershell...`
4. Running on macOS shows `system: Darwin`, `shell: /bin/zsh`
5. Re-running shows `[cache hit]` because the environment didn't change

Try these experiments:

1. `python s13_system_prompt_manager.py` — print the assembled prompt
2. `python s13_system_prompt_manager.py --json` — emit the env dict as JSON
3. `python s13_system_prompt_manager.py --raw` — print only the prompt, no decorations
4. Change directory (`cd /tmp && python .../s13_system_prompt_manager.py`) — watch the workspace section update

## Why This Matters

A system prompt that lies is worse than no system prompt. The agent trusts it. If it says `"Use bash"` on Windows, the agent runs `ls -la` and gets `CommandNotFoundException`. If it says `"Working directory: /home/user"` but cwd is actually `C:\Users\user`, every relative path the agent suggests is wrong.

Dynamic probing makes the prompt *honest*. The same code runs anywhere and produces a prompt that matches reality. This is the foundation for portable agents: ship one codebase, run on any OS, the prompt adapts itself.

## What's Next

The prompt now reflects the environment. But the agent still can't recover when a tool call fails — wrong path, missing file, permission denied. The next step is error recovery: catch, classify, retry with a fix.

<!-- translation-sync: en@v1 -->
