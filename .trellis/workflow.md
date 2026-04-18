# Development Workflow

> Based on [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

---

## Table of Contents

1. [Quick Start (Do This First)](#quick-start-do-this-first)
2. [Workflow Overview](#workflow-overview)
3. [Session Start Process](#session-start-process)
4. [Development Process](#development-process)
5. [Session End](#session-end)
6. [File Descriptions](#file-descriptions)
7. [Best Practices](#best-practices)

---

## Quick Start (Do This First)

### Step 0: Initialize Developer Identity (First Time Only)

> **Multi-developer support**: Each developer/Agent needs to initialize their identity first

```bash
# Check if already initialized
python3 ./.trellis/scripts/get_developer.py

# If not initialized, run:
python3 ./.trellis/scripts/init_developer.py <your-name>
# Example: python3 ./.trellis/scripts/init_developer.py cursor-agent
```

This creates:
- `.trellis/.developer` - Your identity file (gitignored, not committed)
- `.trellis/workspace/<your-name>/` - Your personal workspace directory

**Naming suggestions**:
- Human developers: Use your name, e.g., `john-doe`
- Cursor AI: `cursor-agent` or `cursor-<task>`
- Claude Code: `claude-agent` or `claude-<task>`
- iFlow cli: `iflow-agent` or `iflow-<task>`

### Step 1: Understand Current Context

```bash
# Get full context in one command
python3 ./.trellis/scripts/get_context.py

# Or check manually:
python3 ./.trellis/scripts/get_developer.py      # Your identity
python3 ./.trellis/scripts/task.py list          # Active tasks
git status && git log --oneline -10              # Git state
```

### Step 2: Read Project Guidelines [MANDATORY]

**CRITICAL**: Read guidelines before writing any code:

```bash
# Read frontend guidelines index (if applicable)
cat .trellis/spec/frontend/index.md

# Read backend guidelines index (if applicable)
cat .trellis/spec/backend/index.md
```

**Why read both?**
- Understand the full project architecture
- Know coding standards for the entire codebase
- See how frontend and backend interact
- Learn the overall code quality requirements

### Step 3: Before Coding - Read Specific Guidelines (Required)

Based on your task, read the **detailed** guidelines:

**Frontend Task**:
```bash
cat .trellis/spec/frontend/hook-guidelines.md      # For hooks
cat .trellis/spec/frontend/component-guidelines.md # For components
cat .trellis/spec/frontend/type-safety.md          # For types
```

**Backend Task**:
```bash
cat .trellis/spec/backend/database-guidelines.md   # For DB operations
cat .trellis/spec/backend/type-safety.md           # For types
cat .trellis/spec/backend/logging-guidelines.md    # For logging
cat .trellis/spec/backend/langchain-native-guidelines.md  # For LangChain/LangGraph work
```

**cc-haha Alignment Task**:
```bash
cat .trellis/spec/guides/cc-alignment-guide.md
```

**Architecture / Refactor Boundary Choice**:
```bash
cat .trellis/spec/guides/architecture-posture-guide.md
```

**Staged / Multi-Checkpoint Work**:
```bash
cat .trellis/spec/guides/staged-execution-guide.md
```

**Filling Trellis Specs By Interview**:
```bash
cat .trellis/spec/guides/trellis-doc-map-guide.md
cat .trellis/spec/guides/interview-driven-spec-expansion-guide.md
```

---

## Workflow Overview

### Core Principles

1. **Read Before Write** - Understand context before starting
2. **Follow Standards** - [!] **MUST read `.trellis/spec/` guidelines before coding**
3. **Incremental Development** - Complete one task at a time
4. **Record Promptly** - Update tracking files immediately after completion
5. **Document Limits** - [!] **Max 2000 lines per journal document**
6. **Prefer Clean Architecture Over Minimal Patch** - [!] When a cleaner long-term structure conflicts with smallest-diff compatibility work, follow `.trellis/spec/guides/architecture-posture-guide.md`

### Documentation Language Convention

- Narrative prose in Trellis docs may be written in **Simplified Chinese**.
- Keep commands, file paths, file names, task slugs, branch names, code identifiers, and JSON/YAML keys in **English**.
- Keep structured status values and checklist keywords in **English** when they are used for search, automation, or coordination.
- When precision matters, write the Chinese explanation first and retain the original English term alongside it.

### File System

```
.trellis/
|-- .developer           # Developer identity (gitignored)
|-- scripts/
|   |-- __init__.py          # Python package init
|   |-- common/              # Shared utilities (Python)
|   |   |-- __init__.py
|   |   |-- paths.py         # Path utilities
|   |   |-- developer.py     # Developer management
|   |   +-- git_context.py   # Git context implementation
|   |-- multi_agent/         # Multi-agent pipeline scripts
|   |   |-- __init__.py
|   |   |-- start.py         # Start worktree agent
|   |   |-- status.py        # Monitor agent status
|   |   |-- create_pr.py     # Create PR
|   |   +-- cleanup.py       # Cleanup worktree
|   |-- init_developer.py    # Initialize developer identity
|   |-- get_developer.py     # Get current developer name
|   |-- task.py              # Manage tasks
|   |-- get_context.py       # Get session context
|   +-- add_session.py       # One-click session recording
|-- workspace/           # Developer workspaces
|   |-- index.md         # Workspace index + Session template
|   +-- {developer}/     # Per-developer directories
|       |-- index.md     # Personal index (with @@@auto markers)
|       +-- journal-N.md # Journal files (sequential numbering)
|-- tasks/               # Task tracking
|   +-- {MM}-{DD}-{name}/
|       +-- task.json
|-- spec/                # [!] MUST READ before coding
|   |-- frontend/        # Frontend guidelines (if applicable)
|   |   |-- index.md               # Start here - guidelines index
|   |   +-- *.md                   # Topic-specific docs
|   |-- backend/         # Backend guidelines (if applicable)
|   |   |-- index.md               # Start here - guidelines index
|   |   +-- *.md                   # Topic-specific docs
|   +-- guides/          # Thinking guides
|       |-- index.md                      # Guides index
|       |-- cross-layer-thinking-guide.md # Pre-implementation checklist
|       +-- *.md                          # Other guides
+-- workflow.md             # This document
```

---

## Session Start Process

### Step 1: Get Session Context

Use the unified context script:

```bash
# Get all context in one command
python3 ./.trellis/scripts/get_context.py

# Or get JSON format
python3 ./.trellis/scripts/get_context.py --json
```

### Step 1A: Minimal Mainline Resume

When resuming the `coding-deepgent` mainline and you want the cheapest safe
resume path, read:

```bash
cat .trellis/project-handoff.md
```

Then refresh only lightweight live state:

```bash
git branch --show-current
git status -sb
gh pr view 220 --repo shareAI-lab/learn-claude-code --json number,title,url,isDraft,headRefName,baseRefName
```

### Step 2: Read Development Guidelines [!] REQUIRED

**[!] CRITICAL: MUST read guidelines before writing any code**

Based on what you'll develop, read the corresponding guidelines:

**Frontend Development** (if applicable):
```bash
# Read index first, then specific docs based on task
cat .trellis/spec/frontend/index.md
```

**Backend Development** (if applicable):
```bash
# Read index first, then specific docs based on task
cat .trellis/spec/backend/index.md
```

**Cross-Layer Features**:
```bash
# For features spanning multiple layers
cat .trellis/spec/guides/cross-layer-thinking-guide.md
```

**Architecture / Refactor Choice**:
```bash
# When clean long-term structure competes with compatibility/minimal-diff patches
cat .trellis/spec/guides/architecture-posture-guide.md
```

### Step 3: Select Task to Develop

Use the task management script:

```bash
# List active tasks
python3 ./.trellis/scripts/task.py list

# Create new task (creates directory with task.json)
python3 ./.trellis/scripts/task.py create "<title>" --slug <task-name>
```

---

## Development Process

### Task Development Flow

```
1. Create or select task
   --> python3 ./.trellis/scripts/task.py create "<title>" --slug <name> or list

2. Write code according to guidelines
   --> Read .trellis/spec/ docs relevant to your task
   --> For cross-layer: read .trellis/spec/guides/
   --> For cc-haha-targeted behavior: read .trellis/spec/guides/cc-alignment-guide.md
   --> For staged work: read .trellis/spec/guides/staged-execution-guide.md
   --> For missing project conventions: read .trellis/spec/guides/interview-driven-spec-expansion-guide.md

3. Self-test
   --> Run project's lint/test commands (see spec docs)
   --> Manual feature testing

4. Commit code
   --> AI may commit autonomously after validation passes
   --> git add <scoped files>
   --> git commit -m "type(scope): description"
       Format: feat/fix/docs/refactor/test/chore

5. Record session (one command)
   --> python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
```

### Task Archive Policy

Archive a Trellis task after the work is actually complete:

- code/docs changes are tested as appropriate
- acceptance criteria are met
- the work has been committed, or the task is explicitly docs/planning-only and complete

Do not keep a task active only because `task.json` still says `planning` or
`in_progress`.

Use:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

For completed sessions, preserve the result with `$record-session`.

### Code Quality Checklist

**Must pass before commit**:
- [OK] Lint checks pass (project-specific command)
- [OK] Type checks pass (if applicable)
- [OK] Manual feature testing passes

**Project-specific checks**:
- See `.trellis/spec/frontend/quality-guidelines.md` for frontend
- See `.trellis/spec/backend/quality-guidelines.md` for backend

### Staged Work Protocol

For staged product work, Trellis should own the protocol directly:

- default to `lean` mode unless the user explicitly asks for a broader long-run pass
- for high-value, strongly coupled feature families with a clear boundary,
  prefer one integrated delivery pass with internal checkpoints rather than
  artificially tiny visible increments
- use sub-stage states:
  - `planning`
  - `implementing`
  - `verifying`
  - `checkpoint`
  - `terminal`
- after every sub-stage, choose exactly one checkpoint decision:
  - `continue`
  - `adjust`
  - `split`
  - `stop`
- if the decision is `continue`, move to the next sub-stage immediately
- in `lean` mode, keep validation focused unless cross-cutting risk requires more
- only split or stop a strongly coupled feature family when a real blocker,
  boundary change, or verification failure appears

Read `.trellis/spec/guides/staged-execution-guide.md` for the full checkpoint template and stop conditions.

### Interview-Driven Spec Expansion

When Trellis docs need missing project knowledge:

1. Read `.trellis/spec/guides/trellis-doc-map-guide.md`.
2. Read `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`.
3. Derive what can be learned from code, tests, PRDs, and current specs first.
4. Choose the owning Trellis document before asking.
5. Ask one targeted maintainer question.
6. Write the answer into the owning document immediately.
7. Record the interview note in the active task PRD.

Do not collect a broad chat transcript and reorganize it later.

Active task PRDs are the working record for requirements, interviews,
checkpoints, and verification while work is in progress. Workspace journals are
the completed-session record after validated work is committed and recorded via
`record-session`.

If the maintainer delegates future low-risk process choices to the agent,
proceed with the documented recommended/default option. Still stop for
irreversible deletion, major product direction changes, or unclear ownership.

### Spec Update Trigger

Update `.trellis/spec/*` only when a change creates or changes a reusable
implementation contract, such as:

- tool schema / command / API shape
- runtime state fields or payload formats
- module ownership or boundary
- validation / error behavior
- test requirements or verification matrix
- cross-layer transformation
- recurring mistake that should become a rule

Do not update specs for ordinary implementation details that do not affect
future implementation or review.

---

## Session End

### One-Click Session Recording

After code is committed, use:

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"
```

This automatically:
1. Detects current journal file
2. Creates new file if 2000-line limit exceeded
3. Appends session content
4. Updates index.md (sessions count, history table)

### Pre-end Checklist

Use `/trellis:finish-work` command to run through:
1. [OK] All code committed, commit message follows convention
2. [OK] Session recorded via `add_session.py`
3. [OK] No lint/test errors
4. [OK] Working directory clean (or WIP noted)
5. [OK] Spec docs updated if needed

---

## File Descriptions

### 1. workspace/ - Developer Workspaces

**Purpose**: Record each AI Agent session's work content

**Structure** (Multi-developer support):
```
workspace/
|-- index.md              # Main index (Active Developers table)
+-- {developer}/          # Per-developer directory
    |-- index.md          # Personal index (with @@@auto markers)
    +-- journal-N.md      # Journal files (sequential: 1, 2, 3...)
```

**When to update**:
- [OK] End of each session
- [OK] Complete important task
- [OK] Fix important bug

### 2. spec/ - Development Guidelines

**Purpose**: Documented standards for consistent development

**Structure** (Multi-doc format):
```
spec/
|-- frontend/           # Frontend docs (if applicable)
|   |-- index.md        # Start here
|   +-- *.md            # Topic-specific docs
|-- backend/            # Backend docs (if applicable)
|   |-- index.md        # Start here
|   +-- *.md            # Topic-specific docs
+-- guides/             # Thinking guides
    |-- index.md        # Start here
    +-- *.md            # Guide-specific docs
```

**When to update**:
- [OK] New pattern discovered
- [OK] Bug fixed that reveals missing guidance
- [OK] New convention established

### 3. Tasks - Task Tracking

Each task is a directory containing `task.json`:

```
tasks/
|-- 01-21-my-task/
|   +-- task.json
+-- archive/
    +-- 2026-01/
        +-- 01-15-old-task/
            +-- task.json
```

**Commands**:
```bash
python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>]   # Create task directory
python3 ./.trellis/scripts/task.py archive <name>  # Archive to archive/{year-month}/
python3 ./.trellis/scripts/task.py list            # List active tasks
python3 ./.trellis/scripts/task.py list-archive    # List archived tasks
```

---

## Best Practices

### [OK] DO - Should Do

1. **Before session start**:
   - Run `python3 ./.trellis/scripts/get_context.py` for full context
   - [!] **MUST read** relevant `.trellis/spec/` docs

2. **During development**:
   - [!] **Follow** `.trellis/spec/` guidelines
   - For cross-layer features, use `/trellis:check-cross-layer`
   - For runtime/refactor/contract decisions, prefer the higher-value long-term structure rather than the smallest patch
   - Develop only one task at a time
   - Run lint and tests frequently

3. **After development complete**:
   - Use `/trellis:finish-work` for completion checklist
   - After fix bug, use `/trellis:break-loop` for deep analysis
   - AI commits autonomously after the required checks pass
   - Use `add_session.py` to record progress

### [X] DON'T - Should Not Do

1. [!] **Don't** skip reading `.trellis/spec/` guidelines
2. [!] **Don't** let journal single file exceed 2000 lines
3. **Don't** develop multiple unrelated tasks simultaneously
4. **Don't** commit code with lint/test errors
5. **Don't** forget to update spec docs after learning something
6. [!] **Don't** amend commits, use destructive git commands, or commit
   unrelated user changes without explicit approval
7. [!] **Don't** add compatibility bridges, fallback paths, or duplicate abstractions only to preserve weaker old local designs unless a real external compatibility requirement exists

---

## Quick Reference

### Must-read Before Development

| Task Type | Must-read Document |
|-----------|-------------------|
| Frontend work | `frontend/index.md` → relevant docs |
| Backend work | `backend/index.md` → relevant docs, plus `backend/langchain-native-guidelines.md` when LangChain/LangGraph surfaces change |
| Cross-Layer Feature | `guides/cross-layer-thinking-guide.md` |
| Architecture / Refactor boundary choice | `guides/architecture-posture-guide.md` |
| cc-haha-aligned work | `guides/cc-alignment-guide.md` |
| Staged / checkpointed execution | `guides/staged-execution-guide.md` |
| Interview-driven spec expansion | `guides/trellis-doc-map-guide.md` → `guides/interview-driven-spec-expansion-guide.md` |

### Commit Convention

```bash
git commit -m "type(scope): description"
```

**Type**: feat, fix, docs, refactor, test, chore
**Scope**: Module name (e.g., auth, api, ui)

### Common Commands

```bash
# Session management
python3 ./.trellis/scripts/get_context.py    # Get full context
python3 ./.trellis/scripts/add_session.py    # Record session

# Task management
python3 ./.trellis/scripts/task.py list      # List tasks
python3 ./.trellis/scripts/task.py create "<title>" # Create task

# Slash commands
/trellis:finish-work          # Pre-commit checklist
/trellis:break-loop           # Post-debug analysis
/trellis:check-cross-layer    # Cross-layer verification
```

---

## Summary

Following this workflow ensures:
- [OK] Continuity across multiple sessions
- [OK] Consistent code quality
- [OK] Trackable progress
- [OK] Knowledge accumulation in spec docs
- [OK] Transparent team collaboration

**Core Philosophy**: Read before write, follow standards, record promptly, capture learnings
