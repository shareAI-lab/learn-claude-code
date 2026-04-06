# s07: Task System

`s01 > s02 > s03 > s04 > s05 > s06 | [ s07 ] s08 > s09 > s10 > s11 > s12`

> *"Разбивай большие цели на маленькие task, упорядочивай их, сохраняй на диск"* -- файловый граф task с зависимостями, закладывающий основу для многоагентного взаимодействия.
>
> **Harness layer**: Постоянные task -- цели, которые переживают любой отдельный разговор.

## Проблема

TodoManager из s03 — это плоский чек-лист в памяти: без упорядочивания, без зависимостей, без статусов помимо «сделано или нет». Реальные цели имеют структуру -- task B зависит от task A, task C и D можно выполнять параллельно, task E ждёт завершения обеих: C и D.

Без явных связей agent не может определить, что готово к выполнению, что заблокировано и что можно запустить одновременно. А поскольку список живёт только в памяти, сжатие context (s06) полностью его уничтожает.

## Решение

Превратить чек-лист в **граф task**, сохраняемый на диск. Каждый task — это JSON-файл со статусом и зависимостями (`blockedBy`). Граф в любой момент отвечает на три вопроса:

- **Что готово?** -- task со статусом `pending` и пустым `blockedBy`.
- **Что заблокировано?** -- task, ожидающие завершения зависимостей.
- **Что сделано?** -- task со статусом `completed`, завершение которых автоматически разблокирует зависимые task.

```
.tasks/
  task_1.json  {"id":1, "status":"completed"}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending"}
  task_3.json  {"id":3, "blockedBy":[1], "status":"pending"}
  task_4.json  {"id":4, "blockedBy":[2,3], "status":"pending"}

Task graph (DAG):
                 +----------+
            +--> | task 2   | --+
            |    | pending  |   |
+----------+     +----------+    +--> +----------+
| task 1   |                          | task 4   |
| completed| --> +----------+    +--> | blocked  |
+----------+     | task 3   | --+     +----------+
                 | pending  |
                 +----------+

Ordering:     task 1 must finish before 2 and 3
Parallelism:  tasks 2 and 3 can run at the same time
Dependencies: task 4 waits for both 2 and 3
Status:       pending -> in_progress -> completed
```

Этот граф task становится основой координации для всего, что идёт после s07: фоновое выполнение (s08), многоагентные команды (s09+) и изоляция через worktree (s12) -- всё это читает из этой же структуры и пишет в неё.

## Как это работает

1. **TaskManager**: один JSON-файл на task, CRUD с графом зависимостей.

```python
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def create(self, subject, description=""):
        task = {"id": self._next_id, "subject": subject,
                "status": "pending", "blockedBy": [],
                "owner": ""}
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)
```

2. **Разрешение зависимостей**: завершение task удаляет его ID из списка `blockedBy` всех остальных task, автоматически разблокируя зависимые.

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **Статус и управление зависимостями**: `update` обрабатывает переходы состояний и рёбра зависимостей.

```python
def update(self, task_id, status=None,
           add_blocked_by=None, remove_blocked_by=None):
    task = self._load(task_id)
    if status:
        task["status"] = status
        if status == "completed":
            self._clear_dependency(task_id)
    if add_blocked_by:
        task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
    if remove_blocked_by:
        task["blockedBy"] = [x for x in task["blockedBy"] if x not in remove_blocked_by]
    self._save(task)
```

4. Четыре tool для task добавляются в таблицу обработчиков.

```python
TOOL_HANDLERS = {
    # ...base tools...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

Начиная с s07, граф task используется по умолчанию для многошаговых работ. Todo из s03 остаётся для быстрых чек-листов в рамках одной сессии.

## Что изменилось по сравнению с s06

| Компонент | До (s06) | После (s07) |
|---|---|---|
| Tools | 5 | 8 (`task_create/update/list/get`) |
| Модель планирования | Плоский чек-лист (в памяти) | Граф task с зависимостями (на диске) |
| Связи | Отсутствуют | Рёбра `blockedBy` |
| Отслеживание статусов | Сделано или нет | `pending` -> `in_progress` -> `completed` |
| Сохранение | Теряется при сжатии | Переживает сжатие и перезапуски |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s07_task_system.py
```

1. `Create 3 tasks: "Setup project", "Write code", "Write tests". Make them depend on each other in order.`
2. `List all tasks and show the dependency graph`
3. `Complete task 1 and then list tasks to see task 2 unblocked`
4. `Create a task board for refactoring: parse -> transform -> emit -> test, where transform and emit can run in parallel after parse`
