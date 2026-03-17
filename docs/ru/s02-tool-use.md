# s02: Использование инструментов

`s01 > [ s02 ] s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *«Добавить инструмент — значит добавить один обработчик»* — цикл не меняется; новые инструменты регистрируются в dispatch map.

## Проблема

Имея только `bash`, агент использует командную оболочку для всего. `cat` обрезает результат непредсказуемо, `sed` ломается на спецсимволах, и каждый вызов bash — это неограниченная поверхность угроз безопасности. Специализированные инструменты вроде `read_file` и `write_file` позволяют применять ограничения путей на уровне инструмента.

Ключевое понимание: добавление инструментов не требует изменения цикла.

## Решение

```
+----------+      +-------+      +--------------------+
|  Пользов.| ---> |  LLM  | ---> | Dispatch инструм.  |
|  запрос  |      |       |      | {                  |
+----------+      +---+---+      |   bash: run_bash   |
                      ^           |   read: run_read   |
                      |           |   write: run_wr    |
                      +-----------+   edit: run_edit   |
                      tool_result | }                  |
                                  +--------------------+

Dispatch map — словарь: {имя_инструмента: функция_обработчик}.
Один lookup заменяет любую цепочку if/elif.
```

## Как это работает

1. Каждый инструмент получает функцию-обработчик. Ограничение путей предотвращает выход за пределы рабочей директории.

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    if limit and limit < len(lines):
        lines = lines[:limit]
    return "\n".join(lines)[:50000]
```

2. Dispatch map связывает имена инструментов с обработчиками.

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. В цикле находим обработчик по имени. Тело цикла само по себе не изменилось с s01.

```python
for block in response.content:
    if block.type == "tool_use":
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Unknown tool: {block.name}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

Добавить инструмент = добавить обработчик + добавить запись в схему. Цикл никогда не меняется.

## Что изменилось по сравнению с s01

| Компонент      | До (s01)              | После (s02)                |
|----------------|-----------------------|----------------------------|
| Инструменты    | 1 (только bash)       | 4 (bash, read, write, edit)|
| Dispatch       | Жёсткий вызов bash    | Словарь `TOOL_HANDLERS`    |
| Безопасность   | Нет                   | Sandbox `safe_path()`      |
| Цикл агента    | Без изменений         | Без изменений              |

## Попробуйте

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`
