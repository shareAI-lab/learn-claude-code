# s03: TodoWrite

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *«Агент без плана дрейфует»* — сначала составь список шагов, потом выполняй.

## Проблема

На многошаговых задачах модель теряет нить. Она повторяет работу, пропускает шаги или отклоняется от курса. Длинные разговоры усугубляют проблему — системный промпт тускнеет, пока результаты инструментов заполняют контекст. При 10-шаговом рефакторинге модель может выполнить шаги 1-3, а потом начать импровизировать, потому что забыла шаги 4-10.

## Решение

```
+----------+      +-------+      +----------+
|  Пользов.| ---> |  LLM  | ---> | Инструм. |
|  запрос  |      |       |      | + todo   |
+----------+      +---+---+      +----+-----+
                      ^                |
                      |   tool_result  |
                      +----------------+
                            |
                +-----------+-----------+
                | Состояние TodoManager |
                | [ ] задача А          |
                | [>] задача Б  <- сейчас|
                | [x] задача В          |
                +-----------------------+
                            |
                если rounds_since_todo >= 3:
                  добавить <reminder> в tool_result
```

## Как это работает

1. TodoManager хранит элементы со статусами. Только один элемент может быть `in_progress` одновременно.

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

2. Инструмент `todo` добавляется в dispatch map как любой другой.

```python
TOOL_HANDLERS = {
    # ...базовые инструменты...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. Напоминание-«напоминалка» вставляет подсказку, если модель 3+ раундов не вызывает `todo`.

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

Ограничение «только один in_progress одновременно» обеспечивает последовательный фокус. Напоминание создаёт подотчётность.

## Что изменилось по сравнению с s02

| Компонент      | До (s02)         | После (s03)                |
|----------------|------------------|----------------------------|
| Инструменты    | 4                | 5 (+todo)                  |
| Планирование   | Нет              | TodoManager со статусами   |
| Напоминание    | Нет              | `<reminder>` после 3 раундов|
| Цикл агента    | Простой dispatch | + счётчик rounds_since_todo|

## Попробуйте

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`
