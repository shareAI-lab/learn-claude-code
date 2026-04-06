# s04: Subagents

`s01 > s02 > s03 > [ s04 ] s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Раздели большие задачи; каждая подзадача получает чистый context"* -- subagents используют независимые messages[], сохраняя основной диалог чистым.
>
> **Harness layer**: Context isolation -- защищаем ясность мышления model.

## Проблема

По мере работы agent его массив messages растёт. Каждое прочитанное содержимое файла, каждый вывод bash остаётся в context навсегда. На вопрос «Какой тестовый фреймворк использует этот проект?» может потребоваться прочитать 5 файлов — но родительскому agent нужен только ответ: «pytest».

## Решение

```
Parent agent                     Subagent
+------------------+             +------------------+
| messages=[...]   |             | messages=[]      | <-- fresh
|                  |  dispatch   |                  |
| tool: task       | ----------> | while tool_use:  |
|   prompt="..."   |             |   call tools     |
|                  |  summary    |   append results |
|   result = "..." | <---------- | return last text |
+------------------+             +------------------+

Context родителя остаётся чистым. Context subagent отбрасывается.
```

## Как это работает

1. Родитель получает tool `task`. Дочерний agent получает все базовые tools, кроме `task` (без рекурсивного порождения).

```python
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task",
     "description": "Spawn a subagent with fresh context.",
     "input_schema": {
         "type": "object",
         "properties": {"prompt": {"type": "string"}},
         "required": ["prompt"],
     }},
]
```

2. Subagent стартует с `messages=[]` и запускает собственный loop. Родителю возвращается только финальный текст.

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM,
            messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant",
                             "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input)
                results.append({"type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    return "".join(
        b.text for b in response.content if hasattr(b, "text")
    ) or "(no summary)"
```

Вся история сообщений дочернего agent (возможно, 30+ вызовов tools) отбрасывается. Родитель получает краткое резюме в один абзац как обычный `tool_result`.

## Что изменилось по сравнению с s03

| Компонент      | До (s03)          | После (s04)               |
|----------------|-------------------|---------------------------|
| Tools          | 5                 | 5 (базовые) + task (родитель) |
| Context        | Единый общий      | Изоляция родителя и дочернего |
| Subagent       | Нет               | Функция `run_subagent()`  |
| Возвращаемое значение | Нет        | Только текст резюме       |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s04_subagent.py
```

1. `Use a subtask to find what testing framework this project uses`
2. `Delegate: read all .py files and summarize what each one does`
3. `Use a task to create a new module, then verify it from here`
