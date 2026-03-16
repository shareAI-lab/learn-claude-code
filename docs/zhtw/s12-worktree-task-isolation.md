# s12: Worktree + Task Isolation

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *"Each works in its own directory, no interference"* -- tasks 管目標，worktrees 管目錄，兩者以 ID 綁定。

## 問題

到 s11 為止，agents 已能自主認領並完成任務；但所有任務都在同一個共享目錄執行。若兩個 agents 同時重構不同模組，很容易互相干擾：agent A 改 `config.py`，agent B 也改 `config.py`，未暫存變更混在一起，兩邊都難以乾淨回復。

task board 只管理 *做什麼*，不管理 *在哪裡做*。解法是：每個 task 給一個獨立 git worktree。tasks 管目標，worktrees 管執行上下文，並用 task ID 綁定。

## 解法

```
Control plane (.tasks/)             Execution plane (.worktrees/)
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
                          index.json (worktree registry)
                          events.jsonl (lifecycle log)

State machines:
  Task:     pending -> in_progress -> completed
  Worktree: absent  -> active      -> removed | kept
```

## 運作方式

1. **先建立 task。** 先把目標落地保存。

```python
TASKS.create("Implement auth refactor")
# -> .tasks/task_1.json  status=pending  worktree=""
```

2. **建立 worktree 並綁定 task。** 傳入 `task_id` 後，task 會自動進入 `in_progress`。

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json gets new entry, task_1.json gets worktree="auth-refactor"
```

綁定會同時寫入兩邊狀態：

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

3. **在 worktree 裡執行命令。** `cwd` 指向隔離目錄。

```python
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

4. **收尾。** 有兩種方式：
   - `worktree_keep(name)` -- 保留目錄，之後可繼續用。
   - `worktree_remove(name, complete_task=True)` -- 刪除目錄、完成綁定 task、送出事件。一次呼叫完成 teardown + completion。

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

5. **事件流。** 每個生命週期步驟都會寫進 `.worktrees/events.jsonl`：

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

事件包含：`worktree.create.before/after/failed`、`worktree.remove.before/after/failed`、`worktree.keep`、`task.completed`。

若發生 crash，可透過磁碟上的 `.tasks/` + `.worktrees/index.json` 重建狀態。對話記憶是易失的，檔案狀態才是可持久恢復的。

## 相較 s11 的變更

| Component          | Before (s11)               | After (s12)                                  |
|--------------------|----------------------------|----------------------------------------------|
| Coordination       | Task board (owner/status)  | Task board + explicit worktree binding       |
| Execution scope    | Shared directory           | Task-scoped isolated directory               |
| Recoverability     | Task status only           | Task status + worktree index                 |
| Teardown           | Task completion            | Task completion + explicit keep/remove       |
| Lifecycle visibility | Implicit in logs         | Explicit events in `.worktrees/events.jsonl` |

## 動手試試

```sh
cd learn-claude-code
python agents/s12_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.`
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".`
3. `Run "git status --short" in worktree "auth-refactor".`
4. `Keep worktree "ui-login", then list worktrees and inspect events.`
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.`
