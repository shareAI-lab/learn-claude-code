# s13: Background Tasks (後臺任務)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ] > s14 > s15 > s16 > s17 > s18 > s19`

> *慢命令可以在旁邊等，主迴圈不必陪著發呆。*

## 這一章要解決什麼問題

前面幾章裡，工具呼叫基本都是：

```text
模型發起
  ->
立刻執行
  ->
立刻返回結果
```

這對短命令沒有問題。  
但一旦遇到這些慢操作，就會卡住：

- `npm install`
- `pytest`
- `docker build`
- 大型程式碼生成或檢查任務

如果主迴圈一直同步等待，會出現兩個壞處：

- 模型在等待期間什麼都做不了
- 使用者明明還想繼續別的工作，卻被整輪流程堵住

所以這一章要解決的是：

**把“慢執行”移到後臺，讓主迴圈繼續推進別的事情。**

## 建議聯讀

- 如果你還沒有徹底穩住“任務目標”和“執行槽位”是兩層物件，先看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你開始分不清哪些狀態該落在 `RuntimeTaskRecord`、哪些還應留在任務板，回看 [`data-structures.md`](./data-structures.md)。
- 如果你開始把後臺執行理解成“另一條主迴圈”，先看 [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)，重新校正“並行的是執行與等待，不是主迴圈本身”。

## 先把幾個詞講明白

### 什麼叫前臺

前臺指的是：

> 主迴圈這輪發起以後，必須立刻等待結果的執行路徑。

### 什麼叫後臺

後臺不是神秘系統。  
後臺只是說：

> 命令先在另一條執行線上跑，主迴圈先去做別的事。

### 什麼叫通知佇列

通知佇列就是一條「稍後再告訴主迴圈」的收件匣。

後臺任務完成以後，不是直接把全文硬塞回模型，  
而是先寫一條摘要通知，等下一輪再統一帶回去。

## 最小心智模型

這一章最關鍵的句子是：

**主迴圈仍然只有一條，並行的是等待，不是主迴圈本身。**

可以把結構畫成這樣：

```text
主迴圈
  |
  +-- background_run("pytest")
  |      -> 立刻返回 task_id
  |
  +-- 繼續別的工作
  |
  +-- 下一輪模型呼叫前
         -> drain_notifications()
         -> 把摘要注入 messages

後臺執行線
  |
  +-- 真正執行 pytest
  +-- 完成後寫入通知佇列
```

如果讀者能牢牢記住這張圖，後面擴充套件成更復雜的非同步系統也不會亂。

## 關鍵資料結構

### 1. RuntimeTaskRecord

```python
task = {
    "id": "a1b2c3d4",
    "command": "pytest",
    "status": "running",
    "started_at": 1710000000.0,
    "result_preview": "",
    "output_file": "",
}
```

這些欄位分別表示：

- `id`：唯一標識
- `command`：正在跑什麼命令
- `status`：執行中、完成、失敗、超時
- `started_at`：什麼時候開始
- `result_preview`：先給模型看的簡短摘要
- `output_file`：完整輸出寫到了哪裡

教學版再往前走一步時，建議把它直接落成兩份檔案：

```text
.runtime-tasks/
  a1b2c3d4.json   # RuntimeTaskRecord
  a1b2c3d4.log    # 完整輸出
```

這樣讀者會更容易理解：

- `json` 記錄的是執行狀態
- `log` 儲存的是完整產物
- 通知只負責把 `preview` 帶回主迴圈

### 2. Notification

```python
notification = {
    "type": "background_completed",
    "task_id": "a1b2c3d4",
    "status": "completed",
    "preview": "tests passed",
}
```

通知只負責做一件事：

> 告訴主迴圈“有結果回來了，你要不要看”。

它不是完整日誌本體。

## 最小實現

### 第一步：登記後臺任務

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self.notifications = []
        self.lock = threading.Lock()
```

這裡最少要有兩塊狀態：

- `tasks`：當前有哪些後臺任務
- `notifications`：哪些結果已經回來，等待主迴圈領取

### 第二步：啟動後臺執行線

“執行緒”這個詞第一次見可能會有點緊張。  
你可以先把它理解成：

> 同一個程式裡，另一條可以獨立往前跑的執行線。

```python
def run(self, command: str) -> str:
    task_id = new_id()
    self.tasks[task_id] = {
        "id": task_id,
        "command": command,
        "status": "running",
    }

    thread = threading.Thread(
        target=self._execute,
        args=(task_id, command),
        daemon=True,
    )
    thread.start()
    return task_id
