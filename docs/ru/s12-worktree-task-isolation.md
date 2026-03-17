# s12: Worktree + Изоляция задач

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *«Каждый работает в своей директории, без помех»* — задачи управляют целями, worktree управляют директориями, связанными по ID.

## Проблема

К s11 агенты могут самостоятельно захватывать и выполнять задачи. Но каждая задача выполняется в одной общей директории. Два агента, рефакторящих разные модули одновременно, столкнутся: агент А редактирует `config.py`, агент Б редактирует `config.py`, несохранённые изменения смешиваются, и ни один не может откатить чисто.

Доска задач отслеживает *что делать*, но не имеет мнения о *где это делать*. Решение: дать каждой задаче собственную git worktree директорию. Задачи управляют целями, worktree управляют контекстом выполнения. Связываем их по ID задачи.

## Решение

```
Плоскость управления (.tasks/)      Плоскость выполнения (.worktrees/)
+------------------+                +------------------------+
| task_1.json      |                | auth-refactor/         |
|   status: in_progress  <------>   branch: wt/auth-refactor
|   worktree: "auth-refactor"   |   task_id: 1             |
+------------------+                +------------------------+
| task_2.json      |                | ui-login/              |
|   status: pending    <------>     branch: wt/ui-login
|   worktree: "ui-login"       |   task_id: 2             |
+------------------+                +------------------------+
                                    |
                          index.json (реестр worktree)
                          events.jsonl (лог жизненного цикла)

Автоматы состояний:
  Задача:   pending -> in_progress -> completed
  Worktree: absent  -> active      -> removed | kept
```

## Как это работает

1. **Создать задачу.** Сначала сохраняем цель.

```python
TASKS.create("Implement auth refactor")
# -> .tasks/task_1.json  status=pending  worktree=""
```

2. **Создать worktree и привязать к задаче.** Передача `task_id` автоматически переводит задачу в `in_progress`.

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json получает новую запись, task_1.json получает worktree="auth-refactor"
```

Привязка записывает состояние с обеих сторон:

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

3. **Выполнять команды в worktree.** `cwd` указывает на изолированную директорию.

```python
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

4. **Завершить работу.** Два варианта:
   - `worktree_keep(name)` — сохранить директорию для дальнейшего использования.
   - `worktree_remove(name, complete_task=True)` — удалить директорию, завершить привязанную задачу, записать событие. Один вызов обрабатывает демонтаж + завершение.

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

5. **Поток событий.** Каждый шаг жизненного цикла записывается в `.worktrees/events.jsonl`:

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

Записываемые события: `worktree.create.before/after/failed`, `worktree.remove.before/after/failed`, `worktree.keep`, `task.completed`.

После сбоя состояние восстанавливается из `.tasks/` + `.worktrees/index.json` на диске. Память разговора изменчива; состояние файлов долговечно.

## Что изменилось по сравнению с s11

| Компонент          | До (s11)                   | После (s12)                                  |
|--------------------|----------------------------|----------------------------------------------|
| Координация        | Доска задач (владелец/статус)| Доска задач + явная привязка worktree        |
| Область выполнения | Общая директория           | Изолированная директория для каждой задачи   |
| Восстанавливаемость| Только статус задачи       | Статус задачи + индекс worktree              |
| Демонтаж           | Завершение задачи          | Завершение задачи + явный keep/remove        |
| Видимость ЖЦ       | Неявно в логах             | Явные события в `.worktrees/events.jsonl`    |

## Попробуйте

```sh
cd learn-claude-code
python agents/s12_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.`
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".`
3. `Run "git status --short" in worktree "auth-refactor".`
4. `Keep worktree "ui-login", then list worktrees and inspect events.`
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.`
