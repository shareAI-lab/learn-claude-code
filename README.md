[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md)

# Learn Claude Code

A teaching repository for implementers who want to build a high-completion coding-agent harness from scratch.

This repo does not try to mirror every product detail from a production codebase. It focuses on the mechanisms that actually decide whether an agent can work well:

- the loop
- tools
- planning
- delegation
- context control
- permissions
- hooks
- memory
- prompt assembly
- tasks
- teams
- isolated execution lanes
- external capability routing

The goal is simple:

**understand the real design backbone well enough that you can rebuild it yourself.**

## What This Repo Is Really Teaching

One sentence first:

**The model does the reasoning. The harness gives the model a working environment.**

That working environment is made of a few cooperating parts:

- `Agent Loop`: ask the model, run tools, append results, continue
- `Tools`: the agent's hands
- `Planning`: a small structure that keeps multi-step work from drifting
- `Context Management`: keep the active context small and coherent
- `Permissions`: do not let model intent turn into unsafe execution directly
- `Hooks`: extend behavior around the loop without rewriting the loop
- `Memory`: keep only durable facts that should survive sessions
- `Prompt Construction`: assemble the model input from stable rules and runtime state
- `Tasks / Teams / Worktree / MCP`: grow the single-agent core into a larger working platform

This is the teaching promise of the repo:

- teach the mainline in a clean order
- explain unfamiliar concepts before relying on them
- stay close to real system structure
- avoid drowning the learner in irrelevant product details

## What This Repo Deliberately Does Not Teach

This repo is not trying to preserve every detail that may exist in a real production system.

If a detail is not central to the agent's core operating model, it should not dominate the teaching line. That includes things like:

- packaging and release mechanics
- cross-platform compatibility layers
- enterprise policy glue
- telemetry and account wiring
- historical compatibility branches
- product-specific naming accidents

Those details may matter in production. They do not belong at the center of a 0-to-1 teaching path.

## Who This Is For

The assumed reader:

- knows basic Python
- understands functions, classes, lists, and dictionaries
- may be completely new to agent systems

So the repo tries to keep a few strong teaching rules:

- explain a concept before using it
- keep one concept fully explained in one main place
- start from "what it is", then "why it exists", then "how to implement it"
- avoid forcing beginners to assemble the system from scattered fragments

## Recommended Reading Order

The English docs are intended to stand on their own. The chapter order, bridge docs, and mechanism map are aligned across locales, so you can stay inside one language while following the main learning path.

- Overview: [`docs/en/s00-architecture-overview.md`](./docs/en/s00-architecture-overview.md)
- Code Reading Order: [`docs/en/s00f-code-reading-order.md`](./docs/en/s00f-code-reading-order.md)
- Glossary: [`docs/en/glossary.md`](./docs/en/glossary.md)
- Teaching Scope: [`docs/en/teaching-scope.md`](./docs/en/teaching-scope.md)
- Data Structures: [`docs/en/data-structures.md`](./docs/en/data-structures.md)

## If This Is Your First Visit, Start Here

Do not open random chapters first.

The safest path is:

1. Read [`docs/en/s00-architecture-overview.md`](./docs/en/s00-architecture-overview.md) for the full system map.
2. Read [`docs/en/s00d-chapter-order-rationale.md`](./docs/en/s00d-chapter-order-rationale.md) so the chapter order makes sense before you dive into mechanism detail.
3. Read [`docs/en/s00f-code-reading-order.md`](./docs/en/s00f-code-reading-order.md) so you know which local files to open first.
4. Follow the four stages in order: `s01-s06 -> s07-s11 -> s12-s14 -> s15-s19`.
5. After each stage, stop and rebuild the smallest version yourself before continuing.

If the middle and late chapters start to blur together, reset in this order:

1. [`docs/en/data-structures.md`](./docs/en/data-structures.md)
2. [`docs/en/entity-map.md`](./docs/en/entity-map.md)
3. the bridge docs closest to the chapter you are stuck on
4. then return to the chapter body

## Web Learning Interface

If you want a more visual way to understand the chapter order, stage boundaries, and chapter-to-chapter upgrades, run the built-in teaching site:

```sh
cd web
npm install
npm run dev
```

Then use these routes:

- `/en`: the English entry page for choosing a reading path
- `/en/timeline`: the cleanest view of the full mainline
- `/en/layers`: the four-stage boundary map
- `/en/compare`: adjacent-step comparison and jump diagnosis

For a first pass, start with `timeline`.  
If you are already in the middle and chapter boundaries are getting fuzzy, use `layers` and `compare` before you go deeper into source code.

### Bridge Docs

These are not extra main chapters. They are bridge documents that make the middle and late system easier to understand:

