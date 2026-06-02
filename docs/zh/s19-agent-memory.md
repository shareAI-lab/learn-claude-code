# s19: Agent Memory & Persistence (Agent 记忆与持久化)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

> *"文件在对话之外,比对话活得久"* -- 状态跨越会话生存。
>
> **Harness 层**: 持久化 -- 跨会话保存和恢复 Agent 状态。

## 问题

s18 之后,harness 能优化成本。但当 Agent 退出时,所有对话状态都丢失了。下次会话从零开始 -- Agent 不记得学到了什么、正在做什么任务、被给了什么指令。

## 解决方案

```
.agent_memory/
|-- priority.json      (始终加载, < 500 字符,永不清理)
|                       {"directives": ["..."], "notes": {...}}
|-- working/
|   |-- 2025-01-01T12-00-00.json  (带时间戳的条目)
|   `-- 2025-01-02T08-30-00.json
`-- checkpoint.json    (上次对话状态)

会话生命周期:
1. 启动: 加载 priority + 近期 working memory
2. 加载: 恢复 checkpoint (对话状态)
3. 工作: agent 循环,追加消息
4. 保存: 每轮之后保存 checkpoint
5. 清理: 删除 > 7 天的 working memory

Priority vs Working:
Priority  -- 小,始终加载,永不清理
Working   -- 带时间戳,近期才加载,7 天自动清理
```

## 工作原理

1. **Priority 记忆。** 小 JSON 文件,始终加载。

```python
def add_directive(self, directive: str):
    data = self.read_priority()
    data["directives"].append(directive)
    self.write_priority(data)
```

2. **Working 记忆。** 带时间戳的条目,7 天后自动清理。

```python
def write_working(self, content: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    path = self.working / f"{ts}.json"
    path.write_text(json.dumps({"timestamp": ts, "content": content}))

def prune(self, days=7) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    for f in self.working.glob("*.json"):
        ts = datetime.fromisoformat(json.loads(f.read_text())["timestamp"])
        if ts < cutoff:
            f.unlink()
```

3. **Checkpoint。** 保存/恢复对话状态。

```python
def save_checkpoint(self, messages: list):
    path = self.base / "checkpoint.json"
    path.write_text(json.dumps(messages))

def load_checkpoint(self) -> list:
    path = self.base / "checkpoint.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())
```

## 试一试

```sh
cd learn-claude-code
python agents/s19_agent_memory.py
```

试试这些:

1. 添加指令: `/directive Always use type hints`
2. 保存记忆: `/memsave 学到了 API 使用 v2 版本`
3. 检查状态: `/memory`
4. 退出并重启 -- 指令和记忆会保留
5. `/clear` -- 清除所有记忆,重新开始