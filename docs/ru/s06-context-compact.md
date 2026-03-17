# s06: Сжатие контекста

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *«Контекст заполнится; нужен способ освободить место»* — трёхуровневая стратегия сжатия для бесконечных сессий.

## Проблема

Контекстное окно конечно. Один `read_file` на файл в 1000 строк стоит ~4000 токенов. После чтения 30 файлов и 20 bash-команд вы достигаете 100 000+ токенов. Агент не может работать с большими кодовыми базами без сжатия.

## Решение

Три уровня с нарастающей агрессивностью:

```
Каждый ход:
+------------------+
| Результат вызова |
+------------------+
        |
        v
[Уровень 1: micro_compact]        (тихо, каждый ход)
  Заменить tool_result старше 3 ходов
  на "[Previous: used {tool_name}]"
        |
        v
[Проверка: токенов > 50000?]
   |               |
  нет             да
   |               |
   v               v
продолжить  [Уровень 2: auto_compact]
              Сохранить стенограмму в .transcripts/
              LLM суммирует разговор.
              Заменить все сообщения на [сводку].
                    |
                    v
            [Уровень 3: инструмент compact]
              Модель вызывает compact явно.
              То же суммирование, что и auto_compact.
```

## Как это работает

1. **Уровень 1 — micro_compact**: Перед каждым вызовом LLM заменяем старые результаты инструментов заглушками.

```python
def micro_compact(messages: list) -> list:
    tool_results = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for j, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((i, j, part))
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for _, _, part in tool_results[:-KEEP_RECENT]:
        if len(part.get("content", "")) > 100:
            part["content"] = f"[Previous: used {tool_name}]"
    return messages
```

2. **Уровень 2 — auto_compact**: Когда токенов больше порога, сохраняем полную стенограмму на диск, затем просим LLM суммировать.

```python
def auto_compact(messages: list) -> list:
    # Сохраняем стенограмму для восстановления
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM суммирует
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
        {"role": "assistant", "content": "Understood. Continuing."},
    ]
```

3. **Уровень 3 — ручной compact**: Инструмент `compact` запускает то же суммирование по требованию.

4. Цикл интегрирует все три уровня:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Уровень 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Уровень 2
        response = client.messages.create(...)
        # ... выполнение инструментов ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Уровень 3
```

Стенограммы сохраняют полную историю на диске. Ничего по-настоящему не теряется — просто перемещается за пределы активного контекста.

## Что изменилось по сравнению с s05

| Компонент      | До (s05)         | После (s06)                |
|----------------|------------------|----------------------------|
| Инструменты    | 5                | 5 (base + compact)         |
| Управление конт.| Нет             | Трёхуровневое сжатие       |
| Micro-compact  | Нет              | Старые результаты -> заглушки|
| Auto-compact   | Нет              | Триггер по порогу токенов  |
| Стенограммы    | Нет              | Сохраняются в .transcripts/|

## Попробуйте

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (следите, как micro-compact заменяет старые результаты)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`
