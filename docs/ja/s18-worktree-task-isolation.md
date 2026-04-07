# s18: Worktree + Task Isolation

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > [ s18 ] > s19`

> *task board が答えるのは「何をやるか」、worktree が答えるのは「どこでやるか、しかも互いに踏み荒らさずに」です。*

## この章が解く問題

`s17` までで system はすでに次のことができます。

- task を作る
- teammate が task を claim する
- 複数の teammate が並行に作業する

それでも、全員が同じ working directory で作業するなら、すぐに限界が来ます。

典型的な壊れ方は次の通りです。

- 2 つの task が同じ file を同時に編集する
- 片方の未完了変更がもう片方の task を汚染する
- 「この task の変更だけ見たい」が非常に難しくなる

つまり `s12-s17` までで答えられていたのは、

**誰が何をやるか**

までであって、

**その仕事をどの execution lane で進めるか**

はまだ答えられていません。

それを担当するのが `worktree` です。

## 併読すると楽になる資料

- task / runtime slot / worktree lane が同じものに見えたら [`team-task-lane-model.md`](./team-task-lane-model.md)
- task record と worktree record に何を保存すべきか確認したいなら [`data-structures.md`](./data-structures.md)
- なぜ worktree の章が tasks / teams より後ろに来るか再確認したいなら [`s00e-reference-module-map.md`](./s00e-reference-module-map.md)

## 先に言葉をそろえる

### worktree とは何か

Git に慣れている人なら、

> 同じ repository を別ディレクトリへ独立 checkout した作業コピー

と見て構いません。

まだ Git の言葉に慣れていないなら、まずは次の理解で十分です。

> 1 つの task に割り当てる専用の作業レーン

### isolation とは何か

`isolation` は、

> task A は task A の directory で実行し、task B は task B の directory で実行して、未コミット変更を最初から共有しないこと

です。

### binding とは何か

`binding` は、

> task ID と worktree record を明示的に結びつけること

です。

これがないと、system は「この directory が何のために存在しているのか」を説明できません。

## 最小心智モデル

この章は 2 枚の表を別物として見ると一気に分かりやすくなります。

```text
Task Board
  - 何をやるか
  - 誰が持っているか
  - 今どの状態か

Worktree Registry
  - どこでやるか
  - どの branch / path か
  - どの task に結び付いているか
```

両者は `task_id` でつながります。

```text
.tasks/task_12.json
  {
    "id": 12,
    "subject": "Refactor auth flow",
    "status": "in_progress",
    "worktree": "auth-refactor"
  }

.worktrees/index.json
  {
    "worktrees": [
      {
        "name": "auth-refactor",
        "path": ".worktrees/auth-refactor",
        "branch": "wt/auth-refactor",
        "task_id": 12,
        "status": "active"
      }
    ]
  }
