# s25: Named Teams

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > s23 > s24 > [ s25 ]`

> *"Call me by name, give me a role"* -- named agents with independent configs and @mention routing.
>
> **Harness layer**: Named agent registry -- every agent gets a name, a config, and can be addressed directly.

## Problem

By s24, the agent has a persistent goal and self-evaluates progress. But the team model from s09-s10 is still anonymous under the hood. When you spawn "a coder" or "a tester", you get a thread with a label string -- not a first-class identity. There's no way to:

- Address a specific agent by name without guessing its spawn order.
- Give different agents different models, system prompts, or tool limits.
- Persist agent identities across sessions -- restart the team and everyone is a stranger.
- Route a message to "alice" specifically instead of broadcasting to the whole team.

The user wants to say `@alice, review this PR` and have it land in alice's inbox -- not everyone's. And alice should remember she uses the `haiku` model with the `code-review` skill, because that was her config.

## Solution

```
@mention message routing:

  User types: "@alice, review agents/s24_goal_mode.py"
                 |
                 v
  +------------------------------------------+
  |  Message Router                          |
  |                                          |
  |  1. Parse @mentions from the message     |
  |     ["@alice"]                           |
  |  2. Look up names in TeamRegistry        |
  |     alice -> AgentConfig(name="alice",   |
  |               model="haiku", ...)        |
  |  3. Deliver to target inboxes only       |
  +----------------+-------------------------+
                   |
         +---------v---------+
         |  .team/inbox/     |
         |    alice.jsonl << |  {from: "lead",
         |                   |   content: "review...",
         |   (bob.jsonl)     |   mentioned: ["alice"]}
         |   unchanged       |
         +-------------------+
                   |
                   v
         +---------+---------+
         |  Alice wakes up   |
         |  Reads inbox      |
         |  Sees her name    |
         |  Was mentioned    |
         |  Acts on request  |
         +-------------------+


Named agent config (.team/agents/alice.json):
  {
    "name": "alice",
    "role": "code-reviewer",
    "model": "claude-haiku-4-20250514",
    "system_prompt": "You are a meticulous code reviewer.",
    "max_tokens": 4096,
    "skills": ["code-review"],
    "tools": ["read_file", "write_comment"],
    "status": "idle"
  }

TeamRegistry:
  .team/
    registry.json         <- index: name -> config path
    agents/
      alice.json          <- per-agent config
      bob.json
      lead.json
    inbox/
      alice.jsonl         <- only messages for alice
      bob.jsonl
      lead.jsonl
```

## How It Works

1. **NamedAgent** carries a first-class identity with its own config.

```python
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

@dataclass
class NamedAgent:
    name: str
    role: str
    model: str = "claude-sonnet-4-20250514"
    system_prompt: str = ""
    max_tokens: int = 8192
    skills: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    status: str = "idle"

    def to_config(self) -> dict:
        return asdict(self)

    @classmethod
    def from_config(cls, path: Path) -> "NamedAgent":
        data = json.loads(path.read_text())
        return cls(**data)

    def save_config(self, agents_dir: Path):
        config_path = agents_dir / f"{self.name}.json"
        config_path.write_text(json.dumps(self.to_config(), indent=2))
```

2. **TeamRegistry** manages the roster and persists agent configs.

```python
class TeamRegistry:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.agents_dir = self.dir / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.dir / "registry.json"
        self._registry = self._load_registry()
        self._agents: dict[str, NamedAgent] = {}
        self._load_agents()

    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text())
        return {"agents": {}}

    def _save_registry(self):
        self.registry_path.write_text(
            json.dumps(self._registry, indent=2))

    def _load_agents(self):
        for name in self._registry.get("agents", {}):
            cfg_path = self.agents_dir / f"{name}.json"
            if cfg_path.exists():
                agent = NamedAgent.from_config(cfg_path)
                self._agents[name] = agent

    def register(self, agent: NamedAgent) -> str:
        self._agents[agent.name] = agent
        self._registry["agents"][agent.name] = {
            "role": agent.role,
            "model": agent.model,
        }
        agent.save_config(self.agents_dir)
        self._save_registry()
        return f"Registered agent '{agent.name}' ({agent.role})"

    def get(self, name: str) -> NamedAgent | None:
        return self._agents.get(name)

    def list_agents(self) -> list[dict]:
        return [
            {"name": a.name, "role": a.role, "status": a.status,
             "model": a.model}
            for a in self._agents.values()
        ]

    def get_by_role(self, role: str) -> list[NamedAgent]:
        return [a for a in self._agents.values() if a.role == role]
