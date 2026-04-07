# s13a: Runtime Task Model

> この bridge doc はすぐに混ざる次の点をほどくためのものです。
>
> **work graph 上の task と、いま実行中の task は同じものではありません。**

## 主線とどう併読するか

次の順で読むのが最も分かりやすいです。

- まず [`s12-task-system.md`](./s12-task-system.md) を読み、durable な work graph を固める
- 次に [`s13-background-tasks.md`](./s13-background-tasks.md) を読み、background execution を見る
- 用語が混ざり始めたら [`glossary.md`](./glossary.md) を見直す
- field を正確に合わせたいなら [`data-structures.md`](./data-structures.md) と [`entity-map.md`](./entity-map.md) を見直す

## なぜこの橋渡しが必要か

主線自体は正しいです。

- `s12` は task system
- `s13` は background tasks

ただし bridge layer を一枚挟まないと、読者は二種類の「task」をすぐに同じ箱へ入れてしまいます。

例えば:

- 「auth module を実装する」という work-graph task
- 「pytest を走らせる」という background execution
- 「alice がコード修正をしている」という teammate execution

どれも日常語では task と呼べますが、同じ層にはありません。

## 二つの全く違う task

### 1. work-graph task

これは `s12` の durable node です。

答えるものは:

- 何をやるか
- どの仕事がどの仕事に依存するか
- 誰が owner か
- 進捗はどうか

つまり:

> 目標として管理される durable work unit

です。

### 2. runtime task

こちらが答えるものは:

- 今どの execution unit が生きているか
- それが何の type か
- running / completed / failed / killed のどれか
- 出力がどこにあるか

つまり:

> runtime の中で生きている execution slot

です。

## 最小の心智モデル

まず二つの表として分けて考えてください。

```text
work-graph task
  - durable
  - goal / dependency oriented
  - 寿命が長い

runtime task
  - execution oriented
  - output / status oriented
  - 寿命が短い
```

両者の関係は「どちらか一方」ではありません。

```text
1 つの work-graph task
  から
1 個以上の runtime task が派生しうる
```

例えば:

```text
work-graph task:
  "Implement auth module"

runtime tasks:
  1. background で test を走らせる
  2. coder teammate を起動する
  3. 外部 service を monitor する
```

## なぜこの区別が重要か

この境界が崩れると、後続章がすぐに絡み始めます。

- `s13` の background execution が `s12` の task board と混ざる
- `s15-s17` の teammate work がどこにぶら下がるか不明になる
- `s18` の worktree が何に紐づくのか曖昧になる

最短の正しい要約はこれです。

**work-graph task は目標を管理し、runtime task は実行を管理する**

## 主要 record

### 1. `WorkGraphTaskRecord`

これは `s12` の durable task です。

```python
task = {
    "id": 12,
    "subject": "Implement auth module",
    "status": "in_progress",
    "blockedBy": [],
    "blocks": [13],
    "owner": "alice",
    "worktree": "auth-refactor",
}
```

### 2. `RuntimeTaskState`

教材版の最小形は次の程度で十分です。

```python
runtime_task = {
    "id": "b8k2m1qz",
    "type": "local_bash",
    "status": "running",
    "description": "Run pytest",
    "start_time": 1710000000.0,
    "end_time": None,
    "output_file": ".task_outputs/b8k2m1qz.txt",
    "notified": False,
}
```

重要 field は:

- `type`: どの execution unit か
- `status`: active か terminal か
- `output_file`: 結果がどこにあるか
- `notified`: 結果を system がもう表に出したか

### 3. `RuntimeTaskType`

教材 repo ですべての type を即実装する必要はありません。

ただし runtime task は単なる shell 1 種ではなく、型族だと読者に見せるべきです。

最小表は:

```text
local_bash
local_agent
remote_agent
in_process_teammate
monitor
workflow
```

## 最小実装の進め方

### Step 1: `s12` の task board はそのまま保つ

ここへ runtime state を混ぜないでください。

### Step 2: 別の runtime task manager を足す

```python
class RuntimeTaskManager:
    def __init__(self):
        self.tasks = {}
```

### Step 3: background work 開始時に runtime task を作る

```python
def spawn_bash_task(command: str):
    task_id = new_runtime_id()
    runtime_tasks[task_id] = {
        "id": task_id,
        "type": "local_bash",
        "status": "running",
        "description": command,
    }
```

### Step 4: 必要なら work graph へ結び戻す

```python
runtime_tasks[task_id]["work_graph_task_id"] = 12
```

初日から必須ではありませんが、teams や worktrees へ進むほど重要になります。

## 開発者が持つべき図

```text
Work Graph
  task #12: Implement auth module
        |
        +-- runtime task A: local_bash (pytest)
        +-- runtime task B: local_agent (coder worker)
        +-- runtime task C: monitor (watch service status)

Runtime Task Layer
  A/B/C each have:
  - own runtime ID
  - own status
  - own output
  - own lifecycle
```

## 後続章とのつながり

この層が明確になると、後続章がかなり読みやすくなります。

- `s13` の background command は runtime task
- `s15-s17` の teammate も runtime task の一種として見られる
- `s18` の worktree は主に durable work に紐づくが runtime execution にも影響する
- `s19` の monitor や async external work も runtime layer に落ちうる

「裏で生きていて仕事を進めているもの」を見たら、まず二つ問います。

- これは work graph 上の durable goal か
- それとも runtime 上の live execution slot か

## 初学者がやりがちな間違い

### 1. background shell の state を task board に直接入れる

durable task state と runtime execution state が混ざります。

### 2. 1 つの work-graph task は 1 つの runtime task しか持てないと思う

現実の system では、1 つの goal から複数 execution unit が派生することは普通です。

### 3. 両層で同じ status 語彙を使い回す

例えば:

- durable tasks: `pending / in_progress / completed`
- runtime tasks: `running / completed / failed / killed`

可能な限り分けた方が安全です。

### 4. `output_file` や `notified` のような runtime 専用 field を軽視する

durable task board はそこまで気にしませんが、runtime layer は強く依存します。
