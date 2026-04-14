# s00f: 本倉庫程式碼閱讀順序

> 這份文件不是讓你“多看程式碼”。  
> 它專門解決另一個問題：
>
> **當你已經知道章節順序是對的以後，本倉庫程式碼到底應該按什麼順序讀，才不會把心智重新讀亂。**

## 先說結論

不要這樣讀程式碼：

- 不要從檔案最長的那一章開始
- 不要隨機點一個你覺得“高階”的章節開始
- 不要先鑽 `web/` 再回頭猜主線
- 不要把 19 個 `agents/*.py` 當成一個原始碼池亂翻

最穩的讀法只有一句話：

**文件順著章節讀，程式碼也順著章節讀。**

而且每一章的程式碼，都先按同一個模板看：

1. 先看狀態結構
2. 再看工具定義或登錄檔
3. 再看“這一輪怎麼推進”的主函式
4. 最後才看 CLI 入口和試執行方式

## 為什麼需要這份文件

很多讀者不是看不懂某一章文字，而是會在真正開啟程式碼以後重新亂掉。

典型症狀是：

- 一上來先盯住 300 行以上的檔案底部
- 先看一堆 `run_*` 函式，卻不知道它們掛在哪條主線上
- 先看“最複雜”的平臺章節，然後覺得前面的章節好像都太簡單
- 把 `task`、`runtime task`、`teammate`、`worktree` 在程式碼裡重新混成一團

這份閱讀順序就是為了防止這種情況。

## 讀每個 agent 檔案時，都先按同一個模板

不管你開啟的是哪一章，本倉庫裡的 `agents/sXX_*.py` 都建議先按下面順序讀：

### 第一步：先看檔案頭註釋

先回答兩個問題：

- 這一章到底在教什麼
- 它故意沒有教什麼

如果連這一步都沒建立，後面你會把每個函式都看成同等重要。

### 第二步：先看狀態結構或管理器類

優先找這些東西：

- `LoopState`
- `PlanningState`
- `CompactState`
- `TaskManager`
- `BackgroundManager`
- `TeammateManager`
- `WorktreeManager`

原因很簡單：

**先知道系統到底記住了什麼，後面才看得懂它為什麼要這樣流動。**

### 第三步：再看工具列表或登錄檔

優先找這些入口：

- `TOOLS`
- `TOOL_HANDLERS`
- 各種 `run_*`
- `build_tool_pool()`

這一層回答的是：

- 模型到底能呼叫什麼
- 這些呼叫會落到哪條執行面上

### 第四步：最後才看主推進函式

重點函式通常長這樣：

- `run_one_turn(...)`
- `agent_loop(...)`
- 某個 `handle_*`

這一步要回答的是：

- 這一章新機制到底接在主迴圈哪一環
- 哪個分支是新增的
- 新狀態是在哪裡寫入、迴流、繼續的

### 第五步：最後再看 `if __name__ == "__main__"`

CLI 入口當然有用，但它不應該成為第一屏。

因為它通常只是在做：

- 讀使用者輸入
- 初始化狀態
- 呼叫 `agent_loop`

真正決定一章心智主幹的，不在這裡。

## 階段 1：`s01-s06` 應該怎樣讀程式碼

這一段不是在學“很多功能”，而是在學：

**一個單 agent 主骨架到底怎樣成立。**

| 章節 | 檔案 | 先看什麼 | 再看什麼 | 讀完要確認什麼 |
|---|---|---|---|---|
| `s01` | `agents/s01_agent_loop.py` | `LoopState` | `TOOLS` -> `execute_tool_calls()` -> `run_one_turn()` -> `agent_loop()` | 你已經能看懂 `messages -> model -> tool_result -> next turn` |
| `s02` | `agents/s02_tool_use.py` | `safe_path()` | `run_read()` / `run_write()` / `run_edit()` -> `TOOL_HANDLERS` -> `agent_loop()` | 你已經能看懂“主迴圈不變，工具靠分發面增長” |
| `s03` | `agents/s03_todo_write.py` | `PlanItem` / `PlanningState` / `TodoManager` | `todo` 相關 handler -> reminder 注入 -> `agent_loop()` | 你已經能看懂“會話計劃狀態”怎麼外顯化 |
| `s04` | `agents/s04_subagent.py` | `AgentTemplate` | `run_subagent()` -> 父 `agent_loop()` | 你已經能看懂“子智慧體首先是上下文隔離” |
| `s05` | `agents/s05_skill_loading.py` | `SkillManifest` / `SkillDocument` / `SkillRegistry` | `get_descriptions()` / `get_content()` -> `agent_loop()` | 你已經能看懂“先發現、再按需載入” |
| `s06` | `agents/s06_context_compact.py` | `CompactState` | `persist_large_output()` -> `micro_compact()` -> `compact_history()` -> `agent_loop()` | 你已經能看懂“壓縮不是刪歷史，而是轉移細節” |