```

3. **Message routing** parses @mentions and delivers only to targeted agents.

```python
import re

class MessageRouter:
    def __init__(self, registry: TeamRegistry, msg_bus: "MessageBus"):
        self.registry = registry
        self.bus = msg_bus

    def _parse_mentions(self, content: str) -> list[str]:
        """Extract @mention names from message content."""
        return re.findall(r"@(\w+)", content)

    def route(self, sender: str, content: str) -> list[str]:
        """Route a message, returning list of delivered-to names."""
        mentions = self._parse_mentions(content)
        delivered = []

        if mentions:
            # Direct @mention -- deliver only to mentioned agents
            for name in mentions:
                agent = self.registry.get(name)
                if agent:
                    self.bus.send(sender, name, content,
                                  msg_type="mention")
                    delivered.append(name)
        else:
            # No mentions -- broadcast to all non-sender agents
            for name, agent in self.registry._agents.items():
                if name != sender:
                    self.bus.send(sender, name, content,
                                  msg_type="broadcast")
                    delivered.append(name)

        return delivered
```

4. **Agent loop** now uses per-agent config for model, tools, and system prompt.

```python
def _agent_loop(self, agent: NamedAgent):
    """Run the agent loop with this agent's specific config."""
    messages = [{"role": "user", "content": agent.system_prompt}]

    for _ in range(50):
        # Check inbox
        inbox = self.bus.read_inbox(agent.name)
        if inbox != "[]":
            messages.append({
                "role": "user",
                "content": f"<inbox for {agent.name}>\n{inbox}\n</inbox>"
            })

        # Use agent's own model and config
        response = client.messages.create(
            model=agent.model,
            max_tokens=agent.max_tokens,
            messages=messages,
            tools=agent.allowed_tools or None,
        )

        if response.stop_reason != "tool_use":
            agent.status = "idle"
            break

        agent.status = "working"
        # Execute tools, append results...
```

5. **Slash command** for managing the team roster.

```python
def handle_team_command(self, args: str) -> str:
    if not args.strip():
        # /team -- show roster
        agents = self.registry.list_agents()
        lines = [f"Team ({len(agents)} agents):"]
        for a in agents:
            lines.append(
                f"  @{a['name']} | {a['role']} | "
                f"{a['model'].split('-')[1] if '-' in a['model'] else a['model']} | "
                f"{a['status']}")
        return "\n".join(lines)

    elif args.startswith("add "):
        # /team add alice code-reviewer haiku
        parts = args.split()
        name, role = parts[1], parts[2]
        model = parts[3] if len(parts) > 3 else "sonnet"
        agent = NamedAgent(name=name, role=role, model=model)
        return self.registry.register(agent)

    else:
        return "Usage: /team [add <name> <role> [model]]"
```

## What Changed From s24

| Component       | Before (s24)                          | After (s25)                                  |
|-----------------|---------------------------------------|----------------------------------------------|
| Agent identity  | Anonymous threads with label strings  | NamedAgent with persistent config            |
| Config          | Shared model, shared system prompt    | Per-agent model, tools, skills, max_tokens   |
| Addressing      | Broadcast only                        | @mention routing to specific agents          |
| Roster          | config.json list of dicts             | TeamRegistry + individual agent JSON files   |
| Message delivery| All teammates get everything          | Targeted delivery, broadcast as fallback     |
| Persistence     | Goal state only                       | Agent configs survive across sessions        |
| Status tracking | Inline in config.json                 | Per-agent status in individual config files  |
| Team command    | None                                  | /team roster view + /team add                |

## Try It

```sh
cd learn-claude-code
python agents/s25_named_teams.py
```

Try these:

1. `/team add alice code-reviewer haiku` -- register a named agent with its own model
2. `/team add bob tester sonnet` -- add another agent
3. `/team` -- see the full roster with names, roles, models, and statuses
4. `@alice, review agents/s24_goal_mode.py` -- direct a message to alice only
5. `Everyone, status update: phase 2 starting` -- broadcast to all agents
6. Check `.team/agents/alice.json` -- alice's config persisted independently
7. `@bob, write tests for the Goal.transition method` -- route to bob specifically
8. `/team` -- watch statuses change from idle to working and back
9. Restart the session -- alice and bob are still registered with their configs
10. `/team add carol architect opus` -- add a third agent mid-session, verify the roster
