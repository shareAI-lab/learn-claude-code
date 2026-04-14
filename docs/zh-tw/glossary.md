# Glossary (術語表)

> 這份術語表只收錄本倉庫主線裡最重要、最容易讓初學者卡住的詞。  
> 如果某個詞你看著眼熟但說不清它到底是什麼，先回這裡。

## 推薦聯讀

如果你不是單純查詞，而是已經開始分不清“這些詞分別活在哪一層”，建議按這個順序一起看：

- 先看 [`entity-map.md`](./entity-map.md)：搞清每個實體屬於哪一層。
- 再看 [`data-structures.md`](./data-structures.md)：搞清這些詞真正落成什麼狀態結構。
- 如果你卡在“任務”這個詞上，再看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你卡在 MCP 不只等於 tools，再看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)。

## Agent

在這套倉庫裡，`agent` 指的是：  
**一個能根據輸入做判斷，並且會呼叫工具去完成任務的模型。**

你可以簡單理解成：

- 模型負責思考
- harness 負責給模型工作環境

## Harness

`harness` 可以理解成“給 agent 準備好的工作臺”。

它包括：

- 工具
- 檔案系統
- 許可權
- 提示詞
- 記憶
- 任務系統

模型本身不是 harness。  
harness 也不是模型。

## Agent Loop

`agent loop` 是系統反覆執行的一條主迴圈：

1. 把當前上下文發給模型
2. 看模型是要直接回答，還是要調工具
3. 如果調工具，就執行工具
4. 把工具結果寫回上下文
5. 再繼續下一輪

沒有這條迴圈，就沒有 agent 系統。

## Message / Messages

`message` 是一條訊息。  
`messages` 是訊息列表。

它通常包含：

- 使用者訊息
- assistant 訊息
- tool_result 訊息

這份列表就是 agent 最主要的工作記憶。

## Tool

`tool` 是模型可以呼叫的一種動作。

例如：

- 讀檔案
- 寫檔案
- 改檔案
- 跑 shell 命令
- 搜尋文字

模型並不直接執行系統命令。  
模型只是說“我要調哪個工具、傳什麼引數”，真正執行的是你的程式碼。

## Tool Schema

`tool schema` 是工具的輸入說明。

它告訴模型：

- 這個工具叫什麼
- 這個工具做什麼
- 需要哪些引數
- 引數是什麼型別

可以把它想成“工具使用說明書”。

## Dispatch Map

`dispatch map` 是一張對映表：

```python
{
    "read_file": read_file_handler,
    "write_file": write_file_handler,
    "bash": bash_handler,
}
```

意思是：

- 模型說要呼叫 `read_file`
- 程式碼就去表裡找到 `read_file_handler`
- 然後執行它

## Stop Reason

`stop_reason` 是模型這一輪為什麼停下來的原因。

常見的有：

- `end_turn`：模型說完了
- `tool_use`：模型要呼叫工具
- `max_tokens`：模型輸出被截斷了

它決定主迴圈下一步怎麼走。

## Context

`context` 是模型當前能看到的資訊總和。

包括：

- `messages`
- system prompt
- 動態補充資訊
- tool_result

上下文不是永久記憶。  
上下文是“這一輪工作時當前擺在桌上的東西”。

## Compact / Compaction

`compact` 指壓縮上下文。

因為對話越長，模型能看到的歷史就越多，成本和混亂也會一起增加。

壓縮的目標不是“刪除有用資訊”，而是：

- 保留真正關鍵的內容
- 去掉重複和噪聲
- 給後面的輪次騰空間

## Subagent

`subagent` 是從當前 agent 派生出來的一個子任務執行者。

它最重要的價值是：

**把一個大任務放到獨立上下文裡處理，避免汙染父上下文。**

## Fork

`fork` 在本倉庫語境裡，指一種子 agent 啟動方式：

- 不是從空白上下文開始
- 而是先繼承父 agent 的已有上下文

這適合“子任務必須理解當前討論背景”的場景。

## Permission

`permission` 就是“這個工具呼叫能不能執行”。

一個好的許可權系統通常要回答三件事：

- 應不應該直接拒絕
- 能不能自動允許
- 剩下的是不是要問使用者

## Permission Mode

`permission mode` 是許可權系統的工作模式。

例如：

- `default`：預設詢問
- `plan`：只允許讀，不允許寫
- `auto`：簡單安全的操作自動過，危險操作再問

## Hook

`hook` 是一個插入點。

意思是：  
在不改主迴圈程式碼的前提下，在某個時機額外執行一段邏輯。

例如：

- 工具呼叫前先檢查一下
- 工具呼叫後追加一條審計資訊

## Memory

`memory` 是跨會話儲存的資訊。

但不是所有東西都該存 memory。

適合存 memory 的，通常是：

- 使用者長期偏好
- 多次出現的重要反饋
- 未來別的會話仍然有價值的資訊

## System Prompt

`system prompt` 是系統級說明。

它告訴模型：

- 你是誰
- 你能做什麼
- 你有哪些規則
- 你應該如何協作

它比普通使用者訊息更穩定。

## System Reminder

`system reminder` 是每一輪臨時追加的動態提醒。

例如：

