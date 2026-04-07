# s13: バックグラウンドタスク

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ] > s14 > s15 > s16 > s17 > s18 > s19`

> *遅い command は横で待たせればよく、main loop まで一緒に止まる必要はありません。*

## この章が解く問題

前の章までの tool call は、基本的に次の形でした。

```text
model が tool を要求する
  ->
すぐ実行する
  ->
すぐ結果を返す
```

短い command ならこれで問題ありません。

でも次のような処理はすぐに詰まります。

- `npm install`
- `pytest`
- `docker build`
- 重い code generation
- 長時間の lint / typecheck

もし main loop がその完了を同期的に待ち続けると、2 つの問題が起きます。

- model は待ち時間のあいだ次の判断へ進めない
- user は別の軽い作業を進めたいのに、agent 全体が足止めされる

この章で入れるのは、

**遅い実行を background へ逃がし、main loop は次の仕事へ進めるようにすること**

です。

## 併読すると楽になる資料

- `task goal` と `live execution slot` がまだ混ざるなら [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)
- `RuntimeTaskRecord` と task board の境界を見直したいなら [`data-structures.md`](./data-structures.md)
- background execution が「別の main loop」に見えてきたら [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)

## 先に言葉をそろえる

### foreground とは何か

ここで言う foreground は、

> この turn の中で今すぐ結果が必要なので、main loop がその場で待つ実行

です。

### background とは何か

background は謎の裏世界ではありません。

意味は単純で、

> command を別の execution line に任せ、main loop は先に別のことを進める

ことです。

### 通知キューとは何か

background task が終わっても、その完全な出力をいきなり model へ丸ごと押し込む必要はありません。

いったん queue に要約通知として積み、

> 次の model call の直前にまとめて main loop へ戻す

のが分かりやすい設計です。

## 最小心智モデル

この章で最も大切な 1 文は次です。

**並行になるのは実行と待機であって、main loop 自体が増えるわけではありません。**

図にするとこうです。

```text
Main loop
  |
  +-- background_run("pytest")
  |      -> すぐ task_id を返す
  |
  +-- そのまま別の仕事を続ける
  |
  +-- 次の model call の前
         -> drain_notifications()
         -> 結果要約を messages へ注入

Background lane
  |
  +-- 実際に subprocess を実行
  +-- 終了後に result preview を queue へ積む
```

この図を保ったまま理解すれば、後でもっと複雑な runtime へ進んでも心智が崩れにくくなります。

## この章の核になるデータ構造

### 1. RuntimeTaskRecord

この章で扱う background task は durable task board の task とは別物です。

教材コードでは、background 実行はおおむね次の record を持ちます。

```python
task = {
    "id": "a1b2c3d4",
    "command": "pytest",
    "status": "running",
    "started_at": 1710000000.0,
    "finished_at": None,
    "result_preview": "",
    "output_file": ".runtime-tasks/a1b2c3d4.log",
}
```

各 field の意味は次の通りです。

- `id`: runtime slot の識別子
- `command`: 今走っている command
- `status`: `running` / `completed` / `timeout` / `error`
- `started_at`: いつ始まったか
- `finished_at`: いつ終わったか
- `result_preview`: model に戻す短い要約
- `output_file`: 完全出力の保存先

教材版ではこれを disk 上にも分けて残します。

```text
.runtime-tasks/
  a1b2c3d4.json
  a1b2c3d4.log
```

これで読者は、

- `json` は状態 record
- `log` は完全出力
- model へ戻すのはまず preview

という 3 層を自然に見分けられます。

### 2. Notification

background result はまず notification queue に入ります。

```python
notification = {
    "task_id": "a1b2c3d4",
    "status": "completed",
    "command": "pytest",
    "preview": "42 tests passed",
    "output_file": ".runtime-tasks/a1b2c3d4.log",
}
```

notification の役割は 1 つだけです。

> main loop に「結果が戻ってきた」と知らせること

ここに完全出力の全量を埋め込む必要はありません。

## 最小実装を段階で追う

### 第 1 段階: background manager を持つ

最低限必要なのは次の 2 つの状態です。

- `tasks`: いま存在する runtime task
- `_notification_queue`: main loop にまだ回収されていない結果

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self._notification_queue = []
        self._lock = threading.Lock()
```

ここで lock を置いているのは、background thread と main loop が同じ queue / dict を触るからです。

### 第 2 段階: `run()` はすぐ返す

background 化の一番大きな変化はここです。

