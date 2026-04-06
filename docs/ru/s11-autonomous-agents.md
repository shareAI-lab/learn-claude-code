# s11: Автономные агенты

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > [ s11 ] s12`

> *"Коллеги сами просматривают доску и берут задачи"* -- лиду не нужно назначать каждую вручную.
>
> **Harness layer**: Автономность -- model-и, которые находят работу без указаний.

## Проблема

В s09-s10 коллеги работают только тогда, когда им явно говорят. Лид должен запустить каждого с конкретным промптом. Десять невзятых задач на доске? Лид назначает каждую вручную. Не масштабируется.

Настоящая автономность: коллеги сами просматривают доску задач, берут свободные задачи, работают над ними, затем ищут следующие.

Один нюанс: после сжатия context-а (s06) агент может забыть, кто он. Повторная инъекция идентичности решает эту проблему.

## Решение

```
Жизненный цикл коллеги с циклом ожидания:

+-------+
| spawn |
+---+---+
    |
    v
+-------+   tool_use     +-------+
| WORK  | <------------- |  LLM  |
+---+---+                +-------+
    |
    | stop_reason != tool_use (or idle tool called)
    v
+--------+
|  IDLE  |  опрос каждые 5с, до 60с
+---+----+
    |
    +---> проверить inbox --> сообщение? -------> WORK
    |
    +---> сканировать .tasks/ --> свободная? ---> взять -> WORK
    |
    +---> таймаут 60с --------------------------> SHUTDOWN

Повторная инъекция идентичности после сжатия:
  if len(messages) <= 3:
    messages.insert(0, identity_block)
```

## Как это работает

1. Loop коллеги имеет две фазы: WORK и IDLE. Когда LLM перестаёт вызывать tool-ы (или вызывает `idle`), коллега переходит в IDLE.

```python
def _loop(self, name, role, prompt):
    while True:
        # -- ФАЗА WORK --
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(...)
            if response.stop_reason != "tool_use":
                break
            # выполнить tool-ы...
            if idle_requested:
                break

        # -- ФАЗА IDLE --
        self._set_status(name, "idle")
        resume = self._idle_poll(name, messages)
        if not resume:
            self._set_status(name, "shutdown")
            return
        self._set_status(name, "working")
```

2. Фаза IDLE опрашивает inbox и доску задач в цикле.

```python
def _idle_poll(self, name, messages):
    for _ in range(IDLE_TIMEOUT // POLL_INTERVAL):  # 60s / 5s = 12
        time.sleep(POLL_INTERVAL)
        inbox = BUS.read_inbox(name)
        if inbox:
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            return True
        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            claim_task(unclaimed[0]["id"], name)
            messages.append({"role": "user",
                "content": f"<auto-claimed>Task #{unclaimed[0]['id']}: "
                           f"{unclaimed[0]['subject']}</auto-claimed>"})
            return True
    return False  # таймаут -> завершение
```

3. Сканирование доски задач: найти задачи в статусе pending, без владельца, без блокировок.

```python
def scan_unclaimed_tasks() -> list:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed
```

4. Повторная инъекция идентичности: когда context слишком короткий (произошло сжатие), вставить блок идентичности.

```python
if len(messages) <= 3:
    messages.insert(0, {"role": "user",
        "content": f"<identity>You are '{name}', role: {role}, "
                   f"team: {team_name}. Continue your work.</identity>"})
    messages.insert(1, {"role": "assistant",
        "content": f"I am {name}. Continuing."})
```

## Что изменилось по сравнению с s10

| Компонент      | До (s10)         | После (s11)                |
|----------------|------------------|----------------------------|
| Tool-ы         | 12               | 14 (+idle, +claim_task)    |
| Автономность   | Управляется лидом| Самоорганизующаяся         |
| Фаза IDLE      | Нет              | Опрос inbox + доски задач  |
| Взятие задач   | Только вручную   | Авто-взятие свободных задач|
| Идентичность   | System prompt    | + повторная инъекция после сжатия|
| Таймаут        | Нет              | 60с IDLE -> авто-завершение|

## Попробуй сам

```sh
cd learn-claude-code
python agents/s11_autonomous_agents.py
```

1. `Create 3 tasks on the board, then spawn alice and bob. Watch them auto-claim.`
2. `Spawn a coder teammate and let it find work from the task board itself`
3. `Create tasks with dependencies. Watch teammates respect the blocked order.`
4. Введи `/tasks`, чтобы увидеть доску задач с владельцами
5. Введи `/team`, чтобы следить за тем, кто работает, а кто в IDLE
