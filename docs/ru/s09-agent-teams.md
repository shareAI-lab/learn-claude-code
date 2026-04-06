# s09: Команды агентов

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] s10 > s11 > s12`

> *"Когда задача слишком велика для одного — делегируй коллегам"* -- постоянные коллеги + асинхронные mailbox-ы.
>
> **Harness layer**: Team mailbox-ы -- несколько model-ей, скоординированных через файлы.

## Проблема

Subagent-ы (s04) одноразовые: запустить, поработать, вернуть резюме, завершить. Нет идентичности, нет памяти между вызовами. Фоновые задачи (s08) выполняют команды оболочки, но не могут принимать решения под управлением LLM.

Настоящая командная работа требует: (1) постоянных агентов, которые живут дольше одного промпта, (2) управления идентичностью и жизненным циклом, (3) канала коммуникации между агентами.

## Решение

```
Жизненный цикл коллеги:
  spawn -> WORKING -> IDLE -> WORKING -> ... -> SHUTDOWN

Коммуникация:
  .team/
    config.json           <- состав команды + статусы
    inbox/
      alice.jsonl         <- только дозапись, очищается при чтении
      bob.jsonl
      lead.jsonl

              +--------+    send("alice","bob","...")    +--------+
              | alice  | -----------------------------> |  bob   |
              | loop   |    bob.jsonl << {json_line}    |  loop  |
              +--------+                                +--------+
                   ^                                         |
                   |        BUS.read_inbox("alice")          |
                   +---- alice.jsonl -> read + drain ---------+
```

## Как это работает

1. TeammateManager поддерживает config.json со списком команды.

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

2. `spawn()` создаёт коллегу и запускает его agent loop в отдельном потоке.

```python
def spawn(self, name: str, role: str, prompt: str) -> str:
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()
    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt), daemon=True)
    thread.start()
    return f"Spawned teammate '{name}' (role: {role})"
```

3. MessageBus: JSONL inbox-ы с дозаписью. `send()` добавляет строку JSON; `read_inbox()` читает всё и очищает.

```python
class MessageBus:
    def send(self, sender, to, content, msg_type="message", extra=None):
        msg = {"type": msg_type, "from": sender,
               "content": content, "timestamp": time.time()}
        if extra:
            msg.update(extra)
        with open(self.dir / f"{to}.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")

    def read_inbox(self, name):
        path = self.dir / f"{name}.jsonl"
        if not path.exists(): return "[]"
        msgs = [json.loads(l) for l in path.read_text().strip().splitlines() if l]
        path.write_text("")  # drain
        return json.dumps(msgs, indent=2)
```

4. Каждый коллега проверяет свой inbox перед каждым вызовом LLM, добавляя полученные сообщения в context.

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # выполнить tool-ы, добавить результаты...
    self._find_member(name)["status"] = "idle"
```

## Что изменилось по сравнению с s08

| Компонент      | До (s08)         | После (s09)                |
|----------------|------------------|----------------------------|
| Tool-ы         | 6                | 9 (+spawn/send/read_inbox) |
| Агенты         | Один             | Lead + N коллег            |
| Персистентность| Нет              | config.json + JSONL inbox-ы|
| Потоки         | Фоновые команды  | Полный agent loop в потоке |
| Жизненный цикл | Запустить-забыть | idle -> working -> idle    |
| Коммуникация   | Нет              | message + broadcast        |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s09_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. Введи `/team`, чтобы увидеть список команды со статусами
5. Введи `/inbox`, чтобы вручную проверить inbox лида
