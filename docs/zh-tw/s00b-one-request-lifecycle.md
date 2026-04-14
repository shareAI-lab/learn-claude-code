# s00b: One Request Lifecycle (一次請求的完整生命週期)

> 這是一份橋接文件。  
> 它不替代主線章節，而是把整套系統串成一條真正連續的執行鏈。
>
> 它要回答的問題是：
>
> **使用者的一句話，進入系統以後，到底是怎樣一路流動、分發、執行、再回到主迴圈裡的？**

## 為什麼必須補這一篇

很多讀者在按順序看教程時，會逐章理解：

- `s01` 講迴圈
- `s02` 講工具
- `s03` 講規劃
- `s07` 講許可權
- `s09` 講 memory
- `s12-s19` 講任務、多 agent、MCP

每章單看都能懂。

但一旦開始自己實現，就會很容易卡住：

- 這些模組到底誰先誰後？
- 一條請求進來時，先走 prompt，還是先走 memory？
- 工具執行前，許可權和 hook 在哪一層？
- task、runtime task、teammate、worktree、MCP 到底是在一次請求裡的哪個階段介入？

所以你需要一張“縱向流程圖”。

## 先給一條最重要的總圖

```text
使用者請求
  |
  v
Query State 初始化
  |
  v
組裝 system prompt / messages / reminders
  |
  v
呼叫模型
  |
  +-- 普通回答 -------------------------------> 結束本次請求
  |
  +-- tool_use
        |
        v
    Tool Router
        |
        +-- 許可權判斷
        +-- Hook 攔截/注入
        +-- 本地工具 / MCP / agent / task / team
        |
        v
    執行結果
        |
        +-- 可能寫入 task / runtime task / memory / worktree 狀態
        |
        v
    tool_result 寫回 messages
        |
        v
    Query State 更新
        |
        v
    下一輪繼續
```

你可以把整條鏈先理解成三層：

1. `Query Loop`
2. `Tool Control Plane`
3. `Platform State`

## 第 1 段：使用者請求進入查詢控制平面

當用戶說：

```text
修復 tests/test_auth.py 的失敗，並告訴我原因
```

系統最先做的，不是立刻跑工具，而是先為這次請求建立一份查詢狀態。

最小可以理解成：

```python
query_state = {
    "messages": [{"role": "user", "content": user_text}],
    "turn_count": 1,
    "transition": None,
    "tool_use_context": {...},
}
```

這裡的重點是：

**這次請求不是“單次 API 呼叫”，而是一段可能包含很多輪的查詢過程。**

如果你對這一層還不夠熟，先回看：

- [`s01-the-agent-loop.md`](./s01-the-agent-loop.md)
- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

## 第 2 段：組裝本輪真正送給模型的輸入

主迴圈不會直接把原始 `messages` 裸發出去。

在更完整的系統裡，它通常會先組裝：

- system prompt blocks
- 規範化後的 messages
- memory section
- 當前輪 reminder
- 工具清單

也就是說，真正發給模型的通常是：

```text
system prompt
+ normalized messages
+ tools
+ optional reminders / attachments
```

這裡涉及的章節是：

- `s09` memory
- `s10` system prompt
- `s10a` message & prompt pipeline

這一段的核心心智是：

**system prompt 不是全部輸入，它只是輸入管道中的一段。**

## 第 3 段：模型產出兩類東西

模型這一輪的輸出，最關鍵地分成兩種：

### 第一種：普通回覆

如果模型直接給出結論或說明，本次請求可能就結束了。

### 第二種：動作意圖

也就是工具呼叫。

例如：

```text
read_file("tests/test_auth.py")
bash("pytest tests/test_auth.py -q")
todo([...])
load_skill("code-review")
task_create(...)
mcp__postgres__query(...)
```

這時候系統真正收到的，不只是“文字”，而是：

> 模型想讓真實世界發生某些動作。

## 第 4 段：工具路由層接管動作意圖

一旦出現 `tool_use`，系統就進入工具控制平面。

這一層至少要回答：

1. 這是什麼工具？
2. 它應該路由到哪類能力來源？
3. 執行前要不要先過許可權？
4. hook 有沒有要攔截或補充？
5. 它執行時能訪問哪些共享狀態？

最小圖可以這樣看：

```text
tool_use
  |
  v
Tool Router
  |
  +-- native tool handler
  +-- MCP client
  +-- agent/team/task handler
```

如果你對這一層不夠清楚，回看：

- [`s02-tool-use.md`](./s02-tool-use.md)
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## 第 5 段：許可權系統決定“能不能執行”

不是所有動作意圖都應該直接變成真實執行。

例如：

- 寫檔案
- 跑 bash
- 改工作目錄
- 調外部服務

這時會先進入許可權判斷：

```text
deny rules
  -> mode
  -> allow rules
  -> ask user
```

許可權系統處理的是：

> 這次動作是否允許發生。

相關章節：

- [`s07-permission-system.md`](./s07-permission-system.md)

## 第 6 段：Hook 可以在邊上做擴充套件

透過許可權檢查以後，系統還可能在工具執行前後跑 hook。

你可以把 hook 理解成：

> 不改主迴圈主幹，也能插入自定義行為的擴充套件點。