```

この 2 つを見て、

- task は goal を記録する
- worktree は execution lane を記録する

と分けて理解できれば、この章の幹はつかめています。

## この章の核になるデータ構造

### 1. TaskRecord 側の lane 情報

この段階の教材コードでは、task 側に単に `worktree` という名前だけがあるわけではありません。

```python
task = {
    "id": 12,
    "subject": "Refactor auth flow",
    "status": "in_progress",
    "owner": "alice",
    "worktree": "auth-refactor",
    "worktree_state": "active",
    "last_worktree": "auth-refactor",
    "closeout": None,
}
```

それぞれの意味は次の通りです。

- `worktree`: 今この task がどの lane に結び付いているか
- `worktree_state`: その lane が `active` / `kept` / `removed` / `unbound` のどれか
- `last_worktree`: 直近で使っていた lane 名
- `closeout`: 最後にどういう終わらせ方をしたか

ここが重要です。

task 側はもはや単に「現在の directory 名」を持っているだけではありません。

**いま結び付いている lane と、最後にどう閉じたかまで記録し始めています。**

### 2. WorktreeRecord

worktree registry 側の record は path の写しではありません。

```python
worktree = {
    "name": "auth-refactor",
    "path": ".worktrees/auth-refactor",
    "branch": "wt/auth-refactor",
    "task_id": 12,
    "status": "active",
    "last_entered_at": 1710000000.0,
    "last_command_at": 1710000012.0,
    "last_command_preview": "pytest tests/auth -q",
    "closeout": None,
}
```

ここで答えているのは path だけではありません。

- いつ lane に入ったか
- 最近何を実行したか
- どんな closeout が最後に行われたか

つまり worktree record は、

**directory mapping ではなく、観測可能な execution lane record**

です。

### 3. CloseoutRecord

closeout は「最後に削除したかどうか」だけではありません。

教材コードでは次のような record を残します。

```python
closeout = {
    "action": "keep",
    "reason": "Need follow-up review",
    "at": 1710000100.0,
}
```

これにより system は、

- keep したのか
- remove したのか
- なぜそうしたのか

を state として残せます。

初心者にとって大事なのはここです。

**closeout は単なる cleanup コマンドではなく、execution lane の終わり方を明示する操作**

です。

### 4. Event Record

worktree は lifecycle が長いので event log も必要です。

```python
{
    "event": "worktree.closeout.keep",
    "task_id": 12,
    "worktree": "auth-refactor",
    "reason": "Need follow-up review",
    "ts": 1710000100.0,
}
```

なぜ state file だけでは足りないかというと、lane の lifecycle には複数段階があるからです。

- create
- enter
- run
- keep
- remove
- remove failed

append-only の event があれば、いまの最終状態だけでなく、

**そこへ至る途中の挙動**

も追えます。

## 最小実装を段階で追う

### 第 1 段階: 先に task を作り、そのあと lane を作る

順番は非常に大切です。

```python
task = tasks.create("Refactor auth flow")
worktrees.create("auth-refactor", task_id=task["id"])
```

この順番にする理由は、

**worktree は task の代替ではなく、task にぶら下がる execution lane**

だからです。

最初に goal があり、そのあと goal に lane を割り当てます。

### 第 2 段階: worktree を作り、registry に書く

```python
def create(self, name: str, task_id: int):
    path = self.root / ".worktrees" / name
    branch = f"wt/{name}"

    run_git(["worktree", "add", "-b", branch, str(path), "HEAD"])

    record = {
        "name": name,
        "path": str(path),
        "branch": branch,
        "task_id": task_id,
        "status": "active",
    }
    self.index["worktrees"].append(record)
    self._save_index()
```

ここで registry は次を答えられるようになります。

- lane 名
- 実 directory
- branch
- 対応 task
- active かどうか

### 第 3 段階: task record 側も同時に更新する

lane registry を書くだけでは不十分です。

```python
def bind_worktree(task_id: int, name: str):
    task = tasks.load(task_id)
    task["worktree"] = name
    task["last_worktree"] = name
    task["worktree_state"] = "active"
    if task["status"] == "pending":
        task["status"] = "in_progress"
    tasks.save(task)
```

なぜ両側へ書く必要があるか。

もし registry だけ更新して task board 側を更新しなければ、

- task 一覧から lane が見えない
- closeout 時にどの task を終わらせるか分かりにくい
- crash 後の再構成が不自然になる

からです。

### 第 4 段階: lane に入ることと、lane で command を実行することを分ける

教材コードでは `enter` と `run` を分けています。

```python
worktree_enter("auth-refactor")
worktree_run("auth-refactor", "pytest tests/auth -q")
```

底では本質的に次のことをしています。

```python
def enter(self, name: str):
    self._update_entry(name, last_entered_at=time.time())
    self.events.emit("worktree.enter", ...)

def run(self, name: str, command: str):
    subprocess.run(command, cwd=worktree_path, ...)
