# Entity Map (系統實體邊界圖)

> 這份文件不是某一章的正文，而是一張“別再混詞”的地圖。  
> 到了倉庫後半程，真正讓讀者困惑的往往不是程式碼，而是：
>
> **同一個系統裡，為什麼會同時出現這麼多看起來很像、但其實不是一回事的實體。**

## 這張圖和另外幾份橋接文件怎麼分工

- 這份圖先回答：一個詞到底屬於哪一層。
- [`glossary.md`](./glossary.md) 先回答：這個詞到底是什麼意思。
- [`data-structures.md`](./data-structures.md) 再回答：這個詞落到程式碼裡時，狀態長什麼樣。
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 專門補“工作圖任務”和“執行時任務”的分層。
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) 專門補 MCP 平臺層不是隻有 tools。

## 先給一個總圖

```text
對話層
  - message
  - prompt block
  - reminder

動作層
  - tool call
  - tool result
  - hook event

工作層
  - work-graph task
  - runtime task
  - protocol request

執行層
  - subagent
  - teammate
  - worktree lane

平臺層
  - mcp server
  - mcp capability
  - memory record
```

## 最容易混淆的 8 對概念

### 1. Message vs Prompt Block

| 實體 | 它是什麼 | 它不是什麼 | 常見位置 |
|---|---|---|---|
| `Message` | 對話歷史中的一條訊息 | 不是長期系統規則 | `messages[]` |
| `Prompt Block` | system prompt 內的一段穩定說明 | 不是某一輪剛發生的事件 | prompt builder |

簡單記法：

- message 更像“對話內容”
- prompt block 更像“系統說明”

### 2. Todo / Plan vs Task

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `todo / plan` | 當前輪或當前階段的過程性安排 | 不是長期持久化工作圖 |
| `task` | 持久化的工作節點 | 不是某一輪的臨時思路 |

### 3. Work-Graph Task vs Runtime Task

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `work-graph task` | 任務板上的工作節點 | 不是系統裡活著的執行單元 |
| `runtime task` | 當前正在執行的後臺/agent/monitor 插槽 | 不是依賴圖節點 |

這對概念是整個倉庫後半程最關鍵的區分之一。

### 4. Subagent vs Teammate

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `subagent` | 一次性委派執行者 | 不是長期線上成員 |
| `teammate` | 持久存在、可重複接活的隊友 | 不是一次性摘要工具 |

### 5. Protocol Request vs Normal Message

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `normal message` | 自由文字溝通 | 不是可追蹤的審批流程 |
| `protocol request` | 帶 request_id 的結構化請求 | 不是隨便說一句話 |

### 6. Worktree vs Task

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `task` | 說明要做什麼 | 不是目錄 |
| `worktree` | 說明在哪做 | 不是工作目標 |

### 7. Memory vs CLAUDE.md

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `memory` | 跨會話仍有價值、但不易從當前程式碼直接推出來的資訊 | 不是專案規則檔案 |
| `CLAUDE.md` | 長期規則、約束和說明 | 不是使用者偏好或專案動態背景 |

### 8. MCP Server vs MCP Tool

| 實體 | 它是什麼 | 它不是什麼 |
|---|---|---|
| `MCP server` | 外部能力提供者 | 不是單個工具定義 |
| `MCP tool` | 某個 server 暴露出來的一項具體能力 | 不是完整平臺連線本身 |

## 一張“是什麼 / 存在哪裡”的速查表

| 實體 | 主要作用 | 典型存放位置 |
|---|---|---|
| `Message` | 當前對話歷史 | `messages[]` |
| `PromptParts` | system prompt 的組裝片段 | prompt builder |
| `PermissionRule` | 工具執行前的決策規則 | settings / session state |
| `HookEvent` | 某個時機觸發的擴充套件點 | hook config |
| `MemoryEntry` | 跨會話有價值資訊 | `.memory/` |
| `TaskRecord` | 持久化工作節點 | `.tasks/` |
| `RuntimeTaskState` | 正在執行的任務槽位 | runtime task manager |
| `TeamMember` | 持久隊友 | `.team/config.json` |
| `MessageEnvelope` | 隊友間結構化訊息 | `.team/inbox/*.jsonl` |
| `RequestRecord` | 審批/關機等協議狀態 | request tracker |
| `WorktreeRecord` | 隔離工作目錄記錄 | `.worktrees/index.json` |
| `MCPServerConfig` | 外部 server 配置 | plugin / settings |

## 後半程推薦怎麼記

如果你到了 `s15` 以後開始覺得名詞多，可以只記這條線：

```text
message / prompt
   管輸入

tool / permission / hook
   管動作

task / runtime task / protocol
   管工作推進

subagent / teammate / worktree
   管執行者和執行車道

mcp / memory / claude.md
   管平臺外延和長期上下文
```

## 初學者最容易心智打結的地方

### 1. 把“任務”這個詞用在所有層

這是最常見的混亂來源。

所以建議你在寫正文時，儘量直接寫全：

- 工作圖任務
- 執行時任務
- 後臺任務
- 協議請求

不要都叫“任務”。

### 2. 把隊友和子 agent 混成一類

如果生命週期不同，就不是同一類實體。

### 3. 把 worktree 當成 task 的別名

一個是“做什麼”，一個是“在哪做”。

### 4. 把 memory 當成通用筆記本

它不是。它只儲存很特定的一類長期資訊。

## 這份圖應該怎麼用

最好的用法不是讀一遍背下來，而是：

- 每次你發現兩個詞開始混
- 先來這張圖裡確認它們是不是一個層級
- 再回去讀對應章節

如果你確認“不在一個層級”，下一步最好立刻去找它們對應的資料結構，而不是繼續憑感覺讀正文。

## 教學邊界

這張圖只解決“實體邊界”這一個問題。

它不負責展開每個實體的全部欄位，也不負責把所有產品化分支一起講完。

你可以把它當成一張分層地圖：

- 先確認詞屬於哪一層
- 再去對應章節看機制
- 最後去 [`data-structures.md`](./data-structures.md) 看狀態形狀

## 一句話記住

**一個結構完整的系統最怕的不是功能多，而是實體邊界不清；邊界一清，很多複雜度會自動塌下來。**
