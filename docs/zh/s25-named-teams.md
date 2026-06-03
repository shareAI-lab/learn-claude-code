# s25: 命名团队

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > s23 > s24 > [ s25 ]`

> *"叫我的名字, 给我一个角色"* —— 带独立配置和 @提及路由的命名 Agent。
>
> **Harness 层**: 命名 Agent 注册表 —— 每个 Agent 拥有名字、配置, 可以被直接寻址。

## 问题

到了 s24, Agent 有持久化的目标并能自我评估进度。但 s09-s10 的团队模型在底层仍然是匿名的。当你创建"一个程序员"或"一个测试员"时, 你得到的只是一个带标签字符串的线程 —— 不是一等公民身份。无法做到:

- 通过名字寻址某个特定 Agent, 而不靠猜测它的创建顺序。
- 给不同 Agent 分配不同的模型、系统提示或工具限制。
- 跨会话保持 Agent 身份 —— 重启团队后大家又变成了陌生人。
- 把消息路由给"alice"本人, 而不是广播给整个团队。

用户希望输入 `@alice, review this PR` 然后消息落入 alice 的收件箱 —— 而不是每个人的。而且 alice 应该记得她用 `haiku` 模型和 `code-review` 技能, 因为那是她的配置。

## 解决方案

```
@提及消息路由:

  用户输入: "@alice, review agents/s24_goal_mode.py"
                 |
                 v
  +------------------------------------------+
  |  消息路由器                               |
  |                                          |
  |  1. 从消息中解析 @提及                    |
  |     ["@alice"]                           |
  |  2. 在 TeamRegistry 中查找名字            |
  |     alice -> AgentConfig(name="alice",   |
  |               model="haiku", ...)        |
  |  3. 仅投递到目标收件箱                     |
  +----------------+-------------------------+
                   |
         +---------v---------+
         |  .team/inbox/     |
         |    alice.jsonl << |  {from: "lead",
         |                   |   content: "review...",
         |   (bob.jsonl)     |   mentioned: ["alice"]}
         |   未变动           |
         +-------------------+
                   |
                   v
         +---------+---------+
         |  Alice 被唤醒      |
         |  读取收件箱        |
         |  看到自己的名字    |
         |  被提及了          |
         |  处理请求          |
         +-------------------+


命名 Agent 配置 (.team/agents/alice.json):
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
    registry.json         <- 索引: 名字 -> 配置路径
    agents/
      alice.json          <- 每个 Agent 的独立配置
      bob.json
      lead.json
    inbox/
      alice.jsonl         <- 仅 alice 的消息
      bob.jsonl
      lead.jsonl
```

## 工作原理

1. **NamedAgent** 携带一等身份和独立配置。

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

2. **TeamRegistry** 管理名册并持久化 Agent 配置。

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

3. **消息路由** 解析 @提及并只投递给目标 Agent。

```python
import re

class MessageRouter:
    def __init__(self, registry: TeamRegistry, msg_bus: "MessageBus"):
        self.registry = registry
        self.bus = msg_bus

    def _parse_mentions(self, content: str) -> list[str]:
        """从消息内容中提取 @提及的名字。"""
        return re.findall(r"@(\w+)", content)

    def route(self, sender: str, content: str) -> list[str]:
        """路由消息, 返回已投递的目标名字列表。"""
        mentions = self._parse_mentions(content)
        delivered = []

        if mentions:
            # 直接 @提及 —— 仅投递给被提及的 Agent
            for name in mentions:
                agent = self.registry.get(name)
                if agent:
                    self.bus.send(sender, name, content,
                                  msg_type="mention")
                    delivered.append(name)
        else:
            # 无提及 —— 广播给所有非发送者 Agent
            for name, agent in self.registry._agents.items():
                if name != sender:
                    self.bus.send(sender, name, content,
                                  msg_type="broadcast")
                    delivered.append(name)

        return delivered
```

4. **Agent loop** 现在使用每个 Agent 自己的配置来选择模型、工具和系统提示。

```python
def _agent_loop(self, agent: NamedAgent):
    """使用此 Agent 的专属配置运行 agent loop。"""
    messages = [{"role": "user", "content": agent.system_prompt}]

    for _ in range(50):
        # 检查收件箱
        inbox = self.bus.read_inbox(agent.name)
        if inbox != "[]":
            messages.append({
                "role": "user",
                "content": f"<inbox for {agent.name}>\n{inbox}\n</inbox>"
            })

        # 使用 Agent 自己的模型和配置
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
        # 执行工具, 追加结果...
```

5. **斜杠命令** 管理团队名册。

```python
def handle_team_command(self, args: str) -> str:
    if not args.strip():
        # /team -- 显示名册
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

## 相对 s24 的变更

| 组件           | 之前 (s24)                      | 之后 (s25)                                |
|----------------|---------------------------------|-------------------------------------------|
| Agent 身份     | 带标签字符串的匿名线程           | 带持久化配置的 NamedAgent                 |
| 配置           | 共享模型, 共享系统提示           | 每个 Agent 独立的模型、工具、技能、max_tokens |
| 寻址           | 仅广播                          | @提及路由到指定 Agent                     |
| 名册           | config.json 中的字典列表        | TeamRegistry + 独立的 Agent JSON 文件      |
| 消息投递       | 所有队友收到所有消息             | 定向投递, 无提及时广播作为兜底            |
| 持久化         | 仅目标状态                       | Agent 配置跨会话存活                      |
| 状态追踪       | 内联在 config.json 中           | 每个 Agent 的独立配置文件中维护状态        |
| 团队命令       | 无                              | /team 名册查看 + /team add                |

## 试一试

```sh
cd learn-claude-code
python agents/s25_named_teams.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `/team add alice code-reviewer haiku` —— 注册一个带独立模型的命名 Agent
2. `/team add bob tester sonnet` —— 添加另一个 Agent
3. `/team` —— 查看完整名册, 包含名字、角色、模型和状态
4. `@alice, review agents/s24_goal_mode.py` —— 把消息只发给 alice
5. `Everyone, status update: phase 2 starting` —— 广播给所有 Agent
6. 检查 `.team/agents/alice.json` —— alice 的配置独立持久化
7. `@bob, write tests for the Goal.transition method` —— 路由到 bob
8. `/team` —— 观察状态从 idle 变为 working 再回到 idle
9. 重启会话 —— alice 和 bob 仍然保留注册和配置
10. `/team add carol architect opus` —— 在会话中途添加第三个 Agent, 验证名册更新
