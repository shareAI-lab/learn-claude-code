# Core Data Structures (核心資料結構總表)

> 學習 agent，最容易迷路的地方不是功能太多，而是不知道“狀態到底放在哪”。這份文件把主線章節和橋接章節裡反覆出現的關鍵資料結構集中列出來，方便你把整套系統看成一張圖。

## 推薦聯讀

建議把這份總表當成“狀態地圖”來用：

- 先不懂詞，就回 [`glossary.md`](./glossary.md)。
- 先不懂邊界，就回 [`entity-map.md`](./entity-map.md)。
- 如果卡在 `TaskRecord` 和 `RuntimeTaskState`，繼續看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果卡在 MCP 為什麼還有 resource / prompt / elicitation，繼續看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)。

## 先記住兩個總原則

### 原則 1：區分“內容狀態”和“流程狀態”

- `messages`、`tool_result`、memory 正文，屬於內容狀態。
- `turn_count`、`transition`、`pending_classifier_check`，屬於流程狀態。

很多初學者會把這兩類狀態混在一起。  
一混，後面就很難看懂為什麼一個結構完整的系統會需要控制平面。

### 原則 2：區分“持久狀態”和“執行時狀態”

- task、memory、schedule 這類狀態，通常會寫入磁碟，跨會話存在。
- runtime task、當前 permission decision、當前 MCP connection 這類狀態，通常只在系統執行時活著。

## 1. 查詢與對話控制狀態

### Message

作用：儲存當前對話和工具往返歷史。

最小形狀：

```python
message = {
    "role": "user" | "assistant",
    "content": "...",
}
```

支援工具呼叫後，`content` 常常不再只是字串，而會變成塊列表，其中可能包含：

- text block
- `tool_use`
- `tool_result`

相關章節：

- `s01`
- `s02`
- `s06`
- `s10`

### NormalizedMessage

作用：把不同來源的訊息整理成統一、穩定、可送給模型 API 的訊息格式。

最小形狀：

```python
message = {
    "role": "user" | "assistant",
    "content": [
        {"type": "text", "text": "..."},
    ],
}
```

它和普通 `Message` 的區別是：

- `Message` 偏“系統內部記錄”
- `NormalizedMessage` 偏“準備發給模型之前的統一輸入”

相關章節：

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### CompactSummary

作用：上下文太長時，用摘要替代舊訊息原文。

最小形狀：

```python
summary = {
    "task_overview": "...",
    "current_state": "...",
    "key_decisions": ["..."],
    "next_steps": ["..."],
}
```

相關章節：

- `s06`
- `s11`

### SystemPromptBlock

作用：把 system prompt 從一整段大字串，拆成若干可管理片段。

最小形狀：

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

你可以把它理解成：

- `text`：這一段提示詞正文
- `cache_scope`：這一段是否可以複用快取

相關章節：

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### PromptParts

作用：在真正拼成 system prompt 之前，先把各部分拆開管理。

最小形狀：

```python
parts = {
    "core": "...",
    "tools": "...",
    "skills": "...",
    "memory": "...",
    "claude_md": "...",
    "dynamic": "...",
}
```

相關章節：

- `s10`

### QueryParams

作用：進入查詢主迴圈時，外部一次性傳進來的輸入集合。

最小形狀：

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "fallback_model": None,
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

它的重要點在於：

- 這是“本次 query 的入口輸入”
- 它和迴圈內部不斷變化的狀態，不是同一層

相關章節：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

### QueryState

作用：儲存一條 query 在多輪迴圈之間不斷變化的流程狀態。

