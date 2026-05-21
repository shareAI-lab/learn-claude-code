# s00: Architecture Overview (架構總覽)

> 這一章是全倉庫的地圖。  
> 如果你只想先知道“整個系統到底由哪些模組組成、為什麼是這個學習順序”，先讀這一章。

## 先說結論

這套倉庫的主線是合理的。

它最重要的優點，不是“章節數量多”，而是它把學習過程拆成了四個階段：

1. 先做出一個真的能工作的 agent。
2. 再補安全、擴充套件、記憶和恢復。
3. 再把臨時清單升級成持久化任務系統。
4. 最後再進入多 agent、隔離執行和外部工具平臺。

這個順序符合初學者的心智。

因為一個新手最需要的，不是先知道所有高階細節，而是先建立一條穩定的主線：

`使用者輸入 -> 模型思考 -> 調工具 -> 拿結果 -> 繼續思考 -> 完成`

只要這條主線還沒真正理解，後面的許可權、hook、memory、MCP 都會變成一堆零散名詞。

## 這套倉庫到底要還原什麼

本倉庫的目標不是逐行復制任何一個生產倉庫。

本倉庫真正要還原的是：

- 主要模組有哪些
- 模組之間怎麼協作
- 每個模組的核心職責是什麼
- 關鍵狀態存在哪裡
- 一條請求在系統裡是怎麼流動的

也就是說，我們追求的是：

**設計主脈絡高保真，而不是所有外圍實現細節 1:1。**

這很重要。

如果你是為了自己從 0 到 1 做一個類似系統，那麼你真正需要掌握的是：

- 核心迴圈
- 工具機制
- 規劃與任務
- 上下文管理
- 許可權與擴充套件點
- 持久化
- 多 agent 協作
- 工作隔離
- 外部工具接入

而不是打包、跨平臺相容、歷史相容分支或產品化膠水程式碼。

## 三條閱讀原則

### 1. 先學最小版本，再學結構更完整的版本

比如子 agent。

最小版本只需要：

- 父 agent 發一個子任務
- 子 agent 用自己的 `messages`
- 子 agent 返回一個摘要

這已經能解決 80% 的核心問題：上下文隔離。

等這個最小版本你真的能寫出來，再去補更完整的能力，比如：

- 繼承父上下文的 fork 模式
- 獨立許可權
- 背景執行
- worktree 隔離

### 2. 每個新名詞都必須先解釋

本倉庫會經常用到一些詞：

- `state machine`
- `dispatch map`
- `dependency graph`
- `frontmatter`
- `worktree`
- `MCP`

如果你對這些詞不熟，不要硬扛。  
應該立刻去看術語表：[`glossary.md`](./glossary.md)

如果你想先知道“這套倉庫到底教什麼、不教什麼”，建議配合看：

- [`teaching-scope.md`](./teaching-scope.md)

如果你想先把最關鍵的資料結構建立成整體地圖，可以配合看：

- [`data-structures.md`](./data-structures.md)

如果你已經知道章節順序沒問題，但一開啟本地 `agents/*.py` 就會重新亂掉，建議再配合看：

- [`s00f-code-reading-order.md`](./s00f-code-reading-order.md)

### 3. 不把複雜外圍細節偽裝成“核心機制”

好的教學，不是把一切都講進去。

好的教學，是把真正關鍵的東西講完整，把不關鍵但很複雜的東西先拿掉。

所以本倉庫會刻意省略一些不屬於主幹的內容，比如：

- 打包與釋出
- 企業策略接線
- 遙測
- 多客戶端表層整合
- 歷史相容層

## 建議配套閱讀的文件

除了主線章節，我建議把下面兩份文件當作全程輔助地圖：

| 文件 | 用途 |
|---|---|
| [`teaching-scope.md`](./teaching-scope.md) | 幫你分清哪些內容屬於教學主線，哪些只是維護者側補充 |
| [`data-structures.md`](./data-structures.md) | 幫你集中理解整個系統的關鍵狀態和資料結構 |
| [`s00f-code-reading-order.md`](./s00f-code-reading-order.md) | 幫你把“章節順序”和“原生代碼閱讀順序”對齊，避免重新亂翻原始碼 |

如果你已經讀到中後半程，想把“章節之間缺的那一層”補上，再加看下面這些橋接文件：

