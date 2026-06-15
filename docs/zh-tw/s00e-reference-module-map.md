# s00e: 參考倉庫模組對映圖

> 這是一份給維護者和認真學習者用的校準文件。  
> 它不是讓讀者逐行讀逆向原始碼。
>
> 它只回答一個很關鍵的問題：
>
> **如果把參考倉庫裡真正重要的模組簇，和當前教學倉庫的章節順序對照起來看，現在這套課程順序到底合不合理？**

## 先說結論

合理。

當前這套 `s01 -> s19` 的順序，整體上是對的，而且比“按原始碼目錄順序講”更接近真實系統的設計主幹。

原因很簡單：

- 參考倉庫裡目錄很多
- 但真正決定系統骨架的，是少數幾簇控制、狀態、任務、團隊、隔離執行和外部能力模組
- 這些高訊號模組，和當前教學倉庫的四階段主線基本是對齊的

所以正確動作不是把教程改成“跟著原始碼樹走”。

正確動作是：

- 保留現在這條按依賴關係展開的主線
- 把它和參考倉庫的對映關係講明白
- 繼續把低價值的產品外圍細節擋在主線外

## 這份對照是怎麼做的

這次對照主要看的是參考倉庫裡真正決定系統骨架的部分，例如：

- `Tool.ts`
- `state/AppStateStore.ts`
- `coordinator/coordinatorMode.ts`
- `memdir/*`
- `services/SessionMemory/*`
- `services/toolUseSummary/*`
- `constants/prompts.ts`
- `tasks/*`
- `tools/TodoWriteTool/*`
- `tools/AgentTool/*`
- `tools/ScheduleCronTool/*`
- `tools/EnterWorktreeTool/*`
- `tools/ExitWorktreeTool/*`
- `tools/MCPTool/*`
- `services/mcp/*`
- `plugins/*`
- `hooks/toolPermission/*`

這些已經足夠判斷“設計主脈絡”。

沒有必要為了教學，再把每個命令目錄、相容分支、UI 細節和產品接線全部拖進正文。

## 真正的對映關係

| 參考倉庫模組簇 | 典型例子 | 對應教學章節 | 為什麼這樣放是對的 |
|---|---|---|---|
| 查詢主迴圈 + 控制狀態 | `Tool.ts`、`AppStateStore.ts`、query / coordinator 狀態 | `s00`、`s00a`、`s00b`、`s01`、`s11` | 真實系統絕不只是 `messages[] + while True`。教學上先講最小迴圈，再補控制平面，是對的。 |
| 工具路由與執行面 | `Tool.ts`、原生 tools、tool context、執行輔助邏輯 | `s02`、`s02a`、`s02b` | 參考倉庫明確把 tools 做成統一執行面，不只是玩具版分發表。當前拆法是合理的。 |
| 會話規劃 | `TodoWriteTool` | `s03` | 這是“當前會話怎麼不亂撞”的小結構，應該早於持久任務圖。 |
| 一次性委派 | `AgentTool` 的最小子集 | `s04` | 參考倉庫的 agent 體系很大，但教學倉庫先教“新上下文 + 子任務 + 摘要返回”這個最小正確版本，是對的。 |
| 技能發現與按需載入 | `DiscoverSkillsTool`、`skills/*`、相關 prompt 片段 | `s05` | 技能不是花哨外掛，而是知識注入層，所以應早於 prompt 複雜化和上下文壓力。 |
| 上下文壓力與壓縮 | `services/toolUseSummary/*`、`services/contextCollapse/*`、compact 邏輯 | `s06` | 參考倉庫明確存在顯式壓縮機制，把這一層放在平臺化能力之前完全正確。 |
| 許可權閘門 | `types/permissions.ts`、`hooks/toolPermission/*`、審批處理器 | `s07` | 執行安全是明確閘門，不是“某個 hook 順手乾的事”，所以必須早於 hook。 |
| Hook 與側邊擴充套件 | `types/hooks.ts`、hook runner、生命週期接線 | `s08` | 參考倉庫把擴充套件點和許可權分開。教學順序保持“先 gate，再 extend”是對的。 |
| 持久記憶選擇 | `memdir/*`、`services/SessionMemory/*`、記憶提取與篩選 | `s09` | 參考倉庫把 memory 處理成“跨會話、選擇性裝配”的層，不是通用筆記本。 |
| Prompt 組裝 | `constants/prompts.ts`、prompt sections、memory prompt 注入 | `s10`、`s10a` | 參考倉庫明顯把輸入拆成多個 section。教學版把 prompt 講成流水線，而不是一段大字串，是正確的。 |
| 恢復與續行 | query transition、retry 分支、compact retry、token recovery | `s11`、`s00c` | 真實系統裡“為什麼繼續下一輪”是顯式存在的，所以恢復應當晚於 loop / tools / compact / permissions / memory / prompt。 |
| 持久工作圖 | 任務記錄、任務板、依賴解鎖 | `s12` | 當前教程把“持久任務目標”和“會話內待辦”分開，是對的。 |
| 活著的執行時任務 | `tasks/types.ts`、`LocalShellTask`、`LocalAgentTask`、`RemoteAgentTask`、`MonitorMcpTask` | `s13`、`s13a` | 參考倉庫裡 runtime task 是明確的聯合型別，這強烈證明 `TaskRecord` 和 `RuntimeTaskState` 必須分開教。 |
| 定時觸發 | `ScheduleCronTool/*`、`useScheduledTasks` | `s14` | 排程是建在 runtime work 之上的新啟動條件，放在 `s13` 後非常合理。 |
| 持久隊友 | `InProcessTeammateTask`、team tools、agent registry | `s15` | 參考倉庫清楚地從一次性 subagent 繼續長成長期 actor。把 teammate 放到後段是對的。 |
| 結構化團隊協作 | send-message 流、request tracking、coordinator mode | `s16` | 協議必須建立在“已有持久 actor”之上，所以不能提前。 |
| 自治認領與恢復 | coordinator mode、任務認領、非同步 worker 生命週期、resume 邏輯 | `s17` | 參考倉庫裡的 autonomy 不是魔法，而是建立在 actor、任務和協議之上的。 |
| Worktree 執行車道 | `EnterWorktreeTool`、`ExitWorktreeTool`、agent worktree 輔助邏輯 | `s18` | 參考倉庫把 worktree 當作執行邊界 + 收尾狀態來處理。當前放在 tasks / teams 後是正確的。 |
| 外部能力匯流排 | `MCPTool`、`services/mcp/*`、`plugins/*`、MCP resources / prompts / tools | `s19`、`s19a` | 參考倉庫把 MCP / plugin 放在平臺最外層邊界。把它放最後是合理的。 |

