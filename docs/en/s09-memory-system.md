# s09: Memory System

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > [ s09 ] > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- Four memory categories that cover what is worth remembering: user preferences, feedback, project facts, and references
- How YAML frontmatter files give each memory record a name, type, and description
- What should NOT go into memory -- and why getting this boundary wrong is the most common mistake
- The difference between memory, tasks, plans, and CLAUDE.md

Your agent from s08 is powerful and extensible. It can execute tools safely, be extended through hooks, and work for long sessions thanks to context compression. But it has amnesia. Every time you start a new session, the agent meets you for the first time. It does not remember that you prefer pnpm over npm, that you told it three times to stop modifying test snapshots, or that the legacy directory cannot be deleted because deployment depends on it. You end up repeating yourself every session. The fix is a small, durable memory store -- not a dump of everything the agent has seen, but a curated set of facts that should still matter next time.

## The Problem

Without memory, a new session starts from zero. The agent keeps forgetting things like long-term user preferences, corrections you have repeated multiple times, project constraints that are not obvious from the code itself, and external references the project depends on. The result is an agent that always feels like it is meeting you for the first time. You waste time re-establishing context that should have been saved once and loaded automatically.

## The Solution

A small file-based memory store saves durable facts as individual markdown files with YAML frontmatter (a metadata block at the top of each file, delimited by `---` lines). At the start of each session, relevant memories are loaded and injected into the model's context.

```text
conversation
   |
   | durable fact appears
   v
save_memory
   |
   v
.memory/
  ├── MEMORY.md
  ├── prefer_pnpm.md
  ├── ask_before_codegen.md
  └── incident_dashboard.md
   |
   v
next session loads relevant entries
```

## Read Together

- If you still think memory is just "a longer context window," you might find it helpful to revisit [`s06-context-compact.md`](./s06-context-compact.md) and re-separate compaction from durable memory.
- If `messages[]`, summary blocks, and the memory store start to blend together, keeping [`data-structures.md`](./data-structures.md) open while reading can help.
- If you are about to continue into s10, reading [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) alongside this chapter is useful because memory matters most when it re-enters the next model input.

## How It Works

**Step 1.** Define four memory categories. These are the types of facts worth keeping across sessions. Each category has a clear purpose -- if a fact does not fit one of these, it probably should not be in memory.

### 1. `user` -- Stable user preferences

Examples: prefers `pnpm`, wants concise answers, dislikes large refactors without a plan.

### 2. `feedback` -- Corrections the user wants enforced

Examples: "do not change test snapshots unless I ask", "ask before modifying generated files."

### 3. `project` -- Durable project facts not obvious from the repo

Examples: "this old directory still cannot be deleted because deployment depends on it", "this service exists because of a compliance requirement, not technical preference."

### 4. `reference` -- Pointers to external resources

Examples: incident board URL, monitoring dashboard location, spec document location.

```python
MEMORY_TYPES = ("user", "feedback", "project", "reference")
```

**Step 2.** Save one record per file using frontmatter. Each memory is a markdown file with YAML frontmatter that tells the system what the memory is called, what kind it is, and what it is roughly about.

```md
---
name: prefer_pnpm
description: User prefers pnpm over npm
type: user
---
The user explicitly prefers pnpm for package management commands.
```

```python
def save_memory(name, description, mem_type, content):
    path = memory_dir / f"{slugify(name)}.md"
    path.write_text(render_frontmatter(name, description, mem_type) + content)
    rebuild_index()
```

**Step 3.** Build a small index so the system knows what memories exist without reading every file.

```md
# Memory Index

- prefer_pnpm [user]
- ask_before_codegen [feedback]
- incident_dashboard [reference]
```

The index is not the memory itself -- it is a quick map of what exists.

**Step 4.** Load relevant memory at session start and turn it into a prompt section. Memory becomes useful only when it is fed back into the model input. This is why s09 naturally connects into s10.

```python
memories = memory_store.load_all()
```

**Step 5.** Know what should NOT go into memory. This boundary is the most important part of the chapter, and the place where most beginners go wrong.

| Do not store | Why |
|---|---|
| file tree layout | can be re-read from the repo |
| function names and signatures | code is the source of truth |
| current task status | belongs to task / plan, not memory |
| temporary branch names or PR numbers | gets stale quickly |
| secrets or credentials | security risk |

The right rule is: only keep information that still matters across sessions and cannot be cheaply re-derived from the current workspace.

**Step 6.** Understand the boundaries against neighbor concepts. These four things sound similar but serve different purposes.

| Concept | Purpose | Lifetime |
|---------|---------|----------|
| Memory | Facts that should survive across sessions | Persistent |
| Task | What the system is trying to finish right now | One task |
| Plan | How this turn or session intends to proceed | One session |
| CLAUDE.md | Stable instruction documents and project-level standing rules | Persistent |

Short rule of thumb: only useful for this task -- use `task` or `plan`. Useful next session too -- use `memory`. Long-lived instruction text -- use `CLAUDE.md`.

## Common Mistakes

**Mistake 1: Storing things the repo can tell you.** If the code can answer it, memory should not duplicate it. You will just end up with stale copies that conflict with reality.

**Mistake 2: Storing live task progress.** "Currently fixing auth" is not memory. That belongs to plan or task state. When the task is done, the memory is meaningless.

**Mistake 3: Treating memory as absolute truth.** Memory can be stale. The safer rule is: memory gives direction, current observation gives truth.

## What Changed From s08

| Component | Before (s08) | After (s09) |
|-----------|-------------|-------------|
| Cross-session state | None | File-based memory store |
| Memory types | None | user, feedback, project, reference |
| Storage format | None | YAML frontmatter markdown files |
| Session start | Cold start | Loads relevant memories |
| Durability | Everything forgotten | Key facts persist |

## Try It

```sh
cd learn-claude-code
python agents/s09_memory_system.py
```

Try asking it to remember:

- a user preference
- a correction you want enforced later
- a project fact that is not obvious from the repository

## What You've Mastered

At this point, you can:

- Explain why memory is a curated store of durable facts, not a dump of everything the agent has seen
- Categorize facts into four types: user preferences, feedback, project knowledge, and references
- Store and retrieve memories using frontmatter-based markdown files
- Draw a clear line between what belongs in memory and what belongs in task state, plans, or CLAUDE.md
- Avoid the three most common mistakes: duplicating the repo, storing transient state, and treating memories as ground truth

## What's Next

Your agent now remembers things across sessions, but those memories just sit in a file until session start. In s10, you will build the system prompt assembly pipeline -- the mechanism that takes memories, skills, permissions, and other context and weaves them into the prompt that the model actually sees on every turn.

## Key Takeaway

> Memory is not a dump of everything the agent has seen -- it is a small store of durable facts that should still matter next session.
