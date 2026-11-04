# s10: Task System — 実行チェックリストから協調できるタスク状態へ

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s08 → s09 → `s10` → [s11](../s11_background_tasks/) → s12 → ... → s16 → s17

> *"大きな目標を小さなタスクに分け、順序付け、永続化"* — ファイル永続化タスクグラフ、マルチ Agent 協調の基盤。
>
> **Harness 層**: タスク — 永続化された目標、復旧可能な進捗。

---

## 課題

s05 の TodoWrite は、Agent が現在のタスクの実行手順を記録するためのものだ。各項目には内容と状態があり、次に何をするべきかを確認できる。

プロジェクトをデータベーステーブルの作成、API の実装、テストの追加という 3 つのタスクに分ける場合、Harness はそれらの関係も把握する必要がある。API はデータベーステーブルの完成を待ち、テストは API の仕様が確定するまで待たなければならない。各タスクの担当者も記録する必要がある。

TodoWrite は、こうした依存関係や担当を記録しない。「API を実装する」が未完了であることは示せても、そのタスクを開始できるかどうかを Harness が判断することはできない。

この章では Task System を追加する。各タスクは個別の ID と状態を持ち、`blockedBy` が前提タスクを、`owner` が担当する Agent を記録する。

---

## ソリューション

![Task System Overview](images/task-system-overview.ja.svg)

コードは S04 の 5 つの基本ツール、Permission、Hooks、共通の `execute_tool` を保ち、そこへ 6 つのタスクツール、`.tasks/` ディレクトリへの永続化、`blockedBy` の依存チェックを追加する。

TodoWrite vs Task System：

| | TodoWrite (s05) | Task System (s10) |
|---|---|---|
| 位置づけ | 現在のタスクの実行チェックリスト | 復旧可能なタスクシステム |
| ストレージ | プロセス内 / セッション状態 | `.tasks/{id}.json` |
| 依存関係 | なし | `blockedBy` 依存グラフ |
| ライフサイクル | 現在のセッション / 現在のタスク | セッション横断 |
| 分担 | タスクの引き受けなし | `owner` / claim |
| ステータス | pending / in_progress / completed | pending / in_progress / completed |
| 粒度 | Agent 自身の手順 | 引き受け・追跡・アンロックできるタスク |
| 更新契約 | リスト全体を置換 | 個別レコードを作成・取得・更新・一覧 |

---

## 仕組み

![Task DAG](images/task-dag.ja.svg)

### Task: データ構造

各タスクは JSON ファイル、`.tasks/` ディレクトリに保存：

```python
@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str          # pending | in_progress | completed
    owner: str | None    # このタスクを担当する Agent
    blockedBy: list[str] # 依存タスク ID のリスト
```

ID は `task_` と 8 桁のランダムな 16 進文字で生成する。ファイルは排他的に作成し、同じ ID が存在する場合は生成し直す。

`TaskStore` はタスク ID を検証し、JSON ファイルを読み書きする。`TASKS = TaskStore(TASKS_DIR)` がこの章で使うタスクストアである。

### create_task: タスク作成

```python
def create_task(subject: str, description: str = "") -> Task:
    return TASKS.create(subject, description)
```

`TaskStore.create` は subject を確認し、ランダム ID を割り当てて `.tasks/{id}.json` に書き込む。新しいタスクの `blockedBy` は常に空で、ツール結果が実行時に生成された ID をモデルへ返す。

### update_task: 返された ID で依存を追加

```python
def update_task(task_id: str, addBlockedBy: list[str]) -> Task:
    return TASKS.update_dependencies(task_id, addBlockedBy)
```

タスクグラフは 2 段階で構築する。まず全ノードを作成し、その後 `create_task` が返した ID を使って `update_task` で辺を追加する。モデルが 1 回の応答で複数のツール呼び出しを出す場合、同じ階層の呼び出しはツール結果が返る前にすべて確定するため、ある `create_task` は別の呼び出しで生成されたばかりの ID を利用できない。

`update_task` は変更全体を検証してから保存する。対象と依存タスクは存在し、対象は pending かつ未所有でなければならず、自己依存や循環も禁止する。既存の辺を再度追加しても重複しない。

### can_start: 依存チェック

タスクは `blockedBy` が**すべて completed** になってからでないと開始できない：

```python
def can_start(task_id: str) -> bool:
    return not incomplete_dependencies(load_task(task_id))
```

`incomplete_dependencies` は各前提タスクを読み込む。completed でないタスクや、ファイルが存在しないタスクが一つでもあれば引き受けられない。

### claim_task: タスクを引き受ける

Agent がタスクに取り掛かる時、`claim_task` を呼び出し、`owner` を設定してステータスを `pending` → `in_progress` に変更する。`owner` フィールドは誰がタスクを引き受けたかを記録する：

