# s20: Approval Policy

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > [ s20 ] > s21 > s22 > s23`

> *"Not all actions are equal -- some need a human to say yes"* -- control the blast radius of autonomous agents.
>
> **Harness layer**: Approval gates -- the harness decides which tool calls need human sign-off.

## Problem

By s19, the agent remembers things across sessions. But as autonomy grows, so does the risk. An agent that can run `rm -rf`, push to main, or deploy to production without asking is not efficient -- it's dangerous.

Blocking everything is equally bad. Asking the user to approve every `cat` and `ls` turns the agent into a puppet. The harness needs a policy layer that lets safe actions through and gates risky ones.

## Solution

```
Four policies, one lookup:

Model -> tool_use -> [ Approval Check ]
                            |
                            v
                    +--------------------+
                    | policy_lookup(cmd) |
                    +---------+----------+
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
        +----------+   +------------+   +-----------+
        |  full-   |   | on-request |   |  never    |
        |  auto    |   |            |   |           |
        +----------+   +------------+   +-----------+
              |               |               |
              v               v               v
           Always        Ask human       Block always
           allowed       if flagged      (return error)
                         |
                         v
                   +------------+
                   | auto-edit  |
                   | (mid-tier) |
                   +------------+
                         |
                edits OK, dangerous cmds -> ask
```

## How It Works

1. **Define the policy.** Each agent session gets an approval policy.

```python
APPROVAL_POLICIES = {
    "full-auto":   lambda cmd: "allow",
    "auto-edit":   lambda cmd: _auto_edit_check(cmd),
    "on-request":  lambda cmd: "ask",
    "never":       lambda cmd: "deny",
}
```

2. **Intercept before execution.** The approval check runs between the model and the shell.

```python
def execute_tool(self, tool_name: str, args: dict, policy: str) -> str:
    decision = APPROVAL_POLICIES[policy](args.get("command", ""))

    if decision == "allow":
        return self._run(tool_name, args)
    elif decision == "deny":
        return f"Error: '{tool_name}' is blocked by approval policy '{policy}'"
    elif decision == "ask":
        return self._prompt_for_approval(tool_name, args)
```

3. **Auto-edit policy.** Classify commands into safe and unsafe.

```python
DANGEROUS_PATTERNS = [
    "rm -rf", "git push --force", "drop table",
    "> /etc", "chmod 777", "curl.*| bash",
]

def _auto_edit_check(cmd: str) -> str:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return "ask"  # human gate
    return "allow"  # everything else passes
```

4. **On-request approval.** Pause the loop and wait for the user.

```python
def _prompt_for_approval(self, tool_name: str, args: dict) -> str:
    cmd = args.get("command", "")
    reply = input(f"[APPROVAL] Allow '{cmd}'? (y/n): ")
    if reply.lower() == "y":
        return self._run(tool_name, args)
    return f"Denied by user: '{cmd}'"
```

5. **Policy per tool.** Different tools can have different defaults.

```python
TOOL_POLICIES = {
    "bash":        "auto-edit",    # classify by command
    "file_write":  "full-auto",    # editing files is safe
    "git_push":    "on-request",  # always ask
    "delete_file": "auto-edit",   # block rm -rf patterns
}
```

## What Changed From s19

| Component       | Before (s19)         | After (s20)                      |
|-----------------|----------------------|----------------------------------|
| Tool execution  | Always allowed       | Policy-gated per tool            |
| Safety          | None                 | 4-level approval policy          |
| User interaction| Prompt-based only    | Approval gates mid-execution     |
| Command classif.| N/A                  | Pattern-based dangerous detection|
| Config          | Single mode          | Per-tool policy overrides        |

## Try It

```sh
cd learn-claude-code
python agents/s20_approval_policy.py
```

Try these:

1. Run with `full-auto` policy -- all commands execute without interruption
2. Switch to `auto-edit` -- safe commands pass, dangerous ones prompt
3. Set `on-request` -- every command requires approval
4. Set `never` -- all commands are blocked, see the error messages
5. Configure per-tool policies and test mixed behavior
