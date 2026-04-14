# Team Task Lane Model

> `s15-s18` に入ると、関数名よりも先に混ざりやすいものがあります。
>
> それは、
>
> **誰が働き、誰が調整し、何が目標を記録し、何が実行レーンを提供しているのか**
>
> という層の違いです。

## この橋渡し資料が解決すること

`s15-s18` を通して読むと、次の言葉が一つの曖昧な塊になりやすくなります。

- teammate
- protocol request
- task
- runtime task
- worktree

全部「仕事が進む」ことに関係していますが、同じ層ではありません。

ここを分けないと、後半が急に分かりにくくなります。

- teammate は task と同じなのか
- `request_id` と `task_id` は何が違うのか
- worktree は runtime task の一種なのか
- task が終わっているのに、なぜ worktree が kept のままなのか

この資料は、その層をきれいに分けるためのものです。

## 読む順番

1. [`s15-agent-teams.md`](./s15-agent-teams.md) で長寿命 teammate を確認する
2. [`s16-team-protocols.md`](./s16-team-protocols.md) で追跡可能な request-response を確認する
3. [`s17-autonomous-agents.md`](./s17-autonomous-agents.md) で自律 claim を確認する
4. [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md) で隔離 execution lane を確認する

用語が混ざってきたら、次も見直してください。

- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## まずはこの区別を固定する

```text
teammate
  = 長期に協力する主体

protocol request
  = チーム内で追跡される調整要求

task
  = 何をやるべきか

runtime task / execution slot
  = 今まさに動いている実行単位

worktree
  = 他の変更とぶつからずに仕事を進める実行ディレクトリ
```

特に混ざりやすいのは最後の3つです。

- `task`
- `runtime task`
- `worktree`

毎回、次の3つを別々に問い直してください。

- これは目標か
- これは実行中の単位か
- これは隔離された実行ディレクトリか

## 一番小さい図

```text
Team Layer
  teammate: alice (frontend)

Protocol Layer
  request_id=req_01
  kind=plan_approval
  status=pending

Work Graph Layer
  task_id=12
  subject="Implement login page"
  owner="alice"
  status="in_progress"

Runtime Layer
  runtime_id=rt_01
  type=in_process_teammate
  status=running

Execution Lane Layer
  worktree=login-page
  path=.worktrees/login-page
  status=active
```

この中で、仕事そのものの目標を表しているのは一つだけです。

> `task_id=12`

他は、その目標のまわりで協調・実行・分離を支える層です。

## 1. Teammate: 誰が協力しているか

`s15` で導入される層です。

ここが答えること：

- 長寿命 worker の名前
- 役割
- `working` / `idle` / `shutdown`
- 独立した inbox を持つか

例：

```python
member = {
    "name": "alice",
    "role": "frontend",
    "status": "idle",
}
```

大事なのは「agent をもう1個増やす」ことではありません。

> 繰り返し仕事を受け取れる長寿命の身元

これが本質です。

## 2. Protocol Request: 何を調整しているか

`s16` の層です。

ここが答えること：

- 誰が誰に依頼したか
- どんな種類の request か
- pending なのか、もう解決済みなのか

例：

```python
request = {
    "request_id": "a1b2c3d4",
    "kind": "plan_approval",
    "from": "alice",
    "to": "lead",
    "status": "pending",
}
```

これは普通の会話ではありません。

> 状態更新を続けられる調整記録

です。

## 3. Task: 何をやるのか

これは `s12` の durable work-graph task であり、`s17` で teammate が claim する対象です。

ここが答えること：

- 目標は何か
- 誰が担当しているか
- 何にブロックされているか
- 進捗状態はどうか

例：

```python
task = {
    "id": 12,
    "subject": "Implement login page",
    "status": "in_progress",
    "owner": "alice",
    "blockedBy": [],
}
```

キーワードは：

**目標**

ディレクトリでも、protocol でも、process でもありません。

## 4. Runtime Task / Execution Slot: 今なにが走っているか

この層は `s13` の橋渡し資料ですでに説明されていますが、`s15-s18` ではさらに重要になります。

例：

- background shell が走っている
- 長寿命 teammate が今作業している
- monitor が外部状態を見ている

これらは、

> 実行中の slot

として理解するのが一番きれいです。

例：

```python
runtime = {
    "id": "rt_01",
    "type": "in_process_teammate",
    "status": "running",
    "work_graph_task_id": 12,
}
```

大事な境界：

- 1つの task から複数の runtime task が派生しうる
- runtime task は durable な目標そのものではなく、実行インスタンスである

## 5. Worktree: どこでやるのか

`s18` で導入される execution lane 層です。

ここが答えること：

- どの隔離ディレクトリを使うか
- どの task と結び付いているか
- その lane は `active` / `kept` / `removed` のどれか

例：

```python
worktree = {
    "name": "login-page",
    "path": ".worktrees/login-page",
    "task_id": 12,
    "status": "active",
}
```

キーワードは：

**実行境界**

task そのものではなく、その task を進めるための隔離レーンです。

## 層はどうつながるか

```text
teammate
  protocol request で協調し
  task を claim し
  execution slot として走り
  worktree lane の中で作業する
```

もっと具体的に言うなら：

> `alice` が `task #12` を claim し、`login-page` worktree lane の中でそれを進める

この言い方は、

> "alice is doing the login-page worktree task"

のような曖昧な言い方よりずっと正確です。

後者は次の3層を一つに潰してしまいます。

- teammate
- task
- worktree

## よくある間違い

### 1. teammate と task を同じものとして扱う

teammate は実行者、task は目標です。

### 2. `request_id` と `task_id` を同じ種類の ID だと思う

片方は調整、片方は目標です。

### 3. runtime slot を durable task だと思う

実行は終わっても、durable task は残ることがあります。

### 4. worktree を task そのものだと思う

worktree は execution lane でしかありません。

### 5. 「並列で動く」とだけ言って層の名前を出さない

良い教材は「agent がたくさんいる」で止まりません。

次のように言える必要があります。

> teammate は長期協力を担い、request は調整を追跡し、task は目標を記録し、runtime slot は実行を担い、worktree は実行ディレクトリを隔離する。

## 読み終えたら言えるようになってほしいこと

1. `s17` の自律 claim は `s12` の work-graph task を取るのであって、`s13` の runtime slot を取るのではない。
2. `s18` の worktree は task に execution lane を結び付けるのであって、task をディレクトリへ変えるのではない。
