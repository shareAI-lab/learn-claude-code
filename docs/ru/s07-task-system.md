# s07: Система задач

`s01 > s02 > s03 > s04 > s05 > s06 | [ s07 ] s08 > s09 > s10 > s11 > s12`

> *«Разбивай большие цели на маленькие задачи, упорядочивай их, сохраняй на диск»* — файловый граф задач с зависимостями, закладывающий основу для многоагентного взаимодействия.

## Проблема

TodoManager из s03 — плоский чеклист в памяти: без порядка, без зависимостей, без статусов кроме «сделано/нет». Реальные цели имеют структуру — задача Б зависит от задачи А, задачи В и Г могут выполняться параллельно, задача Д ждёт завершения обеих В и Г.

Без явных связей агент не может понять, что готово, что заблокировано, а что может выполняться параллельно. И поскольку список живёт только в памяти, сжатие контекста (s06) полностью его стирает.

## Решение

Превратить чеклист в **граф задач**, сохранённый на диске. Каждая задача — JSON-файл со статусом, зависимостями (`blockedBy`) и зависящими задачами (`blocks`). Граф в любой момент отвечает на три вопроса:

- **Что готово?** — задачи со статусом `pending` и пустым `blockedBy`.
- **Что заблокировано?** — задачи, ждущие незавершённых зависимостей.
- **Что сделано?** — задачи со статусом `completed`, завершение которых автоматически разблокирует зависящие задачи.

```
.tasks/
  task_1.json  {"id":1, "status":"completed"}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending"}
  task_3.json  {"id":3, "blockedBy":[1], "status":"pending"}
  task_4.json  {"id":4, "blockedBy":[2,3], "status":"pending"}

Граф задач (DAG):
                 +----------+
            +--> | задача 2 | --+
            |    | pending  |   |
+----------+     +----------+    +--> +----------+
| задача 1 |                          | задача 4 |
| completed| --> +----------+    +--> | blocked  |
+----------+     | задача 3 | --+     +----------+
                 | pending  |
                 +----------+

Порядок:      задача 1 должна завершиться до 2 и 3
Параллелизм:  задачи 2 и 3 могут выполняться одновременно
Зависимости:  задача 4 ждёт завершения обеих 2 и 3
Статусы:      pending -> in_progress -> completed
```

Этот граф задач становится координационным каркасом для всего, что идёт после s07: фоновое выполнение (s08), многоагентные команды (s09+) и изоляция worktree (s12) — все читают и пишут в эту же структуру.

## Как это работает

1. **TaskManager**: один JSON-файл на задачу, CRUD с графом зависимостей.

```python
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def create(self, subject, description=""):
        task = {"id": self._next_id, "subject": subject,
                "status": "pending", "blockedBy": [],
                "blocks": [], "owner": ""}
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)
```

2. **Разрешение зависимостей**: завершение задачи удаляет её ID из списка `blockedBy` всех других задач, автоматически разблокируя зависящие.

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **Статус + связывание зависимостей**: `update` обрабатывает переходы и рёбра зависимостей.

```python
def update(self, task_id, status=None,
           add_blocked_by=None, add_blocks=None):
    task = self._load(task_id)
    if status:
        task["status"] = status
        if status == "completed":
            self._clear_dependency(task_id)
    self._save(task)
```

4. Четыре инструмента задач добавляются в dispatch map.

```python
TOOL_HANDLERS = {
    # ...базовые инструменты...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

Начиная с s07, граф задач — стандартный инструмент для многошаговой работы. Todo из s03 остаётся для быстрых односессионных чеклистов.

## Что изменилось по сравнению с s06

| Компонент | До (s06) | После (s07) |
|---|---|---|
| Инструменты | 5 | 8 (`task_create/update/list/get`) |
| Модель планирования | Плоский чеклист (в памяти) | Граф задач с зависимостями (на диске) |
| Связи | Нет | Рёбра `blockedBy` + `blocks` |
| Отслеживание статусов | Да/нет | `pending` -> `in_progress` -> `completed` |
| Персистентность | Теряется при сжатии | Переживает сжатие и перезапуски |

## Попробуйте

```sh
cd learn-claude-code
python agents/s07_task_system.py
```

1. `Create 3 tasks: "Setup project", "Write code", "Write tests". Make them depend on each other in order.`
2. `List all tasks and show the dependency graph`
3. `Complete task 1 and then list tasks to see task 2 unblocked`
4. `Create a task board for refactoring: parse -> transform -> emit -> test, where transform and emit can run in parallel after parse`
