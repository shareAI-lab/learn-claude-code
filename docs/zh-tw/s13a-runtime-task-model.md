# s13a: Runtime Task Model (執行時任務模型)

> 這篇橋接文件專門解決一個非常容易混淆的問題：
>
> **任務板裡的 task，和後臺/隊友/監控這些“正在執行的任務”，不是同一個東西。**

## 建議怎麼聯讀

這篇最好夾在下面幾份文件中間讀：

- 先看 [`s12-task-system.md`](./s12-task-system.md)，確認工作圖任務在講什麼。
- 再看 [`s13-background-tasks.md`](./s13-background-tasks.md)，確認後臺執行在講什麼。
- 如果詞開始混，再回 [`glossary.md`](./glossary.md)。
- 如果想把欄位和狀態徹底對上，再對照 [`data-structures.md`](./data-structures.md) 和 [`entity-map.md`](./entity-map.md)。

## 為什麼必須單獨講這一篇

主線裡：

- `s12` 講的是任務系統
- `s13` 講的是後臺任務

這兩章各自都沒錯。  
但如果不額外補一層橋接，很多讀者很快就會把兩種“任務”混在一起。

例如：

- 任務板裡的 “實現 auth 模組”
- 後臺執行裡的 “正在跑 pytest”
- 隊友執行裡的 “alice 正在做程式碼改動”

這些都可以叫“任務”，但它們不在同一層。

為了讓整個倉庫接近滿分，這一層必須講透。

## 先解釋兩個完全不同的“任務”

### 第一種：工作圖任務

這就是 `s12` 裡的任務板節點。

它回答的是：

- 要做什麼
- 誰依賴誰
- 誰認領了
- 當前進度如何

它更像：

> 工作計劃中的一個可跟蹤工作單元。

### 第二種：執行時任務

這類任務回答的是：

- 現在有什麼執行單元正在跑
- 它是什麼型別
- 是在執行、完成、失敗還是被殺掉
- 輸出檔案在哪

它更像：

> 系統當前活著的一條執行槽位。

## 最小心智模型

你可以先把兩者畫成兩張表：

```text
工作圖任務
  - durable
  - 面向目標與依賴
  - 生命週期更長

執行時任務
  - runtime
  - 面向執行與輸出
  - 生命週期更短
```

它們的關係不是“二選一”，而是：

```text
一個工作圖任務
  可以派生
一個或多個執行時任務
```

例如：

```text
工作圖任務：
  "實現 auth 模組"

執行時任務：
  1. 後臺跑測試
  2. 啟動一個 coder teammate
  3. 監控一個 MCP 服務返回結果
```

## 為什麼這層區別非常重要

如果不區分這兩層，後面很多章節都會開始纏在一起：

- `s13` 的後臺任務會和 `s12` 的任務板混淆
- `s15-s17` 的隊友任務會不知道該掛在哪
- `s18` 的 worktree 到底繫結哪一層任務，也會變模糊

所以你要先記住一句：

**工作圖任務管“目標”，執行時任務管“執行”。**

## 關鍵資料結構

### 1. WorkGraphTaskRecord

這就是 `s12` 裡的那條 durable task。

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

### 2. RuntimeTaskState

教學版可以先用這個最小形狀：

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

這裡的欄位重點在於：

- `type`：它是什麼執行單元
- `status`：它現在在執行態還是終態
- `output_file`：它的產出在哪
- `notified`：結果有沒有回通知系統

### 3. RuntimeTaskType

你不必在教學版裡一次性實現所有型別，  
但應該讓讀者知道“執行時任務”是一個型別族，而不只是 `background shell` 一種。

最小型別表可以先這樣講：

```text
local_bash
local_agent
remote_agent
in_process_teammate
monitor
workflow
```

## 最小實現

### 第一步：繼續保留 `s12` 的任務板

這一層不要動。

### 第二步：單獨加一個 RuntimeTaskManager

```python
class RuntimeTaskManager:
    def __init__(self):
        self.tasks = {}
```

### 第三步：後臺執行時建立 runtime task

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

### 第四步：必要時把 runtime task 關聯回工作圖任務

```python
runtime_tasks[task_id]["work_graph_task_id"] = 12
```

這一步不是必須一上來就做，但如果系統進入多 agent / worktree 階段，就會越來越重要。

## 一張真正清楚的圖

```text
Work Graph
  task #12: Implement auth module
        |
        +-- spawns runtime task A: local_bash (pytest)
        +-- spawns runtime task B: local_agent (coder worker)
        +-- spawns runtime task C: monitor (watch service status)

Runtime Task Layer
  A/B/C each have:
  - own runtime ID
  - own status
  - own output
  - own lifecycle
```

## 它和後面章節怎麼連

這層一旦講清楚，後面幾章會順很多：

- `s13` 後臺命令，本質上是 runtime task
- `s15-s17` 隊友/agent，也可以看成 runtime task 的一種
- `s18` worktree 主要繫結工作圖任務，但也會影響執行時執行環境
- `s19` 某些外部監控或非同步呼叫，也可能落成 runtime task

所以後面只要你看到“有東西在後臺活著並推進工作”，都可以先問自己兩句：

- 它是不是某個 durable work graph task 派生出來的執行槽位。
- 它的狀態是不是應該放在 runtime layer，而不是任務板節點裡。

## 初學者最容易犯的錯

### 1. 把後臺 shell 直接寫成任務板狀態

這樣 durable task 和 runtime state 就混在一起了。

### 2. 認為一個工作圖任務只能對應一個執行時任務

現實裡很常見的是一個工作目標派生多個執行單元。

### 3. 用同一套狀態名描述兩層物件

例如：

- 工作圖任務的 `pending / in_progress / completed`
- 執行時任務的 `running / completed / failed / killed`

這兩套狀態最好不要混。

### 4. 忽略 output file 和 notified 這類執行時欄位

工作圖任務不太關心這些，執行時任務非常關心。

## 教學邊界

這篇最重要的，不是把執行時欄位一次加滿，而是先把下面三層物件徹底拆開：

- durable task 是長期工作目標
- runtime task 是當前活著的執行槽位
- notification / output 只是執行時把結果帶回來的通道

執行時任務型別列舉、增量輸出 offset、槽位清理策略，都可以等你先把這三層邊界手寫清楚以後再擴充套件。

## 一句話記住

**工作圖任務管“長期目標和依賴”，執行時任務管“當前活著的執行單元和輸出”。**

**`s12` 的 task 是工作圖節點，`s13+` 的 runtime task 是系統裡真正跑起來的執行單元。**
