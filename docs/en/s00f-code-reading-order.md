# s00f: Code Reading Order

> **Deep Dive** -- Read this when you're about to open the Python agent files and want a strategy for reading them.

This page is not about reading more code. It answers a narrower question: once the chapter order is stable, what is the cleanest order for reading this repository's code without scrambling your mental model again?

## Conclusion First

Do not read the code like this:

- do not start with the longest file
- do not jump straight into the most "advanced" chapter
- do not open `web/` first and then guess the mainline
- do not treat all `agents/*.py` files like one flat source pool

The stable rule is simple:

**read the code in the same order as the curriculum.**

Inside each chapter file, keep the same reading order:

1. state structures
2. tool definitions or registries
3. the function that advances one turn
4. the CLI entry last

## Why This Page Exists

You will probably not get lost in the prose first. You will get lost when you finally open the code and immediately start scanning the wrong things.

Typical mistakes:

- staring at the bottom half of a long file first
- reading a pile of `run_*` helpers before knowing where they connect
- jumping into late platform chapters and treating early chapters as "too simple"
- collapsing `task`, `runtime task`, `teammate`, and `worktree` back into one vague idea

## Use The Same Reading Template For Every Agent File

For any `agents/sXX_*.py`, read in this order:

### 1. File header

Answer two questions before anything else:

- what is this chapter teaching
- what is it intentionally not teaching yet

### 2. State structures or manager classes

Look for things like:

- `LoopState`
- `PlanningState`
- `CompactState`
- `TaskManager`
- `BackgroundManager`
- `TeammateManager`
- `WorktreeManager`

### 3. Tool list or registry

Look for:

- `TOOLS`
- `TOOL_HANDLERS`
- `build_tool_pool()`
- the important `run_*` entrypoints

### 4. The turn-advancing function

Usually this is one of:

- `run_one_turn(...)`
- `agent_loop(...)`
- a chapter-specific `handle_*`

### 5. CLI entry last

`if __name__ == "__main__"` matters, but it should not be the first thing you study.

## Stage 1: `s01-s06`

This stage is the single-agent backbone taking shape.

| Chapter | File | Read First | Then Read | Confirm Before Moving On |
|---|---|---|---|---|
| `s01` | `agents/s01_agent_loop.py` | `LoopState` | `TOOLS` -> `execute_tool_calls()` -> `run_one_turn()` -> `agent_loop()` | You can trace `messages -> model -> tool_result -> next turn` |
| `s02` | `agents/s02_tool_use.py` | `safe_path()` | tool handlers -> `TOOL_HANDLERS` -> `agent_loop()` | You understand how tools grow without rewriting the loop |
| `s03` | `agents/s03_todo_write.py` | planning state types | todo handler path -> reminder injection -> `agent_loop()` | You understand visible session planning state |
| `s04` | `agents/s04_subagent.py` | `AgentTemplate` | `run_subagent()` -> parent `agent_loop()` | You understand that subagents are mainly context isolation |
| `s05` | `agents/s05_skill_loading.py` | skill registry types | registry methods -> `agent_loop()` | You understand discover light, load deep |
| `s06` | `agents/s06_context_compact.py` | `CompactState` | persist / micro compact / history compact -> `agent_loop()` | You understand that compaction relocates detail instead of deleting continuity |

## Stage 2: `s07-s11`

This stage hardens the control plane around a working single agent.

| Chapter | File | Read First | Then Read | Confirm Before Moving On |
|---|---|---|---|---|
| `s07` | `agents/s07_permission_system.py` | validator / manager | permission path -> `run_bash()` -> `agent_loop()` | You understand gate before execute |
| `s08` | `agents/s08_hook_system.py` | `HookManager` | hook registration and dispatch -> `agent_loop()` | You understand fixed extension points |
| `s09` | `agents/s09_memory_system.py` | memory managers | save path -> prompt build -> `agent_loop()` | You understand memory as a long-term information layer |
| `s10` | `agents/s10_system_prompt.py` | `SystemPromptBuilder` | reminder builder -> `agent_loop()` | You understand input assembly as a pipeline |
| `s11` | `agents/s11_error_recovery.py` | compact / backoff helpers | recovery branches -> `agent_loop()` | You understand continuation after failure |

## Stage 3: `s12-s14`

This stage turns the harness into a work runtime.

| Chapter | File | Read First | Then Read | Confirm Before Moving On |
|---|---|---|---|---|
| `s12` | `agents/s12_task_system.py` | `TaskManager` | task create / dependency / unlock -> `agent_loop()` | You understand durable work goals |
| `s13` | `agents/s13_background_tasks.py` | `NotificationQueue` / `BackgroundManager` | background registration -> notification drain -> `agent_loop()` | You understand runtime slots |
| `s14` | `agents/s14_cron_scheduler.py` | `CronLock` / `CronScheduler` | cron match -> trigger -> `agent_loop()` | You understand future start conditions |

## Stage 4: `s15-s19`

This stage is about platform boundaries.

| Chapter | File | Read First | Then Read | Confirm Before Moving On |
|---|---|---|---|---|
| `s15` | `agents/s15_agent_teams.py` | `MessageBus` / `TeammateManager` | roster / inbox / loop -> `agent_loop()` | You understand persistent teammates |
| `s16` | `agents/s16_team_protocols.py` | `RequestStore` / `TeammateManager` | request handlers -> `agent_loop()` | You understand request-response plus `request_id` |
| `s17` | `agents/s17_autonomous_agents.py` | claim and identity helpers | claim path -> resume path -> `agent_loop()` | You understand idle check -> safe claim -> resume work |
| `s18` | `agents/s18_worktree_task_isolation.py` | `TaskManager` / `WorktreeManager` / `EventBus` | worktree lifecycle -> `agent_loop()` | You understand goals versus execution lanes |
| `s19` | `agents/s19_mcp_plugin.py` | capability gate / MCP client / plugin loader / router | tool pool build -> route -> normalize -> `agent_loop()` | You understand how external capability enters the same control plane |

## Best Doc + Code Loop

For each chapter:

1. read the chapter prose
2. read the bridge note for that chapter
3. open the matching `agents/sXX_*.py`
4. follow the order: state -> tools -> turn driver -> CLI entry
5. run the demo once
6. rewrite the smallest version from scratch

## Key Takeaway

**Code reading order must obey teaching order: read boundaries first, then state, then the path that advances the loop.**