### 這一段最值得反覆看的 3 個程式碼點

1. `state` 在哪裡第一次從“聊天內容”升級成“顯式系統狀態”
2. `tool_result` 是怎麼一直保持為統一回流介面的
3. 新機制是怎樣接進 `agent_loop()` 而不是把 `agent_loop()` 重寫爛的

### 這一段讀完後，最好的動作

不要立刻去看 `s07`。

先自己從空目錄手寫一遍下面這些最小件：

- 一個 loop
- 一個 dispatch map
- 一個會話計劃狀態
- 一個一次性子任務隔離
- 一個按需技能載入
- 一個最小壓縮層

## 階段 2：`s07-s11` 應該怎樣讀程式碼

這一段不是在學“又多了五種功能”。

它真正是在學：

**單 agent 的控制面是怎樣長出來的。**

| 章節 | 檔案 | 先看什麼 | 再看什麼 | 讀完要確認什麼 |
|---|---|---|---|---|
| `s07` | `agents/s07_permission_system.py` | `BashSecurityValidator` / `PermissionManager` | 許可權判定入口 -> `run_bash()` -> `agent_loop()` | 你已經能看懂“先 gate，再 execute” |
| `s08` | `agents/s08_hook_system.py` | `HookManager` | hook 註冊與觸發 -> `agent_loop()` | 你已經能看懂 hook 是固定時機的插口，不是散落 if |
| `s09` | `agents/s09_memory_system.py` | `MemoryManager` / `DreamConsolidator` | `run_save_memory()` -> `build_system_prompt()` -> `agent_loop()` | 你已經能看懂 memory 是長期資訊層，不是上下文垃圾桶 |
| `s10` | `agents/s10_system_prompt.py` | `SystemPromptBuilder` | `build_system_reminder()` -> `agent_loop()` | 你已經能看懂輸入是流水線，不是單塊 prompt |
| `s11` | `agents/s11_error_recovery.py` | `estimate_tokens()` / `auto_compact()` / `backoff_delay()` | 各恢復分支 -> `agent_loop()` | 你已經能看懂“恢復以後怎樣繼續下一輪” |

### 這一段讀程式碼時，最容易重新讀亂的地方

1. 把許可權和 hook 混成一類
2. 把 memory 和 prompt 裝配混成一類
3. 把 `s11` 看成很多異常判斷，而不是“續行控制”

如果你開始混，先回：

- `docs/zh/s00a-query-control-plane.md`
- `docs/zh/s10a-message-prompt-pipeline.md`
- `docs/zh/s00c-query-transition-model.md`

## 階段 3：`s12-s14` 應該怎樣讀程式碼

這一段開始，程式碼理解的關鍵不再是“工具多了什麼”，而是：

**系統第一次真正長出會話外工作狀態和執行時槽位。**

| 章節 | 檔案 | 先看什麼 | 再看什麼 | 讀完要確認什麼 |
|---|---|---|---|---|
| `s12` | `agents/s12_task_system.py` | `TaskManager` | 任務建立、依賴、解鎖 -> `agent_loop()` | 你已經能看懂 task 是持久工作圖，不是 todo |
| `s13` | `agents/s13_background_tasks.py` | `NotificationQueue` / `BackgroundManager` | 後臺執行登記 -> 通知排空 -> `agent_loop()` | 你已經能看懂 background task 是執行槽位 |
| `s14` | `agents/s14_cron_scheduler.py` | `CronLock` / `CronScheduler` | `cron_matches()` -> schedule 觸發 -> `agent_loop()` | 你已經能看懂排程器只負責“未來何時開始” |

