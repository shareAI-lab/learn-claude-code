# s01: Цикл агента

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *«Одного цикла и Bash достаточно»* — один инструмент + один цикл = агент.

## Проблема

Языковая модель умеет рассуждать о коде, но не может *взаимодействовать* с реальным миром — читать файлы, запускать тесты, проверять ошибки. Без цикла каждый вызов инструмента требует, чтобы вы вручную копировали результаты обратно. Вы сами становитесь циклом.

## Решение

```
+----------+      +-------+      +----------+
|  Пользов.| ---> |  LLM  | ---> | Инструм. |
|  запрос  |      |       |      | выполнить|
+----------+      +---+---+      +----+-----+
                      ^                |
                      |   tool_result  |
                      +----------------+
                      (цикл до stop_reason != "tool_use")
```

Одно условие выхода управляет всем потоком. Цикл работает, пока модель продолжает вызывать инструменты.

## Как это работает

1. Запрос пользователя становится первым сообщением.

```python
messages.append({"role": "user", "content": query})
```

2. Отправляем сообщения и определения инструментов в LLM.

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. Добавляем ответ ассистента. Проверяем `stop_reason` — если модель не вызвала инструмент, цикл завершён.

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. Выполняем каждый вызов инструмента, собираем результаты, добавляем как сообщение пользователя. Возвращаемся к шагу 2.

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

Собрано в одну функцию:

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

Это весь агент менее чем в 30 строках. Всё остальное в этом курсе надстраивается сверху — не меняя сам цикл.

## Что изменилось

| Компонент     | До         | После                          |
|---------------|------------|--------------------------------|
| Цикл агента   | (нет)      | `while True` + stop_reason     |
| Инструменты   | (нет)      | `bash` (один инструмент)       |
| Сообщения     | (нет)      | Накапливаемый список           |
| Управление    | (нет)      | `stop_reason != "tool_use"`    |

## Попробуйте

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