最小形狀：

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "turn_count": 1,
    "max_output_tokens_recovery_count": 0,
    "has_attempted_reactive_compact": False,
    "max_output_tokens_override": None,
    "pending_tool_use_summary": None,
    "stop_hook_active": False,
    "transition": None,
}
```

這類欄位的共同特點是：

- 它們不是對話內容
- 它們是“這一輪該怎麼繼續”的控制狀態

相關章節：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

### TransitionReason

作用：記錄“上一輪為什麼繼續了，而不是結束”。

最小形狀：

```python
transition = {
    "reason": "next_turn",
}
```

在更完整的 query 狀態裡，這個 `reason` 常見會有這些型別：

- `next_turn`
- `reactive_compact_retry`
- `token_budget_continuation`
- `max_output_tokens_recovery`
- `stop_hook_continuation`

它的價值不是炫技，而是讓：

- 日誌更清楚
- 測試更清楚
- 恢復路徑更清楚

相關章節：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

## 2. 工具、許可權與 hook 執行狀態

### ToolSpec

作用：告訴模型“有哪些工具、每個工具要什麼輸入”。

最小形狀：

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

相關章節：

- `s02`
- `s19`

### ToolDispatchMap

作用：把工具名對映到真實執行函式。

最小形狀：

```python
handlers = {
    "read_file": run_read,
    "write_file": run_write,
    "bash": run_bash,
}
```

相關章節：

- `s02`

### ToolUseContext

作用：把工具執行時需要的共享環境打成一個匯流排。

最小形狀：

```python
tool_use_context = {
    "tools": handlers,
    "permission_context": {...},
    "mcp_clients": [],
    "messages": [...],
    "app_state": {...},
    "cwd": "...",
    "read_file_state": {...},
    "notifications": [],
}
```

這層很關鍵。  
因為在更完整的工具執行環境裡，工具拿到的不只是 `tool_input`，還包括：

- 當前許可權環境
- 當前訊息
- 當前 app state
- 當前 MCP client
- 當前檔案讀取快取

相關章節：

- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)
- `s07`
- `s19`

### PermissionRule

作用：描述某類工具呼叫命中後該怎麼處理。

最小形狀：

```python
rule = {
    "tool_name": "bash",
    "rule_content": "rm -rf *",
    "behavior": "deny",
}
```

相關章節：

- `s07`

### PermissionRuleSource

作用：標記一條許可權規則是從哪裡來的。

最小形狀：

```python
source = (
    "userSettings"
    | "projectSettings"
    | "localSettings"
    | "flagSettings"
    | "policySettings"
    | "cliArg"
    | "command"
    | "session"
)
```

這個結構的意義是：

- 你不只知道“有什麼規則”
- 還知道“這條規則是誰加進來的”

相關章節：

- `s07`

### PermissionDecision

作用：表示一次工具呼叫當前該允許、拒絕還是提問。

最小形狀：

```python
decision = {
    "behavior": "allow" | "deny" | "ask",
    "reason": "matched deny rule",
}
```

在更完整的許可權流裡，`ask` 結果還可能帶：

- 修改後的輸入
- 建議寫回哪些規則更新
- 一個後臺自動分類檢查

相關章節：

- `s07`

### PermissionUpdate

作用：描述“這次許可權確認之後，要把什麼改回配置裡”。

最小形狀：

```python
update = {
    "type": "addRules" | "removeRules" | "setMode" | "addDirectories",
    "destination": "userSettings" | "projectSettings" | "localSettings" | "session",
    "rules": [],
}
```

它解決的是一個很容易被漏掉的問題：

使用者這次點了“允許”，到底只是這一次放行，還是要寫回會話、專案，甚至使用者級配置。

相關章節：

- `s07`

### HookContext

作用：把某個 hook 事件發生時的上下文打包給外部指令碼。

最小形狀：

```python
context = {
    "event": "PreToolUse",
    "tool_name": "bash",
    "tool_input": {...},
    "tool_result": "...",
}
```

相關章節：

- `s08`

### RecoveryState

作用：記錄恢復流程已經嘗試到哪裡。

最小形狀：

```python
state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

相關章節：

- `s11`

## 3. 持久化工作狀態

### TodoItem

作用：當前會話裡的輕量計劃項。

最小形狀：

```python
todo = {
    "content": "Read parser.py",
    "status": "pending" | "completed",
}
```

相關章節：

- `s03`

### MemoryEntry

作用：儲存跨會話仍然有價值的資訊。

最小形狀：

```python
memory = {
    "name": "prefer_tabs",
    "description": "User prefers tabs for indentation",
    "type": "user" | "feedback" | "project" | "reference",
    "scope": "private" | "team",
    "body": "...",
}
```

這裡最重要的不是欄位多，而是邊界清楚：

- 只存不容易從當前專案狀態重新推出來的東西
- 記憶可能會過時，要驗證

相關章節：

- `s09`

### TaskRecord

作用：磁碟上的工作圖任務節點。

最小形狀：

```python
task = {
    "id": 12,
    "subject": "Implement auth module",
    "description": "",
    "status": "pending",
    "blockedBy": [],
    "blocks": [],
    "owner": "",
    "worktree": "",
}
```

重點欄位：

- `blockedBy`：誰擋著我
- `blocks`：我擋著誰
- `owner`：誰認領了
- `worktree`：在哪個隔離目錄裡做