### 這一段讀程式碼時一定要守住的邊界

- `task` 是工作目標
- `runtime task` 是正在跑的執行槽位
- `schedule` 是何時觸發工作

只要這三層在程式碼裡重新混掉，後面 `s15-s19` 會一起變難。

## 階段 4：`s15-s19` 應該怎樣讀程式碼

這一段不要當成“功能狂歡”去讀。

它真正建立的是：

**平臺邊界。**

| 章節 | 檔案 | 先看什麼 | 再看什麼 | 讀完要確認什麼 |
|---|---|---|---|---|
| `s15` | `agents/s15_agent_teams.py` | `MessageBus` / `TeammateManager` | 隊友名冊、郵箱、獨立迴圈 -> `agent_loop()` | 你已經能看懂 teammate 是長期 actor，不是一次性 subagent |
| `s16` | `agents/s16_team_protocols.py` | `RequestStore` / `TeammateManager` | `handle_shutdown_request()` / `handle_plan_review()` -> `agent_loop()` | 你已經能看懂 request-response + `request_id` |
| `s17` | `agents/s17_autonomous_agents.py` | `RequestStore` / `TeammateManager` | `is_claimable_task()` / `claim_task()` / `ensure_identity_context()` -> `agent_loop()` | 你已經能看懂自治主線：空閒檢查 -> 安全認領 -> 恢復工作 |
| `s18` | `agents/s18_worktree_task_isolation.py` | `TaskManager` / `WorktreeManager` / `EventBus` | `worktree_enter` 相關生命週期 -> `agent_loop()` | 你已經能看懂 task 管目標，worktree 管執行車道 |
| `s19` | `agents/s19_mcp_plugin.py` | `CapabilityPermissionGate` / `MCPClient` / `PluginLoader` / `MCPToolRouter` | `build_tool_pool()` / `handle_tool_call()` / `normalize_tool_result()` -> `agent_loop()` | 你已經能看懂外部能力如何接回同一控制面 |

### 這一段最容易誤讀的地方

1. 把 `s15` 的 teammate 當成 `s04` 的 subagent 放大版
2. 把 `s17` 自治看成“agent 自己亂跑”
3. 把 `s18` worktree 看成一個 git 小技巧
4. 把 `s19` MCP 縮成“只是遠端 tools”

## 程式碼閱讀時，哪些檔案不要先看

如果你的目標是建立主線心智，下面這些內容不要先看：

- `web/` 裡的視覺化實現細節
- `web/src/data/generated/*`
- `.next/` 或其他構建產物
- `agents/s_full.py`

原因不是它們沒價值。

而是：

- `web/` 解決的是展示與學習介面
- `generated` 是抽取結果，不是機制本身
- `s_full.py` 是整合參考，不適合第一次建立邊界

## 最推薦的“文件 + 程式碼 + 執行”迴圈

每一章最穩的學習動作不是隻看文件，也不是隻看程式碼。

推薦固定走這一套：

1. 先讀這一章正文
2. 再讀這一章的橋接資料
3. 再開啟對應 `agents/sXX_*.py`
4. 按“狀態 -> 工具 -> 主推進函式 -> CLI 入口”的順序看
5. 跑一次這章的 demo
6. 自己從空目錄重寫一個最小版本

只要你每章都這樣走一次，程式碼理解會非常穩。

## 初學者最容易犯的 6 個程式碼閱讀錯誤

### 1. 先看最長檔案

這通常只會先把自己看暈。

### 2. 先盯 `run_bash()` 這種工具細節

工具實現細節不是主幹。

### 3. 不先找狀態結構

這樣你永遠不知道系統到底記住了什麼。

### 4. 把 `agent_loop()` 當成唯一重點

主迴圈當然重要，但每章真正新增的邊界，往往在狀態容器和分支入口。

### 5. 讀完程式碼不跑 demo

不實際跑一次，很難建立“這一章到底新增了哪條迴路”的感覺。

### 6. 一口氣連看三四章程式碼，不停下來自己重寫

這樣最容易出現“我好像都看過，但其實自己不會寫”的錯覺。

## 一句話記住

**程式碼閱讀順序也必須服從教學順序：先看邊界，再看狀態，再看主線如何推進，而不是隨機翻原始碼。**
