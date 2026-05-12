# s10: System Prompt

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > [ s10 ] > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- How to assemble the system prompt from independent sections instead of one hardcoded string
- The boundary between stable content (role, rules) and dynamic content (date, cwd, per-turn reminders)
- How CLAUDE.md files layer instructions without overwriting each other
- Why memory must be re-injected through the prompt pipeline to actually guide the agent

When your agent had one tool and one job, a single hardcoded prompt string worked fine. But look at everything your harness has accumulated by now: a role description, tool definitions, loaded skills, saved memory, CLAUDE.md instruction files, and per-turn runtime context. If you keep cramming all of that into one big string, nobody -- including you -- can tell where each piece came from, why it is there, or how to change it safely. The fix is to stop treating the prompt as a blob and start treating it as an assembly pipeline.

## The Problem

Imagine you want to add a new tool to your agent. You open the system prompt, scroll past the role paragraph, past the safety rules, past the three skill descriptions, past the memory block, and paste a tool description somewhere in the middle. Next week someone else adds a CLAUDE.md loader and appends its output to the same string. A month later the prompt is 6,000 characters long, half of it is stale, and nobody remembers which lines are supposed to change per turn and which should stay fixed across the entire session.

This is not a hypothetical scenario -- it is the natural trajectory of every agent that keeps its prompt in a single variable.

## The Solution

Turn prompt construction into a pipeline. Each section has one source and one responsibility. A builder object assembles them in a fixed order, with a clear boundary between parts that stay stable and parts that change every turn.

```text
1. core identity and rules
2. tool catalog
3. skills
4. memory
5. CLAUDE.md instruction chain
6. dynamic runtime context
```

Then assemble:

```text
core
+ tools
+ skills
+ memory
+ claude_md
+ dynamic_context
= final model input
```

## How It Works

**Step 1. Define the builder.** Each method owns exactly one source of content.

```python
class SystemPromptBuilder:
    def build(self) -> str:
        parts = []
        parts.append(self._build_core())
        parts.append(self._build_tools())
        parts.append(self._build_skills())
        parts.append(self._build_memory())
        parts.append(self._build_claude_md())
        parts.append(self._build_dynamic())
        return "\n\n".join(p for p in parts if p)
```

That is the central idea of the chapter. Each `_build_*` method pulls from one source only: `_build_tools()` reads the tool list, `_build_memory()` reads the memory store, and so on. If you want to know where a line in the prompt came from, you check the one method responsible for it.

**Step 2. Separate stable content from dynamic content.** This is the most important boundary in the entire pipeline.

Stable content changes rarely or never during a session:

- role description
- tool contract (the list of tools and their schemas)
- long-lived safety rules
- project instruction chain (CLAUDE.md files)

Dynamic content changes every turn or every few turns:

- current date
- current working directory
- current mode (plan mode, code mode, etc.)
- per-turn warnings or reminders

Mixing these together means the model re-reads thousands of tokens of stable text that have not changed, while the few tokens that did change are buried somewhere in the middle. A real system separates them with a boundary marker so the stable prefix can be cached across turns to save prompt tokens.

**Step 3. Layer CLAUDE.md instructions.** `CLAUDE.md` is not the same as memory and not the same as a skill. It is a layered instruction source -- meaning multiple files contribute, and later layers add to earlier ones rather than replacing them:

1. user-level instruction file (`~/.claude/CLAUDE.md`)
2. project-root instruction file (`<project>/CLAUDE.md`)
3. deeper subdirectory instruction files

The important point is not the filename itself. The important point is that instruction sources can be layered instead of overwritten.

**Step 4. Re-inject memory.** Saving memory (in s09) is only half the mechanism. If memory never re-enters the model input, it is not actually guiding the agent. So memory naturally belongs in the prompt pipeline:

- save durable facts in `s09`
- re-inject them through the prompt builder in `s10`

**Step 5. Attach per-turn reminders separately.** Some information is even more short-lived than "dynamic context" -- it only matters for this one turn and should not pollute the stable system prompt. A `system-reminder` user message keeps these transient signals outside the builder entirely:

- this-turn-only instructions
- temporary notices
- transient recovery guidance

## What Changed from s09

| Aspect | s09: Memory System | s10: System Prompt |
|--------|--------------------|--------------------|
| Core concern | Persist durable facts across sessions | Assemble all sources into model input |
| Memory's role | Write and store | Read and inject |
| Prompt structure | Assumed but not managed | Explicit pipeline with sections |
| Instruction files | Not addressed | CLAUDE.md layering introduced |
| Dynamic context | Not addressed | Separated from stable content |

## Read Together

- If you still treat the prompt as one mysterious blob of text, revisit [`s00a-query-control-plane.md`](./s00a-query-control-plane.md) to see what reaches the model and through which control layers.
- If you want to stabilize the order of assembly, keep [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) beside this chapter -- it is the key bridge note for `s10`.
- If system rules, tool docs, memory, and runtime state start to collapse into one big input lump, reset with [`data-structures.md`](./data-structures.md).

## Common Beginner Mistakes

**Mistake 1: teaching the prompt as one fixed string.** That hides how the system really grows. A fixed string is fine for a demo; it stops being fine the moment you add a second capability.

**Mistake 2: putting every changing detail into the same prompt block.** That mixes durable rules with per-turn noise. When you update one, you risk breaking the other.

**Mistake 3: treating skills, memory, and CLAUDE.md as the same thing.** They may all become prompt sections, but their source and purpose are different:

- `skills`: optional capability packages loaded on demand
- `memory`: durable cross-session facts about the user or project
- `CLAUDE.md`: standing instruction documents that layer without overwriting

## Try It

```sh
cd learn-claude-code
python agents/s10_system_prompt.py
```

Look for these three things:

1. where each section comes from
2. which parts are stable
3. which parts are generated dynamically each turn

## What You've Mastered

At this point, you can:

- Build a system prompt from independent, testable sections instead of one opaque string
- Draw a clear line between stable content and dynamic content
- Layer instruction files so that project-level and directory-level rules coexist without overwriting
- Re-inject memory into the prompt pipeline so saved facts actually influence the model
- Attach per-turn reminders separately from the main system prompt

## What's Next

The prompt assembly pipeline means your agent now enters each turn with the right instructions, the right tools, and the right context. But real work produces real failures -- output gets cut off, the prompt grows too large, the API times out. In [s11: Error Recovery](./s11-error-recovery.md), you will teach the harness to classify those failures and choose a recovery path instead of crashing.

## Key Takeaway

> The system prompt is an assembly pipeline with clear sections and clear boundaries, not one big mysterious string.
