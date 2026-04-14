# s14: Cron Scheduler

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] > s15 > s16 > s17 > s18 > s19`

> *バックグラウンドタスクが「遅い仕事をどう続けるか」を扱うなら、スケジューラは「未来のいつ仕事を始めるか」を扱う。*

## この章が解決する問題

`s13` で、遅い処理をバックグラウンドへ逃がせるようになりました。

でもそれは「今すぐ始める仕事」です。

現実には:

- 毎晩実行したい
- 毎週決まった時刻にレポートを作りたい
- 30 分後に再確認したい

といった未来トリガーが必要になります。

この章の核心は:

**未来の意図を今記録して、時刻が来たら新しい仕事として戻す**

ことです。

## 教学上の境界

この章の中心は cron 構文の暗記ではありません。

本当に理解すべきなのは:

**schedule record が通知になり、通知が主ループへ戻る流れ**

です。

## 主線とどう併読するか

- `schedule`、`task`、`runtime task` がまだ同じ object に見えるなら、[`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) に戻ります。
- 1 つの trigger が最終的にどう主線へ戻るかを見たいなら、[`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md) と一緒に読みます。
- 未来トリガーが別の実行系に見えてきたら、[`data-structures.md`](./data-structures.md) で schedule record と runtime record を分け直します。

## 最小の心智モデル

```text
1. schedule records
2. time checker
3. notification queue
```

流れ:

```text
schedule_create(...)
  ->
記録を保存
  ->
time checker が定期的に一致判定
  ->
一致したら scheduled notification を積む
  ->
主ループがそれを新しい仕事として受け取る
```

重要なのは:

**scheduler 自体は第二の agent ではない**

ということです。

## 重要なデータ構造

### 1. schedule record

```python
schedule = {
    "id": "job_001",
    "cron": "0 9 * * 1",
    "prompt": "Run the weekly status report.",
    "recurring": True,
    "durable": True,
    "created_at": 1710000000.0,
    "last_fired_at": None,
}
```

### 2. scheduled notification

```python
{
    "type": "scheduled_prompt",
    "schedule_id": "job_001",
    "prompt": "Run the weekly status report.",
}
```

### 3. check interval

教学版なら分単位で十分です。

## 最小実装

```python
def create(self, cron_expr: str, prompt: str, recurring: bool = True):
    job = {
        "id": new_id(),
        "cron": cron_expr,
        "prompt": prompt,
        "recurring": recurring,
        "created_at": time.time(),
        "last_fired_at": None,
    }
    self.jobs.append(job)
    return job
```

```python
def check_loop(self):
    while True:
        now = datetime.now()
        self.check_jobs(now)
        time.sleep(60)
```

```python
def check_jobs(self, now):
    for job in self.jobs:
        if cron_matches(job["cron"], now):
            self.queue.put({
                "type": "scheduled_prompt",
                "schedule_id": job["id"],
                "prompt": job["prompt"],
            })
            job["last_fired_at"] = now.timestamp()
```

最後に主ループへ戻します。

```python
notifications = scheduler.drain()
for item in notifications:
    messages.append({
        "role": "user",
        "content": f"[scheduled:{item['schedule_id']}] {item['prompt']}",
    })
```

## なぜ `s13` の後なのか

この 2 章は近い問いを扱います。

| 仕組み | 中心の問い |
|---|---|
| background tasks | 遅い仕事を止めずにどう続けるか |
| scheduling | 未来の仕事をいつ始めるか |

この順序の方が、初学者には自然です。

## 初学者がやりがちな間違い

### 1. cron 構文だけに意識を取られる

### 2. `last_fired_at` を持たない

### 3. スケジュールをメモリにしか置かない

### 4. 未来トリガーの仕事を裏で黙って全部実行する

より分かりやすい主線は:

- trigger
- notify
- main loop が処理を決める

です。

## Try It

```sh
cd learn-claude-code
python agents/s14_cron_scheduler.py
```
