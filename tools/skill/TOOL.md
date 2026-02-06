---
name: Skill
description: Load a skill to gain specialized knowledge for a task.
parameters:
  skill:
    type: string
    description: Name of the skill to load
required:
  - skill
dynamic_description: true
---

# Skill Tool

Load domain expertise from SKILL.md files.

## When to Use

- IMMEDIATELY when user task matches a skill description
- Before attempting domain-specific work (PDF, MCP, etc.)

## How It Works

1. Model calls `Skill(skill="pdf")`
2. System loads `skills/pdf/SKILL.md` content
3. Content injected into conversation as tool result
4. Model now has domain knowledge to complete task

## Why Tool Result (Not System Prompt)?

Skill content goes into tool_result (user message), NOT system prompt.
This preserves prompt cache:

- System prompt change → cache invalidated → 20-50x cost increase
- Tool result append → prefix unchanged → cache hit

## Available Skills

Skills are discovered from `skills/*/SKILL.md` files.
Each skill folder can contain:
- `SKILL.md` (required) - Instructions
- `scripts/` (optional) - Helper scripts
- `references/` (optional) - Documentation
- `assets/` (optional) - Templates