例如：

- 執行前記錄日誌
- 執行後做額外檢查
- 根據結果注入額外提醒

相關章節：

- [`s08-hook-system.md`](./s08-hook-system.md)

## 第 7 段：真正執行動作，並影響不同層的狀態

這是很多人最容易低估的一段。

工具執行結果，不只是“一段文字輸出”。

它還可能修改系統別的狀態層。

### 例子 1：規劃狀態

如果工具是 `todo`，它會更新的是當前會話計劃。

相關章節：

- [`s03-todo-write.md`](./s03-todo-write.md)

### 例子 2：持久任務圖

如果工具是 `task_create` / `task_update`，它會修改磁碟上的任務板。

相關章節：

- [`s12-task-system.md`](./s12-task-system.md)

### 例子 3：執行時任務

如果工具啟動了後臺 bash、後臺 agent 或監控任務，它會建立 runtime task。

相關章節：

- [`s13-background-tasks.md`](./s13-background-tasks.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### 例子 4：多 agent / teammate

如果工具是 `delegate`、`spawn_agent` 一類，它會在平臺層生成新的執行單元。

相關章節：

- [`s15-agent-teams.md`](./s15-agent-teams.md)
- [`s16-team-protocols.md`](./s16-team-protocols.md)
- [`s17-autonomous-agents.md`](./s17-autonomous-agents.md)

### 例子 5：worktree

如果系統要為某個任務提供隔離工作目錄，這會影響檔案系統級執行環境。

相關章節：

- [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md)

### 例子 6：MCP

如果呼叫的是外部 MCP 能力，那麼執行主體可能根本不在本地 handler，而在外部能力端。

相關章節：

- [`s19-mcp-plugin.md`](./s19-mcp-plugin.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## 第 8 段：執行結果被包裝回訊息流

不管執行落在哪一層，最後都要回到同一個位置：

```text
tool_result -> messages
```

這是整個系統最核心的閉環。

因為無論工具背後多複雜，模型下一輪真正能繼續工作的依據，仍然是：

> 系統把執行結果重新寫回了它可見的訊息流。

這也是為什麼 `s01` 永遠是根。

## 第 9 段：主迴圈根據結果決定下一輪是否繼續

當 `tool_result` 寫回以後，查詢狀態也會一起更新：

- `messages` 變了
- `turn_count` 增加了
- `transition` 被記錄成某種續行原因

這時系統就進入下一輪。

如果中間發生下面這些情況，控制平面還會繼續介入：

- 上下文太長，需要壓縮
- 輸出被截斷，需要續寫
- 請求失敗，需要恢復

相關章節：

- [`s06-context-compact.md`](./s06-context-compact.md)
- [`s11-error-recovery.md`](./s11-error-recovery.md)

## 第 10 段：哪些資訊不會跟著一次請求一起結束

這也是非常容易混的地方。

一次請求結束後，並不是所有狀態都隨之消失。

### 會跟著當前請求結束的

- 當前輪 messages 中的臨時推進過程
- 會話內 todo 狀態
- 當前輪 reminder

### 可能跨請求繼續存在的

- memory
- 持久任務圖
- runtime task 輸出
- worktree
- MCP 連線狀態

所以你要逐漸學會區分：

```text
query-scope state
session-scope state
project-scope state
platform-scope state
```

## 用一個完整例子串一次

還是用這個請求：

```text
修復 tests/test_auth.py 的失敗，並告訴我原因
```

系統可能會這樣流動：

1. 使用者請求進入 `QueryState`
2. system prompt + memory + tools 被組裝好
3. 模型先呼叫 `todo`，寫出三步計劃
4. 模型呼叫 `read_file("tests/test_auth.py")`
5. 工具路由到本地檔案讀取 handler
6. 讀取結果包裝成 `tool_result` 寫回訊息流
7. 下一輪模型呼叫 `bash("pytest tests/test_auth.py -q")`
8. 許可權系統判斷這條命令是否可執行
9. 執行測試，輸出太長則先落盤並留預覽
10. 失敗日誌回到訊息流
11. 模型再讀實現檔案並修改程式碼
12. 修改後再跑測試
13. 如果對話變長，`s06` 觸發壓縮
14. 如果任務被拆給子 agent，`s15-s17` 介入
15. 最後模型輸出結論，本次請求結束

你會發現：

**整套系統再複雜，也始終沒有脫離“輸入 -> 動作意圖 -> 執行 -> 結果寫回 -> 下一輪”這條主骨架。**

## 讀這篇時最該記住的三件事

### 1. 所有模組都不是平鋪擺在那裡的

它們是在一次請求的不同階段依次介入的。

### 2. 真正的閉環只有一個

那就是：

```text
tool_result 回到 messages
```

### 3. 很多高階機制，本質上只是圍繞這條閉環加的保護層

例如：

- 許可權是執行前保護層
- hook 是擴充套件層
- compact 是上下文預算保護層
- recovery 是出錯後的恢復層
- task/team/worktree/MCP 是更大的平臺能力層

## 一句話記住

**一次請求的完整生命週期，本質上就是：系統圍繞同一條主迴圈，把不同模組按階段接進來，最終持續把真實執行結果送回模型繼續推理。**
