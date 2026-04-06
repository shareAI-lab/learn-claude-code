# s02: Tool Use

`s01 > [ s02 ] s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Добавить tool — значит добавить один handler"* -- loop остаётся прежним; новые tools регистрируются в dispatch map.
>
> **Harness layer**: Tool dispatch -- расширяем возможности model.

## Проблема

Имея только `bash`, agent использует оболочку для всего. `cat` обрезает вывод непредсказуемо, `sed` ломается на спецсимволах, а каждый bash-вызов — это неограниченная поверхность для атак. Специализированные tools вроде `read_file` и `write_file` позволяют применять ограничение путей на уровне tool.

Ключевая идея: добавление tools не требует изменения loop.

## Решение

```
+--------+      +-------+      +------------------+
|  User  | ---> |  LLM  | ---> | Tool Dispatch    |
| prompt |      |       |      | {                |
+--------+      +---+---+      |   bash: run_bash |
                    ^           |   read: run_read |
                    |           |   write: run_wr  |
                    +-----------+   edit: run_edit |
                    tool_result | }                |
                                +------------------+

The dispatch map — это словарь: {tool_name: handler_function}.
Один поиск заменяет любую цепочку if/elif.
```

## Как это работает

1. Каждый tool получает функцию-handler. Ограничение путей предотвращает выход за пределы рабочего пространства.

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

2. Dispatch map связывает имена tools с handlers.

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. В loop ищем handler по имени. Тело loop осталось неизменным по сравнению с s01.

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

Добавить tool = добавить handler + добавить запись в схему. Loop никогда не меняется.

## Что изменилось по сравнению с s01

| Компонент      | До (s01)              | После (s02)                |
|----------------|-----------------------|----------------------------|
| Tools          | 1 (только bash)       | 4 (bash, read, write, edit)|
| Dispatch       | Жёстко закодированный bash | `TOOL_HANDLERS` dict  |
| Безопасность путей | Нет              | Sandbox `safe_path()`      |
| Agent loop     | Без изменений         | Без изменений              |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`