- Chapter order rationale: [`docs/en/s00d-chapter-order-rationale.md`](./docs/en/s00d-chapter-order-rationale.md)
- Code reading order: [`docs/en/s00f-code-reading-order.md`](./docs/en/s00f-code-reading-order.md)
- Reference module map: [`docs/en/s00e-reference-module-map.md`](./docs/en/s00e-reference-module-map.md)
- Query control plane: [`docs/en/s00a-query-control-plane.md`](./docs/en/s00a-query-control-plane.md)
- One request lifecycle: [`docs/en/s00b-one-request-lifecycle.md`](./docs/en/s00b-one-request-lifecycle.md)
- Query transition model: [`docs/en/s00c-query-transition-model.md`](./docs/en/s00c-query-transition-model.md)
- Tool control plane: [`docs/en/s02a-tool-control-plane.md`](./docs/en/s02a-tool-control-plane.md)
- Tool execution runtime: [`docs/en/s02b-tool-execution-runtime.md`](./docs/en/s02b-tool-execution-runtime.md)
- Message and prompt pipeline: [`docs/en/s10a-message-prompt-pipeline.md`](./docs/en/s10a-message-prompt-pipeline.md)
- Runtime task model: [`docs/en/s13a-runtime-task-model.md`](./docs/en/s13a-runtime-task-model.md)
- MCP capability layers: [`docs/en/s19a-mcp-capability-layers.md`](./docs/en/s19a-mcp-capability-layers.md)
- Team-task-lane model: [`docs/en/team-task-lane-model.md`](./docs/en/team-task-lane-model.md)
- Entity map: [`docs/en/entity-map.md`](./docs/en/entity-map.md)

### Four Stages

1. `s01-s06`: build a useful single-agent core
2. `s07-s11`: add safety, extension points, memory, prompt assembly, and recovery
3. `s12-s14`: turn temporary session planning into durable runtime work
4. `s15-s19`: move into teams, protocols, autonomy, isolated execution, and external capability routing

### Main Chapters

| Chapter | Topic | What you get |
|---|---|---|
| `s00` | Architecture Overview | the global map, key terms, and learning order |
| `s01` | Agent Loop | the smallest working agent loop |
| `s02` | Tool Use | a stable tool dispatch layer |
| `s03` | Todo / Planning | a visible session plan |
| `s04` | Subagent | fresh context per delegated subtask |
| `s05` | Skills | load specialized knowledge only when needed |
| `s06` | Context Compact | keep the active window small |
| `s07` | Permission System | a safety gate before execution |
| `s08` | Hook System | extension points around the loop |
| `s09` | Memory System | durable cross-session knowledge |
| `s10` | System Prompt | section-based prompt assembly |
| `s11` | Error Recovery | continuation and retry branches |
| `s12` | Task System | persistent task graph |
| `s13` | Background Tasks | non-blocking execution |
| `s14` | Cron Scheduler | time-based triggers |
| `s15` | Agent Teams | persistent teammates |
| `s16` | Team Protocols | shared coordination rules |
| `s17` | Autonomous Agents | self-claiming and self-resume |
| `s18` | Worktree Isolation | isolated execution lanes |
| `s19` | MCP & Plugin | external capability routing |

## Quick Start

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env
```

Then configure `ANTHROPIC_API_KEY` or a compatible endpoint in `.env`, and run:

```sh
python agents/s01_agent_loop.py
python agents/s18_worktree_task_isolation.py
python agents/s19_mcp_plugin.py
python agents/s_full.py
```

Suggested order:

1. Run `s01` and make sure the minimal loop really works.
2. Read `s00`, then move through `s01 -> s11` in order.
3. Only after the single-agent core plus its control plane feel stable, continue into `s12 -> s19`.
4. Read `s_full.py` last, after the mechanisms already make sense separately.

## How To Read Each Chapter

Each chapter is easier to absorb if you keep the same reading rhythm:

1. what problem appears without this mechanism
2. what the new concept means
3. what the smallest correct implementation looks like
4. where the state actually lives
5. how it plugs back into the loop
6. where to stop first, and what can wait until later

If you keep asking:

- "Is this core mainline or just a side detail?"
- "Where does this state actually live?"

go back to:

- [`docs/en/teaching-scope.md`](./docs/en/teaching-scope.md)
- [`docs/en/data-structures.md`](./docs/en/data-structures.md)
- [`docs/en/entity-map.md`](./docs/en/entity-map.md)

## Repository Structure

```text
learn-claude-code/
├── agents/              # runnable Python reference implementations per chapter
├── docs/zh/             # Chinese mainline docs
├── docs/en/             # English docs
├── docs/ja/             # Japanese docs
├── skills/              # skill files used in s05
├── web/                 # web teaching platform
└── requirements.txt
```

## Language Status

Chinese is still the canonical teaching line and the fastest-moving version.

- `zh`: most reviewed and most complete
- `en`: main chapters plus the major bridge docs are available
- `ja`: main chapters plus the major bridge docs are available

If you want the fullest and most frequently refined explanation path, use the Chinese docs first.

## End Goal

By the end of the repo, you should be able to answer these questions clearly:

- what is the minimum state a coding agent needs?
- why is `tool_result` the center of the loop?
- when should you use a subagent instead of stuffing more into one context?
- what problem do permissions, hooks, memory, prompt assembly, and tasks each solve?
- when should a single-agent system grow into tasks, teams, worktrees, and MCP?

If you can answer those questions clearly and build a similar system yourself, this repo has done its job.
