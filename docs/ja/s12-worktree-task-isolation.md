# s12: Worktree + Task Isolation

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *"各自のディレクトリで作業し、互いに干渉しない"* -- タスクは目標を管理、worktree はディレクトリを管理、IDで紐付け。
>
> **Harness 層**: ディレクトリ隔離 -- 決して衝突しない並列実行レーン。

## 問題

s11までにエージェントはタスクを自律的に確保して完了できるようになった。しかし全タスクが1つの共有ディレクトリで走る。2つのエージェントが同時に異なるモジュールをリファクタリングすると衝突する: 片方が`config.py`を編集し、もう片方も`config.py`を編集し、未コミットの変更が混ざり合い、どちらもクリーンにロールバックできない。

タスクボードは*何をやるか*を追跡するが、*どこでやるか*には関知しない。解決策: 各タスクに専用のgit worktreeディレクトリを与える。タスクが目標を管理し、worktreeが実行コンテキストを管理する。タスクIDで紐付ける。

## 解決策

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

## 仕組み

1. **タスクを作成する。** まず目標を永続化する。

```python
TASKS.create("Implement auth refactor")
# -> .tasks/task_1.json  status=pending  worktree=""
```

2. **worktreeを作成してタスクに紐付ける。** `task_id`を渡すと、タスクが自動的に`in_progress`に遷移する。

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json gets new entry, task_1.json gets worktree="auth-refactor"
```

紐付けは両側に状態を書き込む:

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

3. **worktree内でコマンドを実行する。** `cwd`が分離ディレクトリを指す。

```python
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

4. **終了処理。** 2つの選択肢:
   - `worktree_keep(name)` -- ディレクトリを保持する。
   - `worktree_remove(name, complete_task=True)` -- ディレクトリを削除し、紐付けられたタスクを完了し、イベントを発行する。1回の呼び出しで後片付けと完了を処理する。

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

5. **イベントストリーム。** ライフサイクルの各ステップが`.worktrees/events.jsonl`に記録される:

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

発行されるイベント: `worktree.create.before/after/failed`, `worktree.remove.before/after/failed`, `worktree.keep`, `task.completed`。

クラッシュ後も`.tasks/` + `.worktrees/index.json`から状態を再構築できる。会話メモリは揮発性だが、ファイル状態は永続的だ。

## s11からの変更点

| Component          | Before (s11)               | After (s12)                                  |
|--------------------|----------------------------|----------------------------------------------|
| Coordination       | Task board (owner/status)  | Task board + explicit worktree binding       |
| Execution scope    | Shared directory           | Task-scoped isolated directory               |
| Recoverability     | Task status only           | Task status + worktree index                 |
| Teardown           | Task completion            | Task completion + explicit keep/remove       |
| Lifecycle visibility | Implicit in logs         | Explicit events in `.worktrees/events.jsonl` |

## 試してみる

```sh
cd learn-claude-code
python agents/s12_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.`
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".`
3. `Run "git status --short" in worktree "auth-refactor".`
4. `Keep worktree "ui-login", then list worktrees and inspect events.`
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.`