| 文件 | 它補的是什麼 |
|---|---|
| [`s00d-chapter-order-rationale.md`](./s00d-chapter-order-rationale.md) | 為什麼這套課要按現在這個順序講，哪些重排會把讀者心智講亂 |
| [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) | 參考倉庫裡真正重要的模組簇，和當前課程章節是怎樣一一對應的 |
| [`s00a-query-control-plane.md`](./s00a-query-control-plane.md) | 為什麼一個更完整的系統不能只靠 `messages[] + while True` |
| [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md) | 一條請求如何從使用者輸入一路流過 query、tools、permissions、tasks、teams、MCP 再回到主迴圈 |
| [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) | 為什麼工具層不只是 `tool_name -> handler` |
| [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) | 為什麼 system prompt 不是模型完整輸入的全部 |
| [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) | 為什麼任務板裡的 task 和正在執行的 task 不是一回事 |
| [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) | 為什麼 MCP 正文先講 tools-first，但平臺層還要再補一張地圖 |
| [`entity-map.md`](./entity-map.md) | 幫你把 message、task、runtime task、subagent、teammate、worktree、MCP server 這些實體徹底分開 |

## 四階段學習路徑

### 階段 1：核心單 agent (`s01-s06`)

目標：先做出一個能做事的 agent。

| 章節 | 學什麼 | 解決什麼問題 |
|---|---|---|
| `s01` | Agent Loop | 沒有迴圈，就沒有 agent |
| `s02` | Tool Use | 讓模型從“會說”變成“會做” |
| `s03` | Todo / Planning | 防止大任務亂撞 |
| `s04` | Subagent | 防止上下文被大任務汙染 |
| `s05` | Skills | 按需拿知識，不把所有知識塞進提示詞 |
| `s06` | Context Compact | 防止上下文無限膨脹 |

這一階段結束後，你已經有了一個真正可執行的 coding agent 雛形。

### 階段 2：生產加固 (`s07-s11`)

目標：讓 agent 不只是能跑，而是更安全、更穩、更可擴充套件。

| 章節 | 學什麼 | 解決什麼問題 |
|---|---|---|
| `s07` | Permission System | 危險操作先過許可權關 |
| `s08` | Hook System | 不改主迴圈也能擴充套件行為 |
| `s09` | Memory System | 讓真正有價值的資訊跨會話存在 |
| `s10` | System Prompt | 把系統說明、工具、約束組裝成穩定輸入 |
| `s11` | Error Recovery | 出錯後能恢復，而不是直接崩潰 |

### 階段 3：任務管理 (`s12-s14`)

目標：把“聊天中的清單”升級成“磁碟上的任務圖”。

| 章節 | 學什麼 | 解決什麼問題 |
|---|---|---|
| `s12` | Task System | 大任務要有持久結構 |
| `s13` | Background Tasks | 慢操作不應該卡住前臺思考 |
| `s14` | Cron Scheduler | 讓系統能在未來自動做事 |

### 階段 4：多 agent 與外部系統 (`s15-s19`)

目標：從單 agent 升級成真正的平臺。

| 章節 | 學什麼 | 解決什麼問題 |
|---|---|---|
| `s15` | Agent Teams | 讓多個 agent 協作 |
| `s16` | Team Protocols | 讓協作有統一規則 |
| `s17` | Autonomous Agents | 讓 agent 自己找活、認領任務 |
| `s18` | Worktree Isolation | 並行工作時互不踩目錄 |
| `s19` | MCP & Plugin | 接入外部工具與外部能力 |

## 章節速查表：每章到底新增了哪一層狀態

很多讀者讀到中途會開始覺得：

- 這一章到底是在加工具，還是在加狀態
- 這個機制是“輸入層”的，還是“執行層”的
- 學完這一章以後，我手裡到底多了一個什麼東西

所以這裡給一張全域性速查表。  
讀每章以前，先看這一行；讀完以後，再回來檢查自己是不是真的吃透了這一行。