```

這一步最重要的不是執行緒本身，而是：

**主迴圈拿到 `task_id` 後就可以先繼續往前走。**

### 第三步：完成後寫通知

```python
def _execute(self, task_id: str, command: str):
    try:
        result = subprocess.run(..., timeout=300)
        status = "completed"
        preview = (result.stdout + result.stderr)[:500]
    except subprocess.TimeoutExpired:
        status = "timeout"
        preview = "command timed out"

    with self.lock:
        self.tasks[task_id]["status"] = status
        self.notifications.append({
            "type": "background_completed",
            "task_id": task_id,
            "status": status,
            "preview": preview,
        })
```

這裡體現的思想很重要：

**後臺執行負責產出結果，通知佇列負責把結果送回主迴圈。**

### 第四步：下一輪前排空通知

```python
def before_model_call(messages: list):
    notifications = bg.drain_notifications()
    if not notifications:
        return

    text = "\n".join(
        f"[bg:{n['task_id']}] {n['status']} - {n['preview']}"
        for n in notifications
    )
    messages.append({"role": "user", "content": text})
```

這樣模型在下一輪就會知道：

- 哪個後臺任務完成了
- 是成功、失敗還是超時
- 如果要看全文，該再去讀檔案

## 為什麼完整輸出不要直接塞回 prompt

這是本章必須講透的點。

如果後臺任務輸出幾萬行日誌，你不能每次都把全文塞回上下文。  
更穩的做法是：

1. 完整輸出寫磁碟
2. 通知裡只放簡短摘要
3. 模型真的要看全文時，再呼叫 `read_file`

這背後的心智很重要：

**通知負責提醒，檔案負責存原文。**

## 如何接到主迴圈裡

從 `s13` 開始，主迴圈多出一個標準前置步驟：

```text
1. 先排空通知佇列
2. 再呼叫模型
3. 普通工具照常同步執行
4. 如果模型呼叫 background_run，就登記後臺任務並立刻返回 task_id
5. 下一輪再把後臺結果帶回模型
```

教學版最小工具建議先做兩個：

- `background_run`
- `background_check`

這樣已經足夠支撐最小非同步執行閉環。

## 這一章和任務系統的邊界

這是本章最容易和 `s12` 混掉的地方。

### `s12` 的 task 是什麼

`s12` 裡的 `task` 是：

> 工作目標

它關心的是：

- 要做什麼
- 誰依賴誰
- 現在總體進度如何

### `s13` 的 background task 是什麼

本章裡的後臺任務是：

> 正在執行的執行單元

它關心的是：

- 哪個命令正在跑
- 跑到什麼狀態
- 結果什麼時候回來

所以最穩的記法是：

- `task` 更像工作板
- `background task` 更像執行中的作業

兩者相關，但不是同一個東西。

## 初學者最容易犯的錯

### 1. 以為“後臺”就是更復雜的主迴圈

不是。  
主迴圈仍然儘量保持單主線。

### 2. 只開執行緒，不登記狀態

這樣任務一多，你根本不知道：

- 誰還在跑
- 誰已經完成
- 誰失敗了

### 3. 把長日誌全文塞進上下文

上下文很快就會被撐爆。

### 4. 把 `s12` 的工作目標和本章的執行任務混為一談

這會讓後面多 agent 和排程章節全部打結。

## 教學邊界

這一章只需要先把一個最小執行時模式講清楚：

- 慢工作在後臺跑
- 主迴圈繼續保持單主線
- 結果透過通知路徑在後面回到模型

只要這條模式穩了，執行緒池、更多 worker 型別、更復雜的事件系統都可以後補。

這章真正要讓讀者守住的是：

**並行的是等待與執行槽位，不是主迴圈本身。**

## 學完這一章，你應該真正掌握什麼

學完以後，你應該能獨立複述下面幾句話：

1. 主迴圈只有一條，並行的是等待，不是主迴圈本身。
2. 後臺任務至少需要“任務表 + 通知佇列”兩塊狀態。
3. `background_run` 應該立刻返回 `task_id`，而不是同步卡住。
4. 通知只放摘要，完整輸出放檔案。

如果這 4 句話都已經非常清楚，說明你已經掌握了後臺任務系統的核心。

## 下一章學什麼

這一章解決的是：

> 慢命令如何在後臺執行。

下一章 `s14` 要解決的是：

> 如果連“啟動後臺任務”這件事都不一定由當前使用者觸發，而是由時間觸發，該怎麼做。

也就是從“非同步執行”繼續走向“定時觸發”。
