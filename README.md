[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md)  
# Learn Claude Code -- A nano Claude Code-like agent, built from 0 to 1
<img width="260" src="https://github.com/user-attachments/assets/fe8b852b-97da-4061-a467-9694906b5edf" /><br>

Scan with Wechat to follow us,  
or follow us on X(formerly Twitter): [shareAI-Lab](https://x.com/baicai003)  


```
                    THE AGENT PATTERN
                    =================

    User --> messages[] --> LLM --> response
                                      |
                            stop_reason == "tool_use"?
                           /                          \
                         yes                           no
                          |                             |
                    execute tools                    return text
                    append results
                    loop back -----------------> messages[]


    That's the minimal loop. Every AI coding agent needs this loop.
    Production agents add policy, permissions, and lifecycle layers.
```

**12 progressive sessions, from a simple loop up to isolated autonomous execution.**
**Each session adds one mechanism. Each mechanism has one motto.**

> **s01** &nbsp; *"One loop & Bash is all you need"* &mdash; one tool + one loop = an agent
>
> **s02** &nbsp; *"Adding a tool means adding one handler"* &mdash; the loop stays the same; new tools register into the dispatch map
>
> **s03** &nbsp; *"An agent without a plan drifts"* &mdash; list the steps first, then execute; completion doubles
>
> **s04** &nbsp; *"Break big tasks down; each subtask gets a clean context"* &mdash; subagents use independent messages[], keeping the main conversation clean
>
> **s05** &nbsp; *"Load knowledge when you need it, not upfront"* &mdash; inject via tool_result, not the system prompt
>
> **s06** &nbsp; *"Context will fill up; you need a way to make room"* &mdash; three-layer compression strategy for infinite sessions
>
> **s07** &nbsp; *"Break big goals into small tasks, order them, persist to disk"* &mdash; a file-based task graph with dependencies, laying the foundation for multi-agent collaboration
>
> **s08** &nbsp; *"Run slow operations in the background; the agent keeps thinking"* &mdash; daemon threads run commands, and inject notifications on completion
>
> **s09** &nbsp; *"When the task is too big for one, delegate to teammates"* &mdash; persistent teammates + async mailboxes
>
> **s10** &nbsp; *"Teammates need shared communication rules"* &mdash; one request-response pattern drives all negotiation
>
> **s11** &nbsp; *"Teammates scan the board and claim tasks themselves"* &mdash; no need for the lead to assign each one
>
> **s12** &nbsp; *"Each works in its own directory, no interference"* &mdash; tasks manage goals, worktrees manage directories, bound by ID

---

## The Core Pattern

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

Every session layers one mechanism on top of this loop -- without changing the loop itself.

## Scope (Important)

This repository is a 0->1 learning project for building a nano Claude Code-like agent.
It intentionally simplifies or omits several production mechanisms:

- Full event/hook buses (for example PreToolUse, SessionStart/End, ConfigChange).  
  s12 includes only a minimal append-only lifecycle event stream for teaching.
- Rule-based permission governance and trust workflows
- Session lifecycle controls (resume/fork) and advanced worktree lifecycle controls
- Full MCP runtime details (transport/OAuth/resource subscribe/polling)

Treat the team JSONL mailbox protocol in this repo as a teaching implementation, not a claim about any specific production internals.

## Quick Start

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env   # Edit .env with your ANTHROPIC_API_KEY

python agents/s01_agent_loop.py       # Start here
python agents/s12_worktree_task_isolation.py  # Full progression endpoint
python agents/s_full.py               # Capstone: all mechanisms combined
```

### Web Platform

Interactive visualizations, step-through diagrams, source viewer, and documentation.

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## Learning Path

```
Phase 1: THE LOOP                    Phase 2: PLANNING & KNOWLEDGE
==================                   ==============================
s01  The Agent Loop          [1]     s03  TodoWrite               [5]
     while + stop_reason                  TodoManager + nag reminder
     |                                    |
     +-> s02  Tool Use            [4]     s04  Subagents            [5]
              dispatch map: name->handler     fresh messages[] per child
                                              |
                                         s05  Skills               [5]
                                              SKILL.md via tool_result
                                              |
                                         s06  Context Compact      [5]
                                              3-layer compression

Phase 3: PERSISTENCE                 Phase 4: TEAMS
==================                   =====================
s07  Tasks                   [8]     s09  Agent Teams             [9]
     file-based CRUD + deps graph         teammates + JSONL mailboxes
     |                                    |
s08  Background Tasks        [6]     s10  Team Protocols          [12]
     daemon threads + notify queue        shutdown + plan approval FSM
                                          |
                                     s11  Autonomous Agents       [14]
                                          idle cycle + auto-claim
                                     |
                                     s12  Worktree Isolation      [16]
                                          task coordination + optional isolated execution lanes

                                     [N] = number of tools
```

## Architecture

```
learn-claude-code/
|
|-- agents/                        # Python reference implementations (s01-s12 + s_full capstone)
|-- docs/{en,zh,ja}/               # Mental-model-first documentation (3 languages)
|-- web/                           # Interactive learning platform (Next.js)
|-- skills/                        # Skill files for s05
+-- .github/workflows/ci.yml      # CI: typecheck + build
```

## Documentation

Mental-model-first: problem, solution, ASCII diagram, minimal code.
Available in [English](./docs/en/) | [中文](./docs/zh/) | [日本語](./docs/ja/).

| Session | Topic | Motto |
|---------|-------|-------|
| [s01](./docs/en/s01-the-agent-loop.md) | The Agent Loop | *One loop & Bash is all you need* |
| [s02](./docs/en/s02-tool-use.md) | Tool Use | *Adding a tool means adding one handler* |
| [s03](./docs/en/s03-todo-write.md) | TodoWrite | *An agent without a plan drifts* |
| [s04](./docs/en/s04-subagent.md) | Subagents | *Break big tasks down; each subtask gets a clean context* |
| [s05](./docs/en/s05-skill-loading.md) | Skills | *Load knowledge when you need it, not upfront* |
| [s06](./docs/en/s06-context-compact.md) | Context Compact | *Context will fill up; you need a way to make room* |
| [s07](./docs/en/s07-task-system.md) | Tasks | *Break big goals into small tasks, order them, persist to disk* |
| [s08](./docs/en/s08-background-tasks.md) | Background Tasks | *Run slow operations in the background; the agent keeps thinking* |
| [s09](./docs/en/s09-agent-teams.md) | Agent Teams | *When the task is too big for one, delegate to teammates* |
| [s10](./docs/en/s10-team-protocols.md) | Team Protocols | *Teammates need shared communication rules* |
| [s11](./docs/en/s11-autonomous-agents.md) | Autonomous Agents | *Teammates scan the board and claim tasks themselves* |
| [s12](./docs/en/s12-worktree-task-isolation.md) | Worktree + Task Isolation | *Each works in its own directory, no interference* |

## What's Next -- from understanding to shipping

After the 12 sessions you understand how an agent works inside out. Two ways to put that knowledge to work:

### Kode Agent CLI -- Open-Source Coding Agent CLI

> `npm i -g @shareai-lab/kode`

Skill & LSP support, Windows-ready, pluggable with GLM / MiniMax / DeepSeek and other open models. Install and go.

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- Embed Agent Capabilities in Your App

The official Claude Code Agent SDK communicates with a full CLI process under the hood -- each concurrent user means a separate terminal process. Kode SDK is a standalone library with no per-user process overhead, embeddable in backends, browser extensions, embedded devices, or any runtime.

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## Sister Repo: from *on-demand sessions* to *always-on assistant*

The agent this repo teaches is **use-and-discard** -- open a terminal, give it a task, close when done, next session starts blank. That is the Claude Code model.

[OpenClaw](https://github.com/openclaw/openclaw) proved another possibility: on top of the same agent core, two mechanisms turn the agent from "poke it to make it move" into "it wakes up every 30 seconds to look for work":

- **Heartbeat** -- every 30s the system sends the agent a message to check if there is anything to do. Nothing? Go back to sleep. Something? Act immediately.
- **Cron** -- the agent can schedule its own future tasks, executed automatically when the time comes.

Add multi-channel IM routing (WhatsApp / Telegram / Slack / Discord, 13+ platforms), persistent context memory, and a Soul personality system, and the agent goes from a disposable tool to an always-on personal AI assistant.

**[claw0](https://github.com/shareAI-lab/claw0)** is our companion teaching repo that deconstructs these mechanisms from scratch:

```
claw agent = agent core + heartbeat + cron + IM chat + memory + soul
```

```
learn-claude-code                   claw0
(agent runtime core:                (proactive always-on assistant:
 loop, tools, planning,              heartbeat, cron, IM channels,
 teams, worktree isolation)          memory, soul personality)
```

## License

MIT

---

**The model is the agent. Our job is to give it tools and stay out of the way.**
