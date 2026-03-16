# s07: Task System

`s01 > s02 > s03 > s04 > s05 > s06 | [ s07 ] s08 > s09 > s10 > s11 > s12`

> *"Break big goals into small tasks, order them, persist to disk"* -- 檔案式 task graph（含 dependencies），是 multi-agent 協作的基礎。

## 問題

s03 的 TodoManager 只是記憶體中的平面 checklist：沒有順序、沒有 dependencies、狀態也只有做完或沒做完。真實目標往往有結構 -- task B 依賴 task A、tasks C 與 D 可平行、task E 要等 C 與 D 都完成。

沒有明確關係，agent 就無法判斷哪些可做、哪些被卡住、哪些可同時進行。而且清單只在記憶體裡，經過 context compression（s06）就會被洗掉。

## 解法

把 checklist 升級成「落地到磁碟」的 **task graph**。每個 task 都是一個 JSON 檔案，包含 status、dependencies（`blockedBy`）與 dependents（`blocks`）。這張圖會即時回答三個問題：

- **哪些可做？** -- `pending` 且 `blockedBy` 為空的 tasks。
- **哪些被卡住？** -- 正在等待未完成 dependencies 的 tasks。
- **哪些已完成？** -- `completed` tasks；完成時會自動解除 dependents 的阻塞。

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

這個 task graph 從 s07 開始成為協作主幹：s08 的背景執行、s09+ 的多 agent 團隊、s12 的 worktree 隔離，都會讀寫同一套結構。

## 運作方式

1. **TaskManager**：每個 task 一個 JSON 檔，提供含 dependency graph 的 CRUD。

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

2. **Dependency resolution**：task 完成後，會把自己的 ID 從其他 task 的 `blockedBy` 清掉，自動解鎖 dependents。

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **Status + dependency wiring**：`update` 同時處理狀態遷移與 dependency 關係。

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

4. 四個 task 工具加入 dispatch map。

```python
TOOL_HANDLERS = {
    # ...base tools...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

從 s07 開始，task graph 是預設的多步任務模型；s03 的 Todo 則保留給單次 session 的快速 checklist。

## 相較 s06 的變更

| Component | Before (s06) | After (s07) |
|---|---|---|
| Tools | 5 | 8 (`task_create/update/list/get`) |
| Planning model | Flat checklist (in-memory) | Task graph with dependencies (on disk) |
| Relationships | None | `blockedBy` + `blocks` edges |
| Status tracking | Done or not | `pending` -> `in_progress` -> `completed` |
| Persistence | Lost on compression | Survives compression and restarts |

## 動手試試

```sh
cd learn-claude-code
python agents/s07_task_system.py
```

1. `Create 3 tasks: "Setup project", "Write code", "Write tests". Make them depend on each other in order.`
2. `List all tasks and show the dependency graph`
3. `Complete task 1 and then list tasks to see task 2 unblocked`
4. `Create a task board for refactoring: parse -> transform -> emit -> test, where transform and emit can run in parallel after parse`
