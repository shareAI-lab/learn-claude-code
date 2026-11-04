# s12: Cron Scheduler — 時刻に合わせて作業を開始する

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s10 → s11 → `s12` → [s13](../s13_agent_teams/) → ... → s17

---

## 課題

S11 が扱うのは、コマンド開始後の実行方法である。時間のかかる Bash コマンドはバックグラウンドで実行できるが、将来の作業をいつ開始するかは記録せず、現在時刻を継続的に確認するコンポーネントもない。

「毎朝 9 時にテストを実行する」「30 分ごとに CI の状態を確認する」といった依頼を現在の Agent Loop だけで扱う場合、ユーザーは時刻が来るたびに prompt を送り直す必要がある。Harness は実行時刻を保存し、時刻が来たら対応する prompt を待機キューへ入れ、Agent がアイドルの時に Agent Loop へ渡す必要がある。

---

## 解決方法

![Cron Scheduler Overview](images/cron-scheduler-overview.ja.svg)

Agent が次のジョブを登録したとする。

```text
cron:   0 9 * * *
prompt: run tests
```

ローカル時刻の 09:00 に scheduler thread がジョブを検出し、`[Scheduled] run tests` を `cron_queue` に入れる。queue processor は Agent がアイドルになるまで待ち、Agent Loop の 1 ターンを開始する。モデルはその後 Bash を呼び出してテストを実行できる。

S12 のコードは S04 の 5 つの基本ツールと Hooks を残し、`schedule_cron`、`list_crons`、`cancel_cron` を追加する。ここで渡すのは新しい作業を開始する prompt であり、実行中のコマンド結果ではないため、S11 の background command は含めない。

---

## 仕組み

### CronJob が保存する内容

```python
@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool
    pending_delivery: bool = False
    last_fired: str | None = None
```

`cron` は発火時刻を決め、`prompt` は Agent に渡す作業を表す。`pending_delivery` は期限に達したがモデルに受け取られていないジョブを示し、`last_fired` は同じ分での重複投入を防ぐ。

### 5 フィールドの cron 式

```text
分  時  日  月  曜日
 *   *   *   *   *      毎分
 0   9   *   *   *      毎日 09:00
*/5   *   *   *   *      5 分ごと
 0   9   *   *  1-5     平日 09:00
```

この章では `*`、`*/N`、`N`、`N-M`、`N,M,...` を扱う。`schedule_job()` は保存前に `validate_cron()` を呼び、フィールド数や値の範囲が正しくない式を拒否する。

### 期限に達したらキューへ入れる

scheduler thread は 1 秒ごとにローカル時刻を読む。式が一致し、現在の分にまだ発火していない場合、`_enqueue_due_job()` は `pending_delivery` と `last_fired` を保存してからメモリ上のキューへ追加する。

```python
def poll_due_jobs(moment: datetime):
    minute_marker = moment.strftime("%Y-%m-%d %H:%M")
    with cron_lock:
        for job in list(scheduled_jobs.values()):
            if job.pending_delivery or job.last_fired == minute_marker:
                continue
            if cron_matches(job.cron, moment):
                _enqueue_due_job(job, minute_marker)
```

永続化に失敗すると、`_enqueue_due_job()` は元の状態へ戻し、メモリにしか存在しない配信を queue processor に渡さない。

### Agent がアイドルになってから配信する

`queue_processor_loop()` は時刻を確認しない。キューだけを確認し、`agent_lock` によってユーザーのターンと定時ターンが同時に session を変更するのを防ぐ。

```python
def queue_processor_loop(stop_event=RUNTIME_STOP):
    while not stop_event.wait(0.2):
        if not has_cron_queue() or not agent_lock.acquire(blocking=False):
            continue
        try:
            if has_cron_queue():
                run_agent_turn_locked()
        finally:
            agent_lock.release()
```

Agent Loop は期限に達したジョブをキューから取り出し、それぞれを新しい user message として追加する。

```python
fired = consume_cron_queue()
for job in fired:
    messages.append({"role": "user", "content": f"[Scheduled] {job.prompt}"})
```

モデル呼び出しに失敗すると、これらの message を現在の session から削除し、ジョブをキューへ戻す。モデルが受け取った後、一回限りのジョブは削除し、定期ジョブは `pending_delivery` を解除して次の一致を待つ。

### 永続化の境界

| モード | 保存先 | プロセス再起動後 |
|---|---|---|
| `durable=True` | `.scheduled_tasks.json` | 再読み込み |
| `durable=False` | メモリ | 消失 |

`.scheduled_tasks.json` は一時ファイルと `os.replace()` で更新する。ファイルが壊れている場合、起動時にエラーを表示し、黙って無視しない。

配信保証は at-least-once である。モデルが prompt を受け取った後、確認状態をディスクへ書く前にプロセスが終了すると、再起動後に同じジョブを再配信する場合がある。

### 実行境界

- scheduler は Agent プロセスのローカル時刻を使う。
- Agent プロセスが終了すると scheduler thread も停止する。`durable` が保持するのはジョブ定義だけである。
- 再起動時にジョブを復元するが、停止中に過ぎた実行時刻は補わない。
- 定時ターンは queue processor thread で動く。対話的な許可が必要な tool call は拒否し、main terminal から同時に入力を読まない。
- scheduler と queue processor の thread は CLI 実行時だけ開始する。`code.py` の import では background thread を起動しない。

Agent が閉じている間も実行する必要がある場合は、crontab、systemd timer、外部 scheduler を使う。

---

## 試してみる

```sh
cd learn-claude-code
python s12_cron_scheduler/code.py
```

次の prompt を順に入力できる。

1. `Schedule "run date" every 2 minutes and keep it after restart.`
2. `List all cron jobs.`
3. `Cancel the cron job you just created.`

`.scheduled_tasks.json` の内容と、期限に達した後の `[Scheduled] run date` message を確認する。分単位のジョブを試す間は Agent プロセスを起動したままにする。

---

## 次の章

スケジューラは指定した時刻に Agent Loop の 1 ターンを開始できるが、そのターンを処理するのは一つの Agent である。複数のモジュールを同時に調査、変更し、結果をまとめるタスクでは、Harness が複数の Agent へ作業を割り当て、それぞれの実行結果を集める必要がある。

s13 Agent Teams → Lead がタスクを割り当て、teammate が個別に実行し、inbox を通じて結果を返す。

<!-- translation-sync: zh@v9, en@v9, ja@v9 -->