```

特に大事なのは `cwd=worktree_path` です。

同じ `pytest` でも、どの `cwd` で走るかによって影響範囲が変わります。

`enter` を別操作として教える理由は、読者に次の境界を見せるためです。

- lane を割り当てた
- 実際にその lane へ入った
- その lane で command を実行した

この 3 段階が分かれているからこそ、

- `last_entered_at`
- `last_command_at`
- `last_command_preview`

のような観測項目が自然に見えてきます。

### 第 5 段階: 終わるときは closeout を明示する

教材上は、`keep` と `remove` をバラバラの小技として見せるより、

> closeout という 1 つの判断に 2 分岐ある

と見せた方が心智が安定します。

```python
worktree_closeout(
    name="auth-refactor",
    action="keep",  # or "remove"
    reason="Need follow-up review",
    complete_task=False,
)
```

これで読者は次のことを一度に理解できます。

- lane の終わらせ方には選択肢がある
- その選択には理由を持たせられる
- closeout は task record / lane record / event log に反映される

もちろん実装下層では、

- `worktree_keep(name)`
- `worktree_remove(name, reason=..., complete_task=True)`

のような分離 API を持っていても構いません。

ただし教学の主線では、

**closeout decision -> keep / remove**

という形にまとめた方が初心者には伝わります。

## なぜ `status` と `worktree_state` を分けるのか

これは非常に大事な区別です。

初学者はよく、

> task に `status` があるなら十分ではないか

と考えます。

しかし実際は答えている質問が違います。

- `task.status`: その仕事が `pending` / `in_progress` / `completed` のどれか
- `worktree_state`: その execution lane が `active` / `kept` / `removed` / `unbound` のどれか

たとえば、

```text
task は completed
でも worktree は kept
```

という状態は自然に起こります。

review 用に directory を残しておきたいからです。

したがって、

**goal state と lane state は同じ field に潰してはいけません。**

## なぜ worktree は「Git の小技」で終わらないのか

初見では「別 directory を増やしただけ」に見えるかもしれません。

でも教学上の本質はそこではありません。

本当に重要なのは、

**task と execution directory の対応関係を明示 record として持つこと**

です。

それがあるから system は、

- どの lane がどの task に属するか
- 完了時に何を closeout すべきか
- crash 後に何を復元すべきか

を説明できます。

## 前の章とどうつながるか

この章は前段を次のように結びます。

- `s12`: task ID を与える
- `s15-s17`: teammate と claim を与える
- `s18`: 各 task に独立 execution lane を与える

流れで書くとこうです。

```text
task を作る
  ->
teammate が claim する
  ->
system が worktree lane を割り当てる
  ->
commands がその lane の directory で走る
  ->
終了時に keep / remove を選ぶ
```

ここまで来ると multi-agent の並行作業が「同じ場所に集まる chaos」ではなく、

**goal と lane を分けた協調システム**

として見えてきます。

## worktree は task そのものではない

ここは何度でも繰り返す価値があります。

- task は「何をやるか」
- worktree は「どこでやるか」

です。

同様に、

- runtime slot は「今動いている execution」
- worktree lane は「どの directory / branch で動くか」

という別軸です。

もしこの辺りが混ざり始めたら、次を開いて整理し直してください。

- [`team-task-lane-model.md`](./team-task-lane-model.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)
- [`entity-map.md`](./entity-map.md)

## 初学者が混ぜやすいポイント

### 1. registry だけあって task record に `worktree` がない

task board から lane の情報が見えなくなります。

### 2. task ID はあるのに command が repo root で走っている

`cwd` が切り替わっていなければ isolation は成立していません。

### 3. `remove` だけを覚えて closeout の意味を教えない

読者は「directory を消す小技」としか理解できなくなります。

### 4. remove 前に dirty state を気にしない

教材版でも最低限、

**消す前に未コミット変更を確認する**

という原則は持たせるべきです。

### 5. `worktree_state` や `closeout` を持たない

lane の終わり方が state として残らなくなります。

### 6. lane を増やすだけで掃除しない

長く使うと registry も directory もすぐ乱れます。

### 7. event log を持たない

create / remove failure や binding ミスの調査が極端にやりづらくなります。

## 教学上の境界

この章でまず教えるべき中心は、製品レベルの Git 運用細目ではありません。

中心は次の 3 行です。

- task が「何をやるか」を記録する
- worktree が「どこでやるか」を記録する
- enter / run / closeout が execution lane の lifecycle を構成する

merge 自動化、複雑な回収 policy、cross-machine execution などは、その幹が見えてからで十分です。

この章を読み終えた読者が次の 1 文を言えれば成功です。

> task system は仕事の目標を管理し、worktree system はその仕事を安全に進めるための独立レーンを管理する。
