# Loop Engineering Agent

[中文](README.md) | English

An autonomous coding agent system built on the **Loop Engineering** methodology, inspired by Addy Osmani's approach and implemented using patterns from the learn-claude-code teaching repository (s01-s20).

## Core Concept

```
Agent = Model + Harness
```

- **Model**: Claude API for reasoning and code generation
- **Harness**: Seven-stage loop: Trigger → Discover → Allocate → Execute → Verify → Integrate → Persist

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REPL (main.py)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Plain text → s20.agent_loop() (26 tools available)      │   │
│  │  /loop <task> → orchestrator → maker/checker             │   │
│  │  /goal <cmd> → orchestrator.run_loop(goal)               │   │
│  │  /status /cron /quit                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     s20_comprehensive (base)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  agent_loop, assemble_system_prompt, update_context,     │   │
│  │  prepare_context, assemble_tool_pool, trigger_hooks,     │   │
│  │  scan_skills, list_skills, load_skill,                   │   │
│  │  consume_cron_queue, collect_background_results,         │   │
│  │  create_worktree                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API Key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 2. Run

```bash
# REPL mode (default) — interactive CLI with three modes
python loop-agent/main.py

# Single execution — Maker-Checker pipeline
python loop-agent/main.py --once

# Goal mode — loop until verification command succeeds
python loop-agent/main.py --goal "python -m pytest loop-agent/tests/"
```

### 3. REPL Commands

```bash
loop-agent >> /loop Fix login bug              # Maker-Checker pipeline
loop-agent >> /goal python -m pytest tests/    # Loop until tests pass
loop-agent >> /status                          # Show status
loop-agent >> cron: */5 * * * * check issues   # Add cron job
loop-agent >> What does this project do?       # Direct chat (full s20 capabilities)
loop-agent >> quit                             # Exit
```

## Seven-Stage Workflow

| Stage | Description | Module |
|-------|-------------|--------|
| **Trigger** | Four sources: Manual, Goal, Cron, CI/CD failure | `triggers.py` |
| **Discover** | Extract task items from triggers, filter processed | `task_discovery.py` |
| **Allocate** | Create Git Worktree for isolation | `loop_agent.py` (via s20) |
| **Execute** | Maker sub-agent implements code (read/write tools, 50 turns) | `loop_agent.py` |
| **Verify** | Checker sub-agent reviews code (read-only tools, 20 turns, structured JSON output) | `loop_agent.py` |
| **Integrate** | Approved → mark processed; Rejected → record feedback | `orchestrator.py` |
| **Persist** | Atomic state file write | `state.py` |

## Maker-Checker Pattern

```
Task ──→ Maker (read/write, 50 turns) ──→ diff + tests ──→ Checker (read-only, 20 turns)
                │                                            │
                │          ┌──── APPROVED ──────────────────┘
                │          ▼
                │     Mark processed
                │
                └──── REJECTED (with issues)
                       │
                       ▼
                  Retry (max 3 times, then escalate to human)
```

- **Maker**: Has `bash`, `read_file`, `write_file`, `edit_file`, `glob` tools
- **Checker**: Has `bash` (read-only), `read_file`, `glob` tools. Outputs structured JSON verdict.
- **Tool isolation**: Maker and Checker use independent tool sets without modifying global state (`_run_agent_with_tools`)
- **Token tracking**: Each cycle tracks API token consumption; optional `TOKEN_BUDGET` limit

## File Structure

```
loop-agent/
├── main.py              # Entry point (REPL/once/goal modes)
├── config.py            # Centralized config (paths, turn limits, token budget)
├── loop_agent.py        # s20 wrapper (chat, init_context, run_maker, run_checker)
├── orchestrator.py      # Seven-stage orchestrator
├── triggers.py          # Four trigger sources (Manual/Goal/Cron/CI)
├── task_discovery.py    # Task discovery and filtering
├── state.py             # File-based state management (atomic writes)
├── github_client.py     # Real GitHub API client (read-only)
├── github_mock.py       # GitHub API Mock (for local dev)
├── skills/              # Skill files
│   └── loop-engineering/SKILL.md
├── mock_data/           # Mock data
│   ├── issues.json
│   ├── ci_results.json
│   └── pr_template.json
├── state/               # State files
│   └── .loop-state.json
└── tests/               # Tests (77 passing)
    ├── test_state.py
    ├── test_triggers.py
    ├── test_github_mock.py
    ├── test_github_client.py
    ├── test_maker_checker.py
    ├── test_orchestrator.py
    ├── test_task_discovery.py
    └── test_config.py
```

## Patterns from learn-claude-code

| Pattern | Source | Application |
|---------|--------|-------------|
| `while stop_reason == "tool_use"` | s01 Agent Loop | `s20_comprehensive/code.py` |
| `TOOL_HANDLERS` dispatch table | s02 Tool Use | `s20_comprehensive/code.py` |
| Sub-agent fresh context | s06 Subagent | `s20_comprehensive/code.py` |
| Two-tier skill loading | s07 Skill Loading | `s20_comprehensive/code.py` |
| Atomic file state | s10 Memory | `state.py` |
| Cron scheduler | s14 Cron Scheduler | `s20_comprehensive/code.py` |
| Worktree naming | s18 Worktree | `s20_comprehensive/code.py` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Claude API Key |
| `ANTHROPIC_BASE_URL` | - | Custom API endpoint (optional) |
| `TOKEN_BUDGET` | `0` | Max API tokens per cycle (0 = unlimited) |
| `GITHUB_TOKEN` | - | GitHub Token (uses mock if empty) |
| `GITHUB_REPO` | `owner/repo` | Target repository |

## Run Tests

```bash
pytest loop-agent/tests/ -v
```

## License

MIT