```python
def run(self, command: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    self.tasks[task_id] = {
        "id": task_id,
        "status": "running",
        "command": command,
        "started_at": time.time(),
    }

    thread = threading.Thread(
        target=self._execute,
        args=(task_id, command),
        daemon=True,
    )
    thread.start()
    return task_id
```

重要なのは thread 自体より、

**main loop が結果ではなく `task_id` を受け取り、先に進める**

ことです。

### 第 3 段階: subprocess が終わったら notification を積む

```python
def _execute(self, task_id: str, command: str):
    try:
        result = subprocess.run(..., timeout=300)
        status = "completed"
        preview = (result.stdout + result.stderr)[:500]
    except subprocess.TimeoutExpired:
        status = "timeout"
        preview = "command timed out"

    with self._lock:
        self.tasks[task_id]["status"] = status
        self._notification_queue.append({
            "task_id": task_id,
            "status": status,
            "preview": preview,
        })
```

ここでの設計意図ははっきりしています。

- execution lane は command を実際に走らせる
- notification queue は main loop へ戻すための要約を持つ

役割を分けることで、result transport が見やすくなります。

### 第 4 段階: 次の model call 前に queue を drain する

```python
def agent_loop(messages: list):
    while True:
        notifications = BG.drain_notifications()
        if notifications:
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['preview']}" for n in notifications
            )
            messages.append({
                "role": "user",
                "content": f"<background-results>\n{notif_text}\n</background-results>",
            })
            messages.append({
                "role": "assistant",
                "content": "Noted background results.",
            })
```

この構造が大切です。

結果は「いつでも割り込んで model へ押し込まれる」のではなく、

**次の model call の入口でまとめて注入される**

からです。

### 第 5 段階: preview と full output を分ける

教材コードでは `result_preview` と `output_file` を分けています。

これは初心者にも非常に大事な設計です。

なぜなら background result にはしばしば次の問題があるからです。

- 出力が長い
- model に全量を見せる必要がない
- user だけ詳細 log を見れば十分なことが多い

そこでまず model には短い preview を返し、必要なら後で `read_file` 等で full log を読む形にします。

### 第 6 段階: stalled task も見られるようにする

教材コードは `STALL_THRESHOLD_S` を持ち、長く走りすぎている task を拾えます。

```python
def detect_stalled(self) -> list[str]:
    now = time.time()
    stalled = []
    for task_id, info in self.tasks.items():
        if info["status"] != "running":
            continue
        elapsed = now - info.get("started_at", now)
        if elapsed > STALL_THRESHOLD_S:
            stalled.append(task_id)
    return stalled
```

ここで学ぶべき本質は sophisticated monitoring ではありません。

**background 化したら「開始したまま返ってこないもの」を見張る観点が必要になる**

ということです。

## これは task board の task とは違う

ここは混ざりやすいので強調します。

`s12` の `task` は durable goal node です。

一方この章の background task は、

> いま実行中の live runtime slot

です。

同じ `task` という言葉を使っても指している層が違います。

だから分からなくなったら、本文だけを往復せずに次へ戻るべきです。

- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## 前の章とどうつながるか

この章は `s12` の durable task graph を否定する章ではありません。

むしろ、

- `s12` が「何の仕事が存在するか」を管理し
- `s13` が「いまどの command が走っているか」を管理する

という役割分担を教える章です。

後の `s14`、`s17`、`s18` へ行く前に、

**goal と runtime slot を分けて見る癖**

をここで作っておくことが重要です。

## 初学者が混ぜやすいポイント

### 1. background execution を「もう 1 本の main loop」と考える

実際に増えているのは subprocess waiting lane であって、main conversational loop ではありません。

### 2. result を queue ではなく即座に messages へ乱暴に書き込む

これでは model input の入口が分散し、system の流れが追いにくくなります。

### 3. full output と preview を分けない

長い log で context がすぐあふれます。

### 4. runtime task と durable task を同一視する

「いま走っている command」と「長く残る work goal」は別物です。

### 5. queue 操作に lock を使わない

background thread と main loop の競合で状態が壊れやすくなります。

### 6. timeout / error を `completed` と同じように扱う

戻すべき情報は同じではありません。終了理由は explicit に残すべきです。

## 教学上の境界

この章でまず理解すべき中心は、製品用の完全な async runtime ではありません。

中心は次の 3 行です。

- 遅い仕事を foreground から切り離す
- 結果は notification として main loop に戻す
- runtime slot は durable task board とは別層で管理する

ここが腹落ちしてから、

- より複雑な scheduler
- 複数種類の background lane
- 分散 worker

へ進めば十分です。
