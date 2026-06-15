# s14: Cron Scheduler (定時排程)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] > s15 > s16 > s17 > s18 > s19`

> *如果後臺任務解決的是“稍後回來拿結果”，那麼定時排程解決的是“將來某個時間再開始做事”。*

## 這一章要解決什麼問題

`s13` 已經讓系統學會了把慢命令放到後臺。

但後臺任務預設還是“現在就啟動”。

很多真實需求並不是現在做，而是：

- 每天晚上跑一次測試
- 每週一早上生成報告
- 30 分鐘後提醒我繼續檢查某個結果

如果沒有排程能力，使用者就只能每次手動再說一遍。  
這會讓系統看起來像“只能響應當下”，而不是“能安排未來工作”。

所以這一章要加上的能力是：

**把一條未來要執行的意圖，先記下來，等時間到了再觸發。**

## 建議聯讀

- 如果你還沒完全分清 `schedule`、`task`、`runtime task` 各自表示什麼，先回 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你想重新看清“一條觸發最終是怎樣回到主迴圈裡的”，可以配合讀 [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md)。
- 如果你開始把“未來觸發”誤以為“又多了一套執行系統”，先回 [`data-structures.md`](./data-structures.md)，確認排程記錄和執行時記錄不是同一個表。

## 先解釋幾個名詞

### 什麼是排程器

排程器，就是一段專門負責“看時間、查任務、決定是否觸發”的程式碼。

### 什麼是 cron 表示式

`cron` 是一種很常見的定時寫法。

最小 5 欄位版本長這樣：

```text
分 時 日 月 周
```

例如：

```text
*/5 * * * *   每 5 分鐘
0 9 * * 1     每週一 9 點
30 14 * * *   每天 14:30
```

如果你是初學者，不用先背全。

這一章真正重要的不是語法細節，而是：

> “系統如何把一條未來任務記住，並在合適時刻放回主迴圈。”

### 什麼是持久化排程

持久化，意思是：

> 就算程式重啟，這條排程記錄還在。

## 最小心智模型

先把排程看成 3 個部分：

```text
1. 排程記錄
2. 定時檢查器
3. 通知佇列
```

它們之間的關係是：

```text
schedule_create(...)
  ->
把記錄寫到列表或檔案裡
  ->
後臺檢查器每分鐘看一次“現在是否匹配”
  ->
如果匹配，就把 prompt 放進通知佇列
  ->
主迴圈下一輪把它當成新的使用者訊息餵給模型
```

這條鏈路很重要。

因為它說明了一點：

**定時排程並不是另一套 agent。它最終還是回到同一條主迴圈。**

## 關鍵資料結構

### 1. ScheduleRecord

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

欄位含義：

- `id`：唯一編號
- `cron`：定時規則
- `prompt`：到點後要注入主迴圈的提示
- `recurring`：是不是反覆觸發
- `durable`：是否落盤儲存
- `created_at`：建立時間
- `last_fired_at`：上次觸發時間

### 2. 排程通知

```python
{
    "type": "scheduled_prompt",
    "schedule_id": "job_001",
    "prompt": "Run the weekly status report.",
}
```

### 3. 檢查週期

教學版建議先按“分鐘級”思考，而不是“秒級嚴格精度”。

因為大多數 cron 任務本來就不是為了卡秒執行。

## 最小實現

### 第一步：允許建立一條排程記錄

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

### 第二步：寫一個定時檢查迴圈

```python
def check_loop(self):
    while True:
        now = datetime.now()
        self.check_jobs(now)
        time.sleep(60)
```

最小教學版先每分鐘檢查一次就足夠。

### 第三步：時間到了就發通知

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

### 第四步：主迴圈像處理後臺通知一樣處理定時通知

```python
notifications = scheduler.drain()
for item in notifications:
    messages.append({
        "role": "user",
        "content": f"[scheduled:{item['schedule_id']}] {item['prompt']}",
    })
```

這樣一來，定時任務最終還是由模型接手繼續做。

## 為什麼這章放在後臺任務之後

因為這兩章解決的問題很接近，但不是同一件事。

可以這樣區分：

| 機制 | 回答的問題 |
|---|---|
| 後臺任務 | “已經啟動的慢操作，結果什麼時候回來？” |
| 定時排程 | “一件事應該在未來什麼時候開始？” |

這個順序對初學者很友好。

因為先理解“非同步結果回來”，再理解“未來觸發一條新意圖”，心智會更順。

## 初學者最容易犯的錯

### 1. 一上來沉迷 cron 語法細節

這章最容易跑偏到一大堆表示式規則。

但教學主線其實不是“背語法”，而是：

**排程記錄如何進入通知佇列，又如何回到主迴圈。**

### 2. 沒有 `last_fired_at`

沒有這個欄位，系統很容易在短時間內重複觸發同一條任務。

### 3. 只放記憶體，不支援落盤

如果使用者希望“明天再提醒我”，程式一重啟就沒了，這就不是真正的排程。

### 4. 把排程觸發結果直接在後臺默默執行

教學主線裡更清楚的做法是：

- 時間到了
- 先發通知
- 再讓主迴圈決定怎麼處理

這樣系統行為更透明，讀者也更容易理解。

### 5. 誤以為定時任務必須絕對準點

很多初學者會把排程想成秒錶。

但這裡更重要的是“有計劃地觸發”，而不是追求毫秒級精度。

## 如何接到整個系統裡

到了這一章，系統已經有兩條重要的“外部事件輸入”：

- 後臺任務完成通知
- 定時排程觸發通知

二者最好的統一方式是：

**都走通知佇列，再在下一次模型呼叫前統一注入。**

這樣主迴圈結構不會越來越亂。

## 教學邊界

這一章先講清一條主線就夠了：

**排程器做的是“記住未來”，不是“取代主迴圈”。**

所以教學版先只需要讓讀者看清：

- schedule record 負責記住未來何時開工
- 真正執行工作時，仍然回到任務系統和通知佇列
- 它只是多了一種“開始入口”，不是多了一條新的主迴圈

多程序鎖、漏觸發補報、自然語言時間語法這些，都應該排在這條主線之後。

## 試一試

```sh
cd learn-claude-code
python agents/s14_cron_scheduler.py
```

可以試試這些任務：

1. 建一個每分鐘觸發一次的小任務，觀察它是否會按時進入通知佇列。
2. 建一個只觸發一次的任務，確認觸發後是否會消失。
3. 重啟程式，檢查持久化的排程記錄是否還在。

讀完這一章，你應該能自己說清這句話：

**後臺任務是在“等結果”，定時排程是在“等開始”。**
