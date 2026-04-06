# s06: Context Compact

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *"Context заполнится; нужен способ освободить место"* -- трёхуровневая стратегия сжатия для бесконечных сессий.
>
> **Harness layer**: Сжатие -- чистая память для бесконечных сессий.

## Проблема

Окно context конечно. Один вызов `read_file` на файл из 1000 строк стоит ~4000 токенов. После чтения 30 файлов и выполнения 20 bash-команд накапливается 100 000+ токенов. Без сжатия agent не может работать с большими кодовыми базами.

## Решение

Три уровня, с нарастающей агрессивностью:

```
Every turn:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Layer 1: micro_compact]        (silent, every turn)
  Replace tool_result > 3 turns old
  with "[Previous: used {tool_name}]"
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Layer 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Layer 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## Как это работает

1. **Layer 1 -- micro_compact**: Перед каждым вызовом LLM заменяет старые результаты tool на заглушки.

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

2. **Layer 2 -- auto_compact**: Когда количество токенов превышает порог, сохраняет полный transcript на диск, затем просит LLM создать резюме.

```python
def auto_compact(messages: list) -> list:
    # Save transcript for recovery
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM summarizes
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
    ]
```

3. **Layer 3 -- ручное сжатие**: tool `compact` запускает то же самое суммирование по требованию.

4. loop объединяет все три уровня:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Layer 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Layer 2
        response = client.messages.create(...)
        # ... tool execution ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Layer 3
```

Transcript сохраняют полную историю на диске. Ничто не теряется по-настоящему -- данные просто перемещаются за пределы активного context.

## Что изменилось по сравнению с s05

| Компонент      | До (s05)         | После (s06)                |
|----------------|------------------|----------------------------|
| Tools          | 5                | 5 (base + compact)         |
| Управление context | Отсутствует  | Трёхуровневое сжатие       |
| Micro-compact  | Отсутствует      | Старые результаты -> заглушки|
| Auto-compact   | Отсутствует      | Срабатывание по порогу токенов|
| Transcript     | Отсутствуют      | Сохраняются в .transcripts/|

## Попробуй сам

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (наблюдай, как micro-compact заменяет старые результаты)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`