```python
def claim_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "pending":
        return f"Task {task_id} is {task.status}, cannot claim"
    dependencies = incomplete_dependencies(task)
    if dependencies:
        return f"Blocked by: {dependencies}"
    task.owner = owner
    task.status = "in_progress"
    TASKS.save(task)
    return f"Claimed {task_id} ({task.subject})"
```

タスクが pending でない場合や、依存が未完了の場合は引き受けを拒否する。S10 はタスクの状態を順番に更新する。

### complete_task: 完了とアンロック

タスク完了後、`completed` に設定。同時に他の全タスクを走査し、**直前にアンロックされた**下流タスクを特定：

```python
def complete_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "in_progress":
        return f"Task {task_id} is {task.status}, cannot complete"
    if task.owner != owner:
        return f"Task {task_id} is owned by {task.owner}, not {owner}"
    ready_before = {t.id for t in list_tasks()
                    if t.status == "pending" and t.blockedBy
                    and can_start(t.id)}
    task.status = "completed"
    TASKS.save(task)
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy
                 and t.id not in ready_before
                 and can_start(t.id)]
    msg = f"Completed {task_id} ({task.subject})"
    if unblocked:
        msg += f"\nUnblocked: {', '.join(unblocked)}"
    return msg
```

"schema" 完了後、"endpoints" と "docs" の `can_start` が True を返し、開始可能になる。

### get_task: 完全な詳細を確認

`list_tasks` は 1 行サマリのみ表示。`get_task` は description と依存関係の詳細を含む完全なタスク JSON を返す。セッションをまたいで復旧する際、Agent は完全な説明を読んで作業を継続する必要がある：

```python
def get_task(task_id: str) -> str:
    task = load_task(task_id)
    return json.dumps(asdict(task), indent=2)
```

### 状態マシン: 2 つのアクション、3 つの状態

```
pending ──claim──→ in_progress ──complete──→ completed
```

ここで `claim` / `complete` はアクション、`pending` / `in_progress` / `completed` は状態：

- **claim_task**: `pending` → `in_progress`。owner を設定し、作業を開始。
- **complete_task**: `in_progress` → `completed`。タスクを完了済みにし、下流をアンロック。

### 組み合わせて実行

```python
# 第 1 段階：全ノードを作成して実行時 ID を受け取る
schema = create_task("setup database schema")
endpoints = create_task("create API endpoints")
tests = create_task("write tests")
docs = create_task("write docs")

# 第 2 段階：返された ID で依存の辺を追加する
update_task(endpoints.id, addBlockedBy=[schema.id])
update_task(tests.id, addBlockedBy=[endpoints.id])
update_task(docs.id, addBlockedBy=[schema.id])

# Agent が最初に実行可能なタスクを引き受ける
claim_task(schema.id)       # ✓ Claimed（依存なし）
complete_task(schema.id)    # ✓ Completed → endpoints, docs をアンロック

claim_task(endpoints.id)    # ✓ Claimed（schema 完了済み）
complete_task(endpoints.id) # ✓ Completed → tests をアンロック

claim_task(docs.id)         # ✓ Claimed（schema 完了済み）
complete_task(docs.id)      # ✓ Completed

claim_task(tests.id)        # ✓ Claimed（endpoints 完了済み）
complete_task(tests.id)     # ✓ Completed
```

各 `create_task` が JSON ファイルを書き込み、`update_task`、`claim_task`、`complete_task` がファイルを更新する。セッションをまたいでも `.tasks/` ディレクトリが残り、Agent はファイルを読んで進捗を復旧できる。

---

## 試してみる

```sh
cd learn-claude-code
python s10_task_system/code.py
```

以下のプロンプトを試してください：

1. `Create tasks: setup database schema, create API endpoints (depends on schema), write tests (depends on endpoints), write docs (depends on schema)`
2. `List all tasks and their statuses`
3. `Claim the first unblocked task and complete it`
4. `List tasks again — which ones are now unblocked?`

観察ポイント：`.tasks/` ディレクトリに JSON ファイルが生成されているか？タスク完了後、ブロックされていたタスクがアンロックされているか？

---

## 次の章

タスクグラフができても、全テストの実行、依存関係のインストール、デプロイなどのコマンドには長い時間がかかることがある。これらのコマンドを同期実行すると、Agent Loop は現在のツール呼び出しでブロックされ、コマンドが終了するまで他の処理を続けられない。

s11 Background Tasks → 遅い操作をバックグラウンドで実行する。Agent は他のタスクの処理を続け、バックグラウンド処理の完了後に通知を受け取る。


<!-- translation-sync: zh@v5, en@v5, ja@v5 -->
