# s01: The Agent Loop

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Один loop и Bash — это всё, что нужно"* -- один tool + один loop = agent.
>
> **Harness layer**: The loop -- первое соединение model с реальным миром.

## Проблема

Языковая model умеет рассуждать о коде, но не может *взаимодействовать* с реальным миром — читать файлы, запускать тесты или проверять ошибки. Без loop каждый вызов tool требует вручную копировать и вставлять результаты обратно. Вы сами становитесь loop.

## Решение

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (loop until stop_reason != "tool_use")
```

Одно условие выхода управляет всем потоком. Loop работает до тех пор, пока model не прекращает вызывать tools.

## Как это работает

1. Запрос пользователя становится первым сообщением.

```python
messages.append({"role": "user", "content": query})
```

2. Отправляем messages и определения tools в LLM.

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. Добавляем ответ ассистента. Проверяем `stop_reason` — если model не вызвала tool, работа завершена.

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. Выполняем каждый вызов tool, собираем результаты, добавляем как сообщение пользователя. Возвращаемся к шагу 2.

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
messages.append({"role": "user", "content": results})
```

Собранное в одну функцию:

```python
def agent_loop(query):
    messages = [{"role": "user", "content": query}]
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

Это весь agent — менее 30 строк. Всё остальное в этом курсе надстраивается сверху, не изменяя loop.

## Что изменилось

| Компонент     | До         | После                          |
|---------------|------------|--------------------------------|
| Agent loop    | (нет)      | `while True` + stop_reason     |
| Tools         | (нет)      | `bash` (один tool)             |
| Messages      | (нет)      | Накапливаемый список           |
| Control flow  | (нет)      | `stop_reason != "tool_use"`    |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