| 章節 | 新增的核心結構 | 它接在系統哪一層 | 學完你應該會什麼 |
|---|---|---|---|
| `s01` | `messages` / `LoopState` | 主迴圈 | 手寫一個最小 agent 閉環 |
| `s02` | `ToolSpec` / `ToolDispatchMap` | 工具層 | 把模型意圖路由成真實動作 |
| `s03` | `TodoItem` / `PlanState` | 過程規劃層 | 讓 agent 按步驟推進，而不是亂撞 |
| `s04` | `SubagentContext` | 執行隔離層 | 把探索性工作丟進乾淨子上下文 |
| `s05` | `SkillRegistry` / `SkillContent` | 知識注入層 | 只在需要時載入額外知識 |
| `s06` | `CompactSummary` / `PersistedOutput` | 上下文管理層 | 控制上下文大小又不丟主線 |
| `s07` | `PermissionRule` / `PermissionDecision` | 安全控制層 | 讓危險動作先經過決策管道 |
| `s08` | `HookEvent` / `HookResult` | 擴充套件控制層 | 不改主迴圈也能插入擴充套件邏輯 |
| `s09` | `MemoryEntry` / `MemoryStore` | 持久上下文層 | 只把真正跨會話有價值的資訊留下 |
| `s10` | `PromptParts` / `SystemPromptBlock` | 輸入組裝層 | 把模型輸入拆成可管理的管道 |
| `s11` | `RecoveryState` / `TransitionReason` | 恢復控制層 | 出錯後知道為什麼繼續、怎麼繼續 |
| `s12` | `TaskRecord` / `TaskStatus` | 工作圖層 | 把臨時清單升級成持久化任務圖 |
| `s13` | `RuntimeTaskState` / `Notification` | 執行時執行層 | 讓慢任務後臺執行、稍後回送結果 |
| `s14` | `ScheduleRecord` / `CronTrigger` | 定時觸發層 | 讓時間本身成為工作觸發器 |
| `s15` | `TeamMember` / `MessageEnvelope` | 多 agent 基礎層 | 讓隊友長期存在、反覆接活 |
| `s16` | `ProtocolEnvelope` / `RequestRecord` | 協作協議層 | 讓團隊從自由聊天升級成結構化協作 |
| `s17` | `ClaimPolicy` / `AutonomyState` | 自治排程層 | 讓 agent 空閒時自己找活、恢復工作 |
| `s18` | `WorktreeRecord` / `TaskBinding` | 隔離執行層 | 給並行任務分配獨立工作目錄 |
| `s19` | `MCPServerConfig` / `CapabilityRoute` | 外部能力層 | 把外部能力併入系統主控制面 |

## 整個系統的大圖

先看最重要的一張圖：

```text
User
  |
  v
messages[]
  |
  v
+-------------------------+
|  Agent Loop (s01)       |
|                         |
|  1. 組裝輸入            |
|  2. 調模型              |
|  3. 看 stop_reason      |
|  4. 如果要調工具就執行   |
|  5. 把結果寫回 messages  |
|  6. 繼續下一輪           |
+-------------------------+
  |
  +------------------------------+
  |                              |
  v                              v
Tool Pipeline                Context / State
(s02, s07, s08)              (s03, s06, s09, s10, s11)
  |                              |
  v                              v
Tasks / Teams / Worktree / MCP (s12-s19)
```

你可以把它理解成三層：

### 第一層：主迴圈

這是系統心臟。

它只做一件事：  
**不停地推動“思考 -> 行動 -> 觀察 -> 再思考”的迴圈。**

### 第二層：橫切機制

這些機制不是替代主迴圈，而是“包在主迴圈周圍”：

- 許可權
- hooks
- memory
- prompt 組裝
- 錯誤恢復
- 上下文壓縮

它們的作用，是讓主迴圈更安全、更穩定、更聰明。

### 第三層：更大的工作平臺

這些機制把單 agent 升級成更完整的系統：

- 任務圖
- 後臺任務
- 多 agent 團隊
- worktree 隔離
- MCP 外部工具

## 你真正需要掌握的關鍵狀態

理解 agent，最重要的不是背很多功能名，而是知道**狀態放在哪裡**。

下面是這個倉庫裡最關鍵的幾類狀態：

### 1. 對話狀態：`messages`

這是 agent 當前上下文的主體。

它儲存：

- 使用者說了什麼
- 模型回覆了什麼
- 呼叫了哪些工具
- 工具返回了什麼

你可以把它想成 agent 的“工作記憶”。

