# s07: Permission System

`s01 > s02 > s03 > s04 > s05 > s06 > [ s07 ] > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- A four-stage permission pipeline that every tool call must pass through before execution
- Three permission modes that control how aggressively the agent auto-approves actions
- How deny and allow rules use pattern matching to create a first-match-wins policy
- Interactive approval with an "always" option that writes permanent allow rules at runtime

Your agent from s06 is capable and long-lived. It reads files, writes code, runs shell commands, delegates subtasks, and compresses its own context to keep going. But there is no safety catch. Every tool call the model proposes goes straight to execution. Ask it to delete a directory and it will -- no questions asked. Before you give this agent access to anything that matters, you need a gate between "the model wants to do X" and "the system actually does X."

## The Problem

Imagine your agent is helping refactor a codebase. It reads a few files, proposes some edits, and then decides to run `rm -rf /tmp/old_build` to clean up. Except the model hallucinated the path -- the real directory is your home folder. Or it decides to `sudo` something because the model has seen that pattern in training data. Without a permission layer, intent becomes execution instantly. There is no moment where the system can say "wait, that looks dangerous" or where you can say "no, do not do that." The agent needs a checkpoint -- a pipeline (a sequence of stages that every request passes through) between what the model asks for and what actually happens.

## The Solution

Every tool call now passes through a four-stage permission pipeline before execution. The stages run in order, and the first one that produces a definitive answer wins.

```
tool_call from LLM
     |
     v
[1. Deny rules]     -- blocklist: always block these
     |
     v
[2. Mode check]     -- plan mode? auto mode? default?
     |
     v
[3. Allow rules]    -- allowlist: always allow these
     |
     v
[4. Ask user]       -- interactive y/n/always prompt
     |
     v
execute (or reject)
```

## Read Together

- If you start blurring "the model proposed an action" with "the system actually executed an action," you might find it helpful to revisit [`s00a-query-control-plane.md`](./s00a-query-control-plane.md).
- If you are not yet clear on why tool requests should not drop straight into handlers, keeping [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) open beside this chapter may help.
- If `PermissionRule`, `PermissionDecision`, and `tool_result` start to collapse into one vague idea, [`data-structures.md`](./data-structures.md) can reset them.

## How It Works

**Step 1.** Define three permission modes. Each mode changes how the pipeline treats tool calls that do not match any explicit rule. "Default" mode is the safest -- it asks you about everything. "Plan" mode blocks all writes outright, useful when you want the agent to explore without touching anything. "Auto" mode lets reads through silently and only asks about writes, good for fast exploration.

| Mode | Behavior | Use Case |
|------|----------|----------|
| `default` | Ask user for every unmatched tool call | Normal interactive use |
| `plan` | Block all writes, allow reads | Planning/review mode |
| `auto` | Auto-allow reads, ask for writes | Fast exploration mode |

**Step 2.** Set up deny and allow rules with pattern matching. Rules are checked in order -- first match wins. Deny rules catch dangerous patterns that should never execute, regardless of mode. Allow rules let known-safe operations pass without asking.

```python
rules = [
    # Always deny dangerous patterns
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},
    {"tool": "bash", "content": "sudo *",   "behavior": "deny"},
    # Allow reading anything
    {"tool": "read_file", "path": "*", "behavior": "allow"},
]
```

When the user answers "always" at the interactive prompt, a permanent allow rule is added at runtime.

**Step 3.** Implement the four-stage check. This is the core of the permission system. Notice that deny rules run first and cannot be bypassed -- this is intentional. No matter what mode you are in or what allow rules exist, a deny rule always wins.

```python
def check(self, tool_name, tool_input):
    # Step 1: Deny rules (bypass-immune, always checked first)
    for rule in self.rules:
        if rule["behavior"] == "deny" and self._matches(rule, ...):
            return {"behavior": "deny", "reason": "..."}

    # Step 2: Mode-based decisions
    if self.mode == "plan" and tool_name in WRITE_TOOLS:
        return {"behavior": "deny", "reason": "Plan mode: writes blocked"}
    if self.mode == "auto" and tool_name in READ_ONLY_TOOLS:
        return {"behavior": "allow", "reason": "Auto: read-only approved"}

    # Step 3: Allow rules
    for rule in self.rules:
        if rule["behavior"] == "allow" and self._matches(rule, ...):
            return {"behavior": "allow", "reason": "..."}

    # Step 4: Fall through to ask user
    return {"behavior": "ask", "reason": "..."}
```

**Step 4.** Integrate the permission check into the agent loop. Every tool call now goes through the pipeline before execution. The result is one of three outcomes: denied (with a reason), allowed (silently), or asked (interactively).

```python
for block in response.content:
    if block.type == "tool_use":
        decision = perms.check(block.name, block.input)

        if decision["behavior"] == "deny":
            output = f"Permission denied: {decision['reason']}"
        elif decision["behavior"] == "ask":
            if perms.ask_user(block.name, block.input):
                output = handler(**block.input)
            else:
                output = "Permission denied by user"
        else:  # allow
            output = handler(**block.input)

        results.append({"type": "tool_result", ...})
```

**Step 5.** Add denial tracking as a simple circuit breaker. The `PermissionManager` tracks consecutive denials. After 3 in a row, it suggests switching to plan mode -- this prevents the agent from repeatedly hitting the same wall and wasting turns.

## What Changed From s06

| Component | Before (s06) | After (s07) |
|-----------|-------------|-------------|
| Safety | None | 4-stage permission pipeline |
| Modes | None | 3 modes: default, plan, auto |
| Rules | None | Deny/allow rules with pattern matching |
| User control | None | Interactive approval with "always" option |
| Denial tracking | None | Circuit breaker after 3 consecutive denials |

## Try It

```sh
cd learn-claude-code
python agents/s07_permission_system.py
```

1. Start in `default` mode -- every write tool asks for approval
2. Try `plan` mode -- all writes are blocked, reads pass through
3. Try `auto` mode -- reads auto-approved, writes still ask
4. Answer "always" to permanently allow a tool
5. Type `/mode plan` to switch modes at runtime
6. Type `/rules` to inspect current rule set

## What You've Mastered

At this point, you can:

- Explain why model intent must pass through a decision pipeline before it becomes execution
- Build a four-stage permission check: deny, mode, allow, ask
- Configure three permission modes that give you different safety/speed tradeoffs
- Add rules dynamically at runtime when a user answers "always"
- Implement a simple circuit breaker that catches repeated denial loops

## What's Next

Your permission system controls what the agent is allowed to do, but it lives entirely inside the agent's own code. What if you want to extend behavior -- add logging, auditing, or custom validation -- without modifying the agent loop at all? That is what s08 introduces: a hook system that lets external shell scripts observe and influence every tool call.

## Key Takeaway

> Safety is a pipeline, not a boolean -- deny first, then consider mode, then check allow rules, then ask the user.