## 這份對照最能證明的 5 件事

### 1. `s03` 應該繼續放在 `s12` 前面

參考倉庫裡同時存在：

- 小範圍的會話計劃
- 大範圍的持久任務 / 執行時系統

它們不是一回事。

所以教學順序應當繼續保持：

`會話內計劃 -> 持久任務圖`

### 2. `s09` 應該繼續放在 `s10` 前面

參考倉庫裡的輸入裝配，明確把 memory 當成輸入來源之一。

也就是說：

- `memory` 先回答“內容從哪裡來”
- `prompt pipeline` 再回答“這些內容怎麼組裝進去”

所以先講 `s09`，再講 `s10`，順序不要反過來。

### 3. `s12` 必須早於 `s13`

`tasks/types.ts` 這類執行時任務聯合型別，是這次對照裡最強的證據之一。

它非常清楚地說明：

- 持久化的工作目標
- 當前活著的執行槽位

必須是兩層不同狀態。

如果先講 `s13`，讀者幾乎一定會把這兩層混掉。

### 4. `s15 -> s16 -> s17` 的順序是對的

參考倉庫裡明確能看到：

- 持久 actor
- 結構化協作
- 自治認領 / 恢復

自治必須建立在前兩者之上，所以當前順序合理。

### 5. `s18` 應該繼續早於 `s19`

參考倉庫把 worktree 當作本地執行邊界機制。

這應該先於：

- 外部能力提供者
- MCP server
- plugin 裝配面

被講清。

否則讀者會誤以為“外部能力系統比本地執行邊界更核心”。

## 這套教學倉庫仍然不該抄進主線的內容

參考倉庫裡有很多真實但不應該佔據主線的內容，例如：

- CLI 命令面的完整鋪開
- UI 渲染細節
- 遙測與分析分支
- 遠端 / 企業產品接線
- 平臺相容層
- 檔名、函式名、行號級 trivia

這些不是假的。

但它們不該成為 0 到 1 教學路徑的中心。

## 當前教學最容易漂掉的地方

### 1. 不要把 subagent 和 teammate 混成一個模糊概念

參考倉庫裡的 `AgentTool` 橫跨了：

- 一次性委派
- 後臺 worker
- 持久 worker / teammate
- worktree 隔離 worker

這恰恰說明教學倉庫應該繼續拆開講：

- `s04`
- `s15`
- `s17`
- `s18`

不要在早期就把這些東西混成一個“大 agent 能力”。

### 2. 不要把 worktree 教成“只是 git 小技巧”

參考倉庫裡有 closeout、resume、cleanup、dirty-check 等狀態。

所以 `s18` 必須繼續講清：

- lane 身份
- task 繫結
- keep / remove 收尾
- 恢復與清理

而不是隻講 `git worktree add`。

### 3. 不要把 MCP 縮成“遠端 tools”

參考倉庫裡明顯不只有工具，還有：

- resources
- prompts
- elicitation / connection state
- plugin 中介層

所以 `s19` 可以繼續用 tools-first 的教學路徑切入，但一定要補平臺邊界那一層地圖。

## 最終判斷

如果只拿“章節順序是否貼近參考倉庫的設計主幹”這個問題來打分，那麼當前這套順序是過關而且方向正確的。

真正還能繼續加分的地方，不再是再做一次大重排，而是：

- 把橋接文件補齊
- 把實體邊界講得更硬
- 把多語言內容統一到同一個心智層次
- 讓 web 頁面把這套學習地圖展示得更清楚

## 一句話記住

**最好的教學順序，不是原始碼檔案出現的順序，而是一個初學實現者真正能順著依賴關係把系統重建出來的順序。**
