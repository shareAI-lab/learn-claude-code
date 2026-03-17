# s11: Автономные агенты

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > [ s11 ] s12`

> *«Участники сами просматривают доску и берут задачи»* — лидеру не нужно назначать каждую.

## Проблема

В s09-s10 участники работают только когда им явно говорят. Лид должен порождать каждого с конкретным промптом. 10 незатребованных задач на доске? Лид назначает каждую вручную. Это не масштабируется.

Истинная автономность: участники сами просматривают доску задач, забирают незатребованные задачи, работают над ними, потом ищут ещё.

Одна тонкость: после сжатия контекста (s06) агент может забыть, кто он. Повторная инжекция идентичности решает эту проблему.

## Решение

```
Жизненный цикл участника с idle-циклом:

+-------+
| spawn |
+---+---+
    |
    v
+-------+   tool_use     +-------+
| WORK  | <------------- |  LLM  |
+---+---+                +-------+
    |
    | stop_reason != tool_use (или вызван инструмент idle)
    v
+--------+
|  IDLE  |  опрос каждые 5с до 60с
+---+----+
    |
    +---> проверить inbox --> сообщение? ----------> WORK
    |
    +---> сканировать .tasks/ --> незатребованное? -> забрать -> WORK
    |
    +---> таймаут 60с ----------------------> SHUTDOWN

Повторная инжекция идентичности после сжатия:
  если len(messages) <= 3:
    messages.insert(0, identity_block)
```

## Как это работает

1. Цикл участника имеет две фазы: WORK и IDLE. Когда LLM перестаёт вызывать инструменты (или вызывает `idle`), участник переходит в IDLE.

```python
def _loop(self, name, role, prompt):
    while True:
        # -- ФАЗА WORK --
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(...)
            if response.stop_reason != "tool_use":
                break
            # выполнить инструменты...
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

2. Фаза idle опрашивает почтовый ящик и доску задач в цикле.

```python
def _idle_poll(self, name, messages):
    for _ in range(IDLE_TIMEOUT // POLL_INTERVAL):  # 60с / 5с = 12
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

3. Сканирование доски задач: найти задачи со статусом pending, без владельца, без блокировок.

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

4. Повторная инжекция идентичности: когда контекст слишком короткий (произошло сжатие), вставляем блок идентичности.

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
| Инструменты    | 12               | 14 (+idle, +claim_task)    |
| Автономность   | По указанию лида | Самоорганизующиеся         |
| Фаза idle      | Нет              | Опрос inbox + доски задач  |
| Захват задач   | Только вручную   | Авто-захват незатребованных|
| Идентичность   | Системный промпт | + повторная инжекция после сжатия|
| Таймаут        | Нет              | 60с idle -> авто-завершение|

## Попробуйте

```sh
cd learn-claude-code
python agents/s11_autonomous_agents.py
```

1. `Create 3 tasks on the board, then spawn alice and bob. Watch them auto-claim.`
2. `Spawn a coder teammate and let it find work from the task board itself`
3. `Create tasks with dependencies. Watch teammates respect the blocked order.`
4. Введите `/tasks` для просмотра доски задач с владельцами
5. Введите `/team` для мониторинга статуса работы участников