### 2. 工具登錄檔：`tools` / `handlers`

這是一張“工具名 -> Python 函式”的對映表。

這類結構常被叫做 `dispatch map`。

意思很簡單：

- 模型說“我要呼叫 `read_file`”
- 程式碼就去表裡找 `read_file` 對應的函式
- 找到以後執行

### 3. 計劃與任務狀態：`todo` / `tasks`

這部分儲存：

- 當前有哪些事要做
- 哪些已經完成
- 哪些被別的任務阻塞
- 哪些可以並行

### 4. 許可權與策略狀態

這部分儲存：

- 當前許可權模式是什麼
- 允許規則有哪些
- 拒絕規則有哪些
- 最近是否連續被拒絕

### 5. 持久化狀態

這部分儲存那些“不該跟著一次對話一起消失”的東西：

- memory 檔案
- task 檔案
- transcript
- background task 輸出
- worktree 繫結資訊

## 如果你想做出結構完整的版本，至少要有哪些資料結構

如果你的目標是自己寫一個結構完整、接近真實主脈絡的類似系統，最低限度要把下面這些資料結構設計清楚：

```python
class AppState:
    messages: list
    tools: dict
    tool_schemas: list

    todo: object | None
    tasks: object | None

    permissions: object | None
    hooks: object | None
    memories: object | None
    prompt_builder: object | None

    compact_state: dict
    recovery_state: dict

    background: object | None
    cron: object | None

    teammates: object | None
    worktree_session: dict | None
    mcp_clients: dict
```

這不是要求你一開始就把這些全寫完。

這張表的作用只是告訴你：

**一個像樣的 agent 系統，不只是 `messages + tools`。**

它最終會長成一個帶很多子模組的狀態系統。

## 一條請求是怎麼流動的

```text
1. 使用者發來任務
2. 系統組裝 prompt 和上下文
3. 模型返回普通文字，或者返回 tool_use
4. 如果返回 tool_use：
   - 先過 permission
   - 再過 hook
   - 然後執行工具
   - 把 tool_result 寫回 messages
5. 主迴圈繼續
6. 如果任務太大：
   - 可能寫入 todo / tasks
   - 可能派生 subagent
   - 可能觸發 compact
   - 可能走 background / team / worktree / MCP
7. 直到模型結束這一輪
```

這條流是全倉庫最重要的主脈絡。

你在後面所有章節裡看到的機制，本質上都只是插在這條流的不同位置。

## 讀者最容易混淆的幾組概念

### `Todo` 和 `Task` 不是一回事

- `Todo`：輕量、臨時、偏會話內
- `Task`：持久化、帶狀態、帶依賴關係

### `Memory` 和 `Context` 不是一回事

- `Context`：這一輪工作臨時需要的資訊
- `Memory`：未來別的會話也可能仍然有價值的資訊

### `Subagent` 和 `Teammate` 不是一回事

- `Subagent`：通常是當前 agent 派生出來的一次性幫手
- `Teammate`：更偏向長期存在於團隊中的協作角色

### `Prompt` 和 `System Reminder` 不是一回事

- `System Prompt`：較穩定的系統級輸入
- `System Reminder`：每輪動態變化的補充上下文

## 這套倉庫刻意省略了什麼

為了讓初學者能順著學下去，本倉庫不會把下面這些內容塞進主線：

- 產品級啟動流程裡的全部外圍初始化
- 真實商業產品中的賬號、策略、遙測、灰度等邏輯
- 只服務於相容性和歷史負擔的複雜分支
- 某些非常複雜但教學收益很低的邊角機制

這不是因為這些東西“不存在”。

而是因為對一個從 0 到 1 造類似系統的讀者來說，主幹先於枝葉。

## 這一章之後怎麼讀

推薦順序：

1. 先讀 `s01` 和 `s02`
2. 然後讀 `s03` 到 `s06`
3. 進入 `s07` 到 `s10`
4. 接著補 `s11`
5. 最後再讀 `s12` 到 `s19`

如果你在某一章覺得名詞開始打結，回來看這一章和術語表就夠了。

---

**一句話記住全倉庫：**

先做出能工作的最小迴圈，再一層一層給它補上規劃、隔離、安全、記憶、任務、協作和外部能力。
