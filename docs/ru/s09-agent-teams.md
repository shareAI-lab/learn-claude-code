# s09: Команды агентов

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] s10 > s11 > s12`

> *«Когда задача слишком велика для одного — делегируй команде»* — постоянные участники + асинхронные почтовые ящики.

## Проблема

Субагенты (s04) одноразовые: породил, поработал, вернул сводку, завершился. Нет идентичности, нет памяти между вызовами. Фоновые задачи (s08) выполняют shell-команды, но не могут принимать решения с помощью LLM.

Для реальной командной работы нужны: (1) постоянные агенты, переживающие один промпт, (2) управление идентичностью и жизненным циклом, (3) канал связи между агентами.

## Решение

```
Жизненный цикл участника:
  spawn -> WORKING -> IDLE -> WORKING -> ... -> SHUTDOWN

Коммуникация:
  .team/
    config.json           <- список команды + статусы
    inbox/
      alice.jsonl         <- append-only, очистка при чтении
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

2. `spawn()` создаёт участника и запускает его цикл агента в потоке.

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

3. MessageBus: JSONL-почтовые ящики с дозаписью. `send()` добавляет JSON-строку; `read_inbox()` читает всё и очищает.

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
        path.write_text("")  # очистить
        return json.dumps(msgs, indent=2)
```

4. Каждый участник проверяет почтовый ящик перед каждым вызовом LLM, вставляя полученные сообщения в контекст.

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            messages.append({"role": "assistant",
                "content": "Noted inbox messages."})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # выполнить инструменты, добавить результаты...
    self._find_member(name)["status"] = "idle"
```

## Что изменилось по сравнению с s08

| Компонент      | До (s08)         | После (s09)                |
|----------------|------------------|----------------------------|
| Инструменты    | 6                | 9 (+spawn/send/read_inbox) |
| Агенты         | Один             | Лид + N участников         |
| Персистентность| Нет              | config.json + JSONL-ящики  |
| Потоки         | Фоновые команды  | Полные циклы агентов в потоках|
| Жизненный цикл | Fire-and-forget  | idle -> working -> idle    |
| Коммуникация   | Нет              | message + broadcast        |

## Попробуйте

```sh
cd learn-claude-code
python agents/s09_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. Введите `/team`, чтобы увидеть список команды со статусами
5. Введите `/inbox`, чтобы вручную проверить почтовый ящик лида
