# s03: TodoWrite

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Agent без плана блуждает"* -- сначала перечисли шаги, затем выполняй.
>
> **Harness layer**: Планирование -- удерживаем model на курсе, не прописывая маршрут.

## Проблема

На многоходовых задачах model теряет нить. Она повторяет уже сделанное, пропускает шаги или уходит в сторону. Длинные диалоги усугубляют ситуацию — системный промпт тускнеет по мере того, как tool results заполняют context. Рефакторинг в 10 шагов может завершить шаги 1–3, а затем model начинает импровизировать, потому что забыла шаги 4–10.

## Решение

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> | Tools   |
| prompt |      |       |      | + todo  |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                          |
              +-----------+-----------+
              | TodoManager state     |
              | [ ] task A            |
              | [>] task B  <- doing  |
              | [x] task C            |
              +-----------------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## Как это работает

1. TodoManager хранит элементы со статусами. Одновременно только один элемент может быть в состоянии `in_progress`.

```python
class TodoManager:
    def update(self, items: list) -> str:
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress")
        self.items = validated
        return self.render()
```

2. Tool `todo` добавляется в dispatch map как любой другой tool.

```python
TOOL_HANDLERS = {
    # ...базовые tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. Напоминание встраивает подсказку, если model не вызывала `todo` 3 и более раундов подряд.

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

Ограничение «только один `in_progress` за раз» принуждает к последовательной концентрации. Напоминание создаёт механизм подотчётности.

## Что изменилось по сравнению с s02

| Компонент      | До (s02)         | После (s03)                |
|----------------|------------------|----------------------------|
| Tools          | 4                | 5 (+todo)                  |
| Планирование   | Нет              | TodoManager со статусами   |
| Напоминание    | Нет              | `<reminder>` после 3 раундов|
| Agent loop     | Простой dispatch | + счётчик rounds_since_todo|

## Попробуй сам

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`
