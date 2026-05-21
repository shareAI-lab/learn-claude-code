# s12: Task System (任務系統)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > [ s12 ] > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *Todo 只能提醒你“有事要做”，任務系統才能告訴你“先做什麼、誰在等誰、哪一步還卡著”。*

## 這一章要解決什麼問題

`s03` 的 todo 已經能幫 agent 把大目標拆成幾步。

但 todo 仍然有兩個明顯限制：

- 它更像當前會話裡的臨時清單
- 它不擅長表達“誰先誰後、誰依賴誰”

例如下面這組工作：

```text
1. 先寫解析器
2. 再寫語義檢查
3. 測試和文件可以並行
4. 最後整體驗收
```

這已經不是單純的列表，而是一張“依賴關係圖”。

如果沒有專門的任務系統，agent 很容易出現這些問題：

- 前置工作沒做完，就貿然開始後面的任務
- 某個任務完成以後，不知道解鎖了誰
- 多個 agent 協作時，沒有統一任務板可讀

所以這一章要做的升級是：

**把“會話裡的 todo”升級成“可持久化的任務圖”。**

## 建議聯讀

- 如果你剛從 `s03` 過來，先回 [`data-structures.md`](./data-structures.md)，重新確認 `TodoItem / PlanState` 和 `TaskRecord` 不是同一層狀態。
- 如果你開始把“物件邊界”讀混，先回 [`entity-map.md`](./entity-map.md)，把 message、task、runtime task、teammate 這幾層拆開。
- 如果你準備繼續讀 `s13`，建議把 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 先放在手邊，因為從這裡開始最容易把 durable task 和 runtime task 混成一個詞。

## 先把幾個詞講明白

### 什麼是任務

這裡的 `task` 指的是：

> 一個可以被跟蹤、被分配、被完成、被阻塞的小工作單元。

它不是整段使用者需求，而是使用者需求拆出來的一小塊工作。

### 什麼是依賴

依賴的意思是：

> 任務 B 必須等任務 A 完成，才能開始。

### 什麼是任務圖

任務圖就是：

> 任務節點 + 依賴連線

你可以把它理解成：

- 點：每個任務
- 線：誰依賴誰

### 什麼是 ready

`ready` 的意思很簡單：

> 這條任務現在已經滿足開工條件。

也就是：

- 自己還沒開始
- 前置依賴已經全部完成

## 最小心智模型

本章最重要的，不是複雜排程演算法，而是先回答 4 個問題：

1. 現在有哪些任務？
2. 每個任務是什麼狀態？
3. 哪些任務還被卡住？
4. 哪些任務已經可以開始？

只要這 4 個問題能穩定回答，一個最小任務系統就已經成立了。

## 關鍵資料結構

### 1. TaskRecord

```python
task = {
    "id": 1,
    "subject": "Write parser",
    "description": "",
    "status": "pending",
    "blockedBy": [],
    "blocks": [],
    "owner": "",
}
```

每個欄位都對應一個很實用的問題：

- `id`：怎麼唯一找到這條任務
- `subject`：這條任務一句話在做什麼
- `description`：還有哪些補充說明
- `status`：現在走到哪一步
- `blockedBy`：還在等誰
- `blocks`：它完成後會解鎖誰
- `owner`：現在由誰來做

### 2. TaskStatus

教學版先只保留最少 4 個狀態：

```text
pending -> in_progress -> completed
deleted
```

解釋如下：

- `pending`：還沒開始
- `in_progress`：已經有人在做
- `completed`：已經做完
- `deleted`：邏輯刪除，不再參與工作流

### 3. Ready Rule

這是本章最關鍵的一條判斷規則：

```python
def is_ready(task: dict) -> bool:
    return task["status"] == "pending" and not task["blockedBy"]
```

如果你把這條規則講明白，讀者就會第一次真正明白：

**任務系統的核心不是“儲存清單”，而是“判斷什麼時候能開工”。**

## 最小實現

### 第一步：讓任務寫入磁碟

不要只把任務放在 `messages` 裡。  
教學版最簡單的做法，就是“一任務一檔案”：

```text
.tasks/
  task_1.json
  task_2.json
  task_3.json
```

建立任務時，直接寫成一條 JSON 記錄：

```python
class TaskManager:
    def create(self, subject: str, description: str = "") -> dict:
        task = {
            "id": self._next_id(),
            "subject": subject,
            "description": description,
            "status": "pending",
            "blockedBy": [],
            "blocks": [],
            "owner": "",
        }
        self._save(task)
        return task
```

