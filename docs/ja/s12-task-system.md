# s12: Task System

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *"大きな目標を小タスクに分解し、順序付けし、ディスクに記録する"* -- ファイルベースのタスクグラフ、マルチエージェント協調の基盤。
>
> **Harness 層**: 永続タスク -- どの会話よりも長く生きる目標。

## 問題

s03のTodoManagerはメモリ上のフラットなチェックリストに過ぎない: 順序なし、依存関係なし、ステータスは完了か未完了のみ。実際の目標には構造がある -- タスクBはタスクAに依存し、タスクCとDは並行実行でき、タスクEはCとDの両方を待つ。

明示的な関係がなければ、エージェントは何が実行可能で、何がブロックされ、何が同時に走れるかを判断できない。しかもリストはメモリ上にしかないため、コンテキスト圧縮(s06)で消える。

## 主線とどう併読するか

- `s03` からそのまま来たなら、[`data-structures.md`](./data-structures.md) へ戻って `TodoItem` / `PlanState` と `TaskRecord` を分けます。
- object 境界が混ざり始めたら、[`entity-map.md`](./entity-map.md) で message、task、runtime task、teammate を分離してから戻ります。
- 次に `s13` を読むなら、[`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) を横に置いて、durable task と runtime task を同じ言葉で潰さないようにします。

## 解決策

フラットなチェックリストをディスクに永続化する**タスクグラフ**に昇格させる。各タスクは1つのJSONファイルで、ステータス・前方依存(`blockedBy`)を持つ。タスクグラフは常に3つの問いに答える:

- **何が実行可能か?** -- `pending`ステータスで`blockedBy`が空のタスク。
- **何がブロックされているか?** -- 未完了の依存を待つタスク。
- **何が完了したか?** -- `completed`のタスク。完了時に後続タスクを自動的にアンブロックする。

```
.tasks/
  task_1.json  {"id":1, "status":"completed"}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending"}
  task_3.json  {"id":3, "blockedBy":[1], "status":"pending"}
  task_4.json  {"id":4, "blockedBy":[2,3], "status":"pending"}

タスクグラフ (DAG):
                 +----------+
            +--> | task 2   | --+
            |    | pending  |   |
+----------+     +----------+    +--> +----------+
| task 1   |                          | task 4   |
| completed| --> +----------+    +--> | blocked  |
+----------+     | task 3   | --+     +----------+
                 | pending  |
                 +----------+

順序:       task 1 は 2 と 3 より先に完了する必要がある
並行:       task 2 と 3 は同時に実行できる
依存:       task 4 は 2 と 3 の両方を待つ
ステータス: pending -> in_progress -> completed
```

このタスクグラフは後続の runtime / platform 章の協調バックボーンになる: バックグラウンド実行(`s13`)、マルチエージェントチーム(`s15+`)、worktree 分離(`s18`)はすべてこの durable な構造の恩恵を受ける。

## 仕組み

1. **TaskManager**: タスクごとに1つのJSONファイル、依存グラフ付きCRUD。

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

2. **依存解除**: タスク完了時に、他タスクの`blockedBy`リストから完了IDを除去し、後続タスクをアンブロックする。

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **ステータス遷移 + 依存配線**: `update`がステータス変更と依存エッジを担う。

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

4. 4つのタスクツールをディスパッチマップに追加する。

```python
TOOL_HANDLERS = {
    # ...base tools...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

`s12` 以降、タスクグラフが durable なマルチステップ作業のデフォルトになる。`s03` の Todo は軽量な単一セッション用チェックリストとして残る。

## s06からの変更点

| コンポーネント | Before (s06) | After (s12) |
|---|---|---|
| Tools | 5 | 8 (`task_create/update/list/get`) |
| 計画モデル | フラットチェックリスト (メモリ) | 依存関係付きタスクグラフ (ディスク) |
| 関係 | なし | `blockedBy` エッジ |
| ステータス追跡 | 完了か未完了 | `pending` -> `in_progress` -> `completed` |
| 永続性 | 圧縮で消失 | 圧縮・再起動後も存続 |

## 試してみる

```sh
cd learn-claude-code
python agents/s12_task_system.py
```

1. `Create 3 tasks: "Setup project", "Write code", "Write tests". Make them depend on each other in order.`
2. `List all tasks and show the dependency graph`
3. `Complete task 1 and then list tasks to see task 2 unblocked`
4. `Create a task board for refactoring: parse -> transform -> emit -> test, where transform and emit can run in parallel after parse`

## 教学上の境界

このリポジトリで本当に重要なのは、完全な製品向け保存層の再現ではありません。

重要なのは:

- durable なタスク記録
- 明示的な依存エッジ
- 分かりやすい状態遷移
- 後続章が再利用できる構造

この 4 点を自分で実装できれば、タスクシステムの核心はつかめています。
