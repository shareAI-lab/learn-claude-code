# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Learn Claude Code" teaches agent harness engineering through 12 progressive Python sessions (s01-s12), each adding one mechanism to a minimal agent loop. The repo has two independent parts:

- **Python agents** (`agents/`): Self-contained, runnable Python scripts that implement agent patterns from a single bash tool (s01) to worktree-isolated multi-agent teams (s12). Each session builds on the previous one. `s_full.py` combines all mechanisms from s01-s11 as a capstone reference.
- **Next.js web app** (`web/`): Interactive visualizations, documentation, and diff views for each session. Multi-language (en/ja/zh) with i18n.

## Commands

### Python Agents
```bash
# Install dependencies (project root)
pip install -r requirements.txt  # anthropic, python-dotenv, pyyaml

# Run a single session
python agents/s01_agent_loop.py

# Run all smoke tests (compile check + existence)
python -m pytest tests/ -q

# Run a specific test
python -m pytest tests/test_agents_smoke.py::test_agent_scripts_compile -q
```

### Web App
```bash
# Install dependencies (from web/)
cd web && npm ci

# Dev server (extracts docs first via predev hook)
cd web && npm run dev

# Production build
cd web && npm run build

# Type check
cd web && npx tsc --noEmit
```

### Environment
- Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` and `MODEL_ID` before running agent scripts.
- Optional: `ANTHROPIC_BASE_URL` for Anthropic-compatible providers.

## Session Progression

Sessions are numbered s01-s12 and each introduces exactly one harness concept:

| Session | Concept | Key File |
|---------|---------|----------|
| s01 | Agent loop (one tool) | `agents/s01_agent_loop.py` |
| s02 | Tool dispatch | `agents/s02_tool_use.py` |
| s03 | TodoWrite / planning | `agents/s03_todo_write.py` |
| s04 | Subagent isolation | `agents/s04_subagent.py` |
| s05 | On-demand skill loading | `agents/s05_skill_loading.py` |
| s06 | Context compression | `agents/s06_context_compact.py` |
| s07 | Task system | `agents/s07_task_system.py` |
| s08 | Background tasks | `agents/s08_background_tasks.py` |
| s09 | Agent teams | `agents/s09_agent_teams.py` |
| s10 | Team protocols | `agents/s10_team_protocols.py` |
| s11 | Autonomous agents | `agents/s11_autonomous_agents.py` |
| s12 | Worktree isolation | `agents/s12_worktree_task_isolation.py` |

Each Python file is self-contained (imports only stdlib + anthropic + dotenv) and runnable standalone. They don't import each other.

## Web App Architecture

- **Framework**: Next.js 16 (App Router), React 19, TailwindCSS 4, TypeScript
- **i18n**: Content is extracted from `docs/{en,ja,zh}/` by `scripts/extract-content.ts` (runs as predev/prebuild hook). The extracted data powers the themed rendering.
- **Visualizations**: `src/components/visualizations/` contains a stepped-animation component per session (e.g., `s01-agent-loop.tsx`), each independent and driven by `useSteppedVisualization` hook.
- **Page routing**: `[locale]/(learn)/[version]/` shows the main learning pages with diff views.
- **Data**: `src/types/agent-data.ts` defines the shared type schema; `src/data/execution-flows.ts` provides flow config data used across visualizations.
- **Deployment**: Vercel (see `web/vercel.json`).

## Skills Directory

`skills/` contains reusable agent skill definitions (agent-builder, code-review, mcp-builder, pdf). Each has a `SKILL.md` with references and optional scripts. These are teaching materials, not runtime dependencies.

## CI

Two workflows run on push/PR to main:
- `test.yml`: Python smoke tests (pytest) + web build
- `ci.yml`: Web type-check + build (Node 20)
