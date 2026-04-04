---
name: agent-builder
description: |
  Design and build AI agents for any domain. Use when users:
  (1) ask to "create an agent", "build an assistant", or "design an AI system"
  (2) want to understand agent architecture, agentic patterns, or autonomous AI
  (3) need help with capabilities, subagents, planning, or skill mechanisms
  (4) ask about Claude Code, Cursor, or similar agent internals
  (5) want to build agents for business, research, creative, or operational tasks
  Keywords: agent, assistant, autonomous, workflow, tool use, multi-step, orchestration
---

# Agent Builder

Build AI agents for any domain - customer service, research, operations, creative work, or specialized business processes.

## The Core Philosophy

> **The model already knows how to be an agent. Your job is to get out of the way.**

An agent is not complex engineering. It's a simple loop that invites the model to act:

```
LOOP:
  Model sees: context + available capabilities
  Model decides: act or respond
  If act: execute capability, add result, continue
  If respond: return to user
```

**That's it.** The magic isn't in the code - it's in the model. Your code just provides the opportunity.

## The Three Elements

### 1. Capabilities (What can it DO?)

Atomic actions the agent can perform: search, read, create, send, query, modify.

**Design principle**: Start with 3-5 capabilities. Add more only when the agent consistently fails because a capability is missing.

### 2. Knowledge (What does it KNOW?)

Domain expertise injected on-demand: policies, workflows, best practices, schemas.

**Design principle**: Make knowledge available, not mandatory. Load it when relevant, not upfront.

### 3. Context (What has happened?)

The conversation history - the thread connecting actions into coherent behavior.

**Design principle**: Context is precious. Isolate noisy subtasks. Truncate verbose outputs. Protect clarity.

## Agent Design Thinking

Before building, understand:

- **Purpose**: What should this agent accomplish?
- **Domain**: What world does it operate in? (customer service, research, operations, creative...)
- **Capabilities**: What 3-5 actions are essential?
- **Knowledge**: What expertise does it need access to?
- **Trust**: What decisions can you delegate to the model?

**CRITICAL**: Trust the model. Don't over-engineer. Don't pre-specify workflows. Give it capabilities and let it reason.

## Progressive Complexity

Start simple. Add complexity only when real usage reveals the need:

| Level | What to add | When to add it |
|-------|-------------|----------------|
| Basic | 3-5 capabilities | Always start here |
| Planning | Progress tracking | Multi-step tasks lose coherence |
| Subagents | Isolated child agents | Exploration pollutes context |
| Skills | On-demand knowledge | Domain expertise needed |

**Most agents never need to go beyond Level 2.**

## Domain Examples

**Business**: CRM queries, email, calendar, approvals
**Research**: Database search, document analysis, citations
**Operations**: Monitoring, tickets, notifications, escalation
**Creative**: Asset generation, editing, collaboration, review

The pattern is universal. Only the capabilities change.

## Key Principles

1. **The model IS the agent** - Code just runs the loop
2. **Capabilities enable** - What it CAN do
3. **Knowledge informs** - What it KNOWS how to do
4. **Constraints focus** - Limits create clarity
5. **Trust liberates** - Let the model reason
6. **Iteration reveals** - Start minimal, evolve from usage

## Anti-Patterns

| Pattern | Problem | Solution |
|---------|---------|----------|
| Over-engineering | Complexity before need | Start simple |
| Too many capabilities | Model confusion | 3-5 to start |
| Rigid workflows | Can't adapt | Let model decide |
| Front-loaded knowledge | Context bloat | Load on-demand |
| Micromanagement | Undercuts intelligence | Trust the model |

## Resources

**Philosophy & Theory**:
- `references/agent-philosophy.md` - Deep dive into why agents work

**Implementation**:
- `references/minimal-agent.py` - Complete working agent (~80 lines)
- `references/tool-templates.py` - Capability definitions
- `references/subagent-pattern.py` - Context isolation

**Scaffolding**:
- `scripts/init_agent.py` - Generate new agent projects

## The Agent Mindset

**From**: "How do I make the system do X?"
**To**: "How do I enable the model to do X?"

**From**: "What's the workflow for this task?"
**To**: "What capabilities would help accomplish this?"

The best agent code is almost boring. Simple loops. Clear capabilities. Clean context. The magic isn't in the code.

**Give the model capabilities and knowledge. Trust it to figure out the rest.**