相關章節：

- `s12`
- `s17`
- `s18`
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### ScheduleRecord

作用：記錄未來要觸發的排程任務。

最小形狀：

```python
schedule = {
    "id": "job_001",
    "cron": "0 9 * * 1",
    "prompt": "Generate weekly report",
    "recurring": True,
    "durable": True,
    "created_at": 1710000000.0,
    "last_fired_at": None,
}
```

相關章節：

- `s14`

## 4. 執行時執行狀態

### RuntimeTaskState

作用：表示系統裡一個“正在執行的執行單元”。

最小形狀：

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

這和 `TaskRecord` 不是一回事：

- `TaskRecord` 管工作目標
- `RuntimeTaskState` 管當前執行插槽

相關章節：

- `s13`
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### TeamMember

作用：記錄一個持久隊友是誰、在做什麼。

最小形狀：

```python
member = {
    "name": "alice",
    "role": "coder",
    "status": "idle",
}
```

相關章節：

- `s15`
- `s17`

### MessageEnvelope

作用：隊友之間傳遞結構化訊息。

最小形狀：

```python
message = {
    "type": "message" | "shutdown_request" | "plan_approval",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "content": "...",
    "payload": {},
    "timestamp": 1710000000.0,
}
```

相關章節：

- `s15`
- `s16`

### RequestRecord

作用：追蹤一個協議請求當前走到哪裡。

最小形狀：

```python
request = {
    "request_id": "req_001",
    "kind": "shutdown" | "plan_review",
    "status": "pending" | "approved" | "rejected" | "expired",
    "from": "lead",
    "to": "alice",
}
```

相關章節：

- `s16`

### WorktreeRecord

作用：記錄一個任務繫結的隔離工作目錄。

最小形狀：

```python
worktree = {
    "name": "auth-refactor",
    "path": ".worktrees/auth-refactor",
    "branch": "wt/auth-refactor",
    "task_id": 12,
    "status": "active",
}
```

相關章節：

- `s18`

### WorktreeEvent

作用：記錄 worktree 生命週期事件，便於恢復和排查。

最小形狀：

```python
event = {
    "event": "worktree.create.after",
    "task_id": 12,
    "worktree": "auth-refactor",
    "ts": 1710000000.0,
}
```

相關章節：

- `s18`

## 5. 外部平臺與 MCP 狀態

### ScopedMcpServerConfig

作用：描述一個 MCP server 應該如何連線，以及它的配置來自哪個作用域。

最小形狀：

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

這個 `scope` 很重要，因為 server 配置可能來自：

- 本地
- 使用者
- 專案
- 動態注入
- 外掛或託管來源

相關章節：

- `s19`
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

### MCPServerConnectionState

作用：表示一個 MCP server 當前連到了哪一步。

最小形狀：

```python
server_state = {
    "name": "postgres",
    "type": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

這層特別重要，因為“有沒有接上”不是布林值，而是多種狀態：

- `connected`
- `pending`
- `failed`
- `needs-auth`
- `disabled`

相關章節：

- `s19`
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

### MCPToolSpec

作用：把外部 MCP 工具轉換成 agent 內部統一工具定義。

最小形狀：

```python
mcp_tool = {
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...},
}
```

相關章節：

- `s19`

### ElicitationRequest

作用：表示 MCP server 反過來向用戶請求額外輸入。

最小形狀：

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

它提醒你一件事：

- MCP 不只是“模型主動調工具”
- 外部 server 也可能反過來請求補充輸入

相關章節：

- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## 最後用一句話把它們串起來

如果你只想記一條匯流排索，可以記這個：

```text
messages / prompt / query state
  管本輪輸入和繼續理由

tools / permissions / hooks
  管動作怎麼安全執行

memory / task / schedule
  管跨輪、跨會話的持久工作

runtime task / team / worktree
  管當前執行車道

mcp
  管系統怎樣向外接能力
```

這份總表最好配合 [`s00-architecture-overview.md`](./s00-architecture-overview.md) 和 [`entity-map.md`](./entity-map.md) 一起看。

## 教學邊界

這份總表只負責做兩件事：

- 幫你確認一個狀態到底屬於哪一層
- 幫你確認這個狀態大概長什麼樣

它不負責窮舉真實系統裡的每一個欄位、每一條相容分支、每一種產品化補丁。

如果你已經知道某個狀態歸誰管、什麼時候建立、什麼時候銷燬，再回到對應章節看執行路徑，理解會順很多。
