# s04: Субагенты

`s01 > s02 > s03 > [ s04 ] s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *«Разбивай большие задачи; каждая подзадача получает чистый контекст»* — субагенты используют независимый messages[], сохраняя основной разговор чистым.

## Проблема

По мере работы агента его массив messages растёт. Каждое прочитанное файл, каждый вывод bash остаётся в контексте навсегда. «Какой тестовый фреймворк использует этот проект?» может потребовать чтения 5 файлов, но родителю нужен только ответ: «pytest».

## Решение

```
Родительский агент              Субагент
+------------------+             +------------------+
| messages=[...]   |             | messages=[]      | <-- чистый
|                  |  dispatch   |                  |
| tool: task       | ----------> | while tool_use:  |
|   prompt="..."   |             |   вызов инструм. |
|                  |  summary    |   добавить рез.  |
|   result = "..." | <---------- | вернуть текст    |
+------------------+             +------------------+

Контекст родителя остаётся чистым. Контекст субагента отбрасывается.
```

## Как это работает

1. Родитель получает инструмент `task`. Дочерний агент получает все базовые инструменты кроме `task` (без рекурсивного порождения).

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

2. Субагент стартует с `messages=[]` и запускает собственный цикл. Только финальный текст возвращается родителю.

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # ограничение безопасности
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

Вся история сообщений дочернего агента (возможно, 30+ вызовов инструментов) отбрасывается. Родитель получает одноабзацную сводку как обычный `tool_result`.

## Что изменилось по сравнению с s03

| Компонент      | До (s03)         | После (s04)               |
|----------------|------------------|---------------------------|
| Инструменты    | 5                | 5 (base) + task (parent)  |
| Контекст       | Единый общий     | Изоляция родитель + дочерний|
| Субагент       | Нет              | Функция `run_subagent()`  |
| Возвращаемое   | Н/Д              | Только сводный текст      |

## Попробуйте

```sh
cd learn-claude-code
python agents/s04_subagent.py
```

1. `Use a subtask to find what testing framework this project uses`
2. `Delegate: read all .py files and summarize what each one does`
3. `Use a task to create a new module, then verify it from here`