- 當前目錄
- 當前日期
- 某個本輪才需要的額外上下文

它和穩定的 system prompt 不是一回事。

## Task

`task` 是持久化任務系統裡的一個任務節點。

一個 task 通常不只是一句待辦事項，還會帶：

- 狀態
- 描述
- 依賴關係
- owner

## Dependency Graph

`dependency graph` 指任務之間的依賴關係圖。

最簡單的理解：

- A 做完，B 才能開始
- C 和 D 可以並行
- E 要等 C 和 D 都完成

這類結構能幫助 agent 判斷：

- 現在能做什麼
- 什麼被卡住了
- 什麼能同時做

## Worktree

`worktree` 是 Git 提供的一個機制：

同一個倉庫，可以在多個不同目錄裡同時展開多個工作副本。

它的價值是：

- 並行做多個任務
- 不互相汙染檔案改動
- 便於多 agent 並行工作

## MCP

`MCP` 是 Model Context Protocol。

你可以先把它理解成一套統一介面，讓 agent 能接入外部工具。

它解決的核心問題是：

- 工具不必都寫死在主程式裡
- 可以透過統一協議接入外部能力

如果你已經知道“能接外部工具”，但開始分不清 server、connection、tool、resource、prompt 這些層，繼續看：

- [`data-structures.md`](./data-structures.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## Runtime Task

`runtime task` 指的是：

> 系統當前正在執行、等待完成、或者剛剛結束的一條執行單元。

例如：

- 一個後臺 `pytest`
- 一個正在工作的 teammate
- 一個正在執行的 monitor

它和 `task` 不一樣。

- `task` 更像工作目標
- `runtime task` 更像執行槽位

如果你總把這兩個詞混掉，不要只在正文裡來回翻，直接去看：

- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## Teammate

`teammate` 是長期存在的隊友 agent。

它和 `subagent` 的區別是：

- `subagent`：一次性委派，幹完就結束
- `teammate`：長期存在，可以反覆接任務

如果你發現自己開始把這兩個詞混用，說明你需要回看：

- `s04`
- `s15`
- `entity-map.md`

## Protocol

`protocol` 就是一套提前約好的協作規則。

它回答的是：

- 訊息應該長什麼樣
- 收到以後要怎麼處理
- 批准、拒絕、超時這些狀態怎麼記錄

在團隊章節裡，它最常見的形狀是：

```text
request
  ->
response
  ->
status update
```

## Envelope

`envelope` 本意是“信封”。

在程式裡，它表示：

> 把正文和一些元資訊一起包起來的一條結構化記錄。

例如一條協議訊息裡，正文之外還會附帶：

- `from`
- `to`
- `request_id`
- `timestamp`

這整包東西，就可以叫一個 `envelope`。

## State Machine

`state machine` 不是很玄的高階理論。

你可以先把它理解成：

> 一張“狀態可以怎麼變化”的規則表。

例如：

```text
pending -> approved
pending -> rejected
pending -> expired
```

這就是一個最小狀態機。

## Router

`router` 可以簡單理解成“分發器”。

它的任務是：

- 看請求屬於哪一類
- 把它送去正確的處理路徑

例如工具層裡：

- 本地工具走本地 handler
- `mcp__...` 工具走 MCP client

## Control Plane

`control plane` 可以理解成“負責協調和控制的一層”。

它通常不直接產出最終業務結果，  
而是負責決定：

- 誰來執行
- 在什麼環境裡執行
- 有沒有許可權
- 執行後要不要通知別的模組

這個詞第一次看到容易怕。  
但在本倉庫裡，你只需要把它先記成：

> 不直接幹活，負責協調怎麼幹活的一層。

## Capability

`capability` 就是“能力項”。

例如在 MCP 裡，能力不只可能是工具，還可能包括：

- tools
- resources
- prompts
- elicitation

所以 `capability` 比 `tool` 更寬。

## Resource

`resource` 可以理解成：

> 一個可讀取、可引用、但不一定是“執行動作”的外部內容入口。

例如：

- 一份文件
- 一個只讀配置
- 一塊可被模型讀取的資料內容

它和 `tool` 的區別是：

- `tool` 更像動作
- `resource` 更像可讀取內容

## Elicitation

`elicitation` 可以先理解成：

> 外部系統反過來向用戶要補充輸入。

也就是說，不再只是 agent 主動呼叫外部能力。  
外部能力也可能說：

“我還缺一點資訊，請你補一下。”

## 最容易混的幾對詞

如果你是初學者，下面這幾對詞最值得一起記。

| 詞對 | 最簡單的區分方法 |
|---|---|
| `message` vs `system prompt` | 一個更像對話內容，一個更像系統說明 |
| `todo` vs `task` | 一個更像臨時步驟，一個更像持久化工作節點 |
| `task` vs `runtime task` | 一個管目標，一個管執行 |
| `subagent` vs `teammate` | 一個一次性，一個長期存在 |
| `tool` vs `resource` | 一個更像動作，一個更像內容 |
| `permission` vs `hook` | 一個決定能不能做，一個決定要不要額外插入行為 |

---

如果讀文件時又遇到新詞卡住，優先回這裡，不要硬頂著往後讀。