### 第二步：把依賴關係寫成雙向

如果任務 A 完成後會解鎖任務 B，最好同時維護兩邊：

- A 的 `blocks` 裡有 B
- B 的 `blockedBy` 裡有 A

```python
def add_dependency(self, task_id: int, blocks_id: int):
    task = self._load(task_id)
    blocked = self._load(blocks_id)

    if blocks_id not in task["blocks"]:
        task["blocks"].append(blocks_id)
    if task_id not in blocked["blockedBy"]:
        blocked["blockedBy"].append(task_id)

    self._save(task)
    self._save(blocked)
```

這樣做的好處是：

- 從前往後讀得懂
- 從後往前也讀得懂

### 第三步：完成任務時自動解鎖後續任務

```python
def complete(self, task_id: int):
    task = self._load(task_id)
    task["status"] = "completed"
    self._save(task)

    for other in self._all_tasks():
        if task_id in other["blockedBy"]:
            other["blockedBy"].remove(task_id)
            self._save(other)
```

這一步非常關鍵。

因為它說明：

**任務系統不是靜態記錄表，而是會隨著完成事件自動推進的工作圖。**

### 第四步：把任務工具接給模型

教學版最小工具集建議先只做這 4 個：

- `task_create`
- `task_update`
- `task_get`
- `task_list`

這樣模型就能：

- 新建任務
- 更新狀態
- 看單條任務
- 看整張任務板

## 如何接到主迴圈裡

從 `s12` 開始，主迴圈第一次擁有了“會話外狀態”。

典型流程是：

```text
使用者提出複雜目標
  ->
模型決定先拆任務
  ->
呼叫 task_create / task_update
  ->
任務落到 .tasks/
  ->
後續輪次繼續讀取並推進
```

這裡要牢牢記住一句話：

**todo 更像本輪計劃，task 更像長期工作板。**

## 這一章和 s03、s13 的邊界

這一層邊界必須講清楚，不然後面一定會混。

### 和 `s03` 的區別

| 機制 | 更適合什麼 |
|---|---|
| `todo` | 當前會話裡快速列步驟 |
| `task` | 持久化工作、依賴關係、多人協作 |

如果只是“先看檔案，再改程式碼，再跑測試”，todo 往往就夠。  
如果是“跨很多輪、多人協作、還要管依賴”，就要上 task。

### 和 `s13` 的區別

本章的 `task` 指的是：

> 一條工作目標

它回答的是：

- 要做什麼
- 現在做到哪一步
- 誰在等誰

它不是：

- 某個正在後臺跑的 `pytest`
- 某個正在執行的 worker
- 某條當前活著的執行執行緒

後面這些屬於下一章要講的：

> 執行中的執行任務

## 初學者最容易犯的錯

### 1. 只會建立任務，不會維護依賴

那最後得到的還是一張普通清單，不是任務圖。

### 2. 任務只放記憶體，不落盤

系統一重啟，整個工作結構就沒了。

### 3. 完成任務後不自動解鎖後續任務

這樣系統永遠不知道下一步誰可以開工。

### 4. 把工作目標和執行中的執行混成一層

這會導致後面 `s13` 的後臺任務系統很難講清。

## 教學邊界

這一章先要守住的，不是任務平臺以後還能長出多少管理功能，而是任務記錄本身的最小主幹：

- `TaskRecord`
- 依賴關係
- 持久化
- 就緒判斷

只要讀者已經能把 todo 和 task、工作目標和執行執行明確分開，並且能手寫一個會解鎖後續任務的最小任務圖，這章就已經講到位了。

## 學完這一章，你應該真正掌握什麼

學完以後，你應該能獨立說清這幾件事：

1. 任務系統比 todo 多出來的核心能力，是“依賴關係”和“持久化”。
2. `TaskRecord` 是本章最關鍵的資料結構。
3. `blockedBy` / `blocks` 讓系統能看懂前後關係。
4. `is_ready()` 讓系統能判斷“誰現在可以開始”。

如果這 4 件事都已經清楚，說明你已經能從 0 到 1 手寫一個最小任務系統。

## 下一章學什麼

這一章解決的是：

> 工作目標如何被長期組織。

下一章 `s13` 要解決的是：

> 某個慢命令正在後臺跑時，主迴圈怎麼繼續前進。

也就是從“工作圖”走向“執行時執行層”。
