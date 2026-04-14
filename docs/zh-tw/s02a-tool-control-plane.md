# s02a: Tool Control Plane (工具控制平面)

> 這篇橋接文件用來回答另一個關鍵問題：
>
> **為什麼“工具系統”不只是一個 `tool_name -> handler` 的對映表？**

## 這一篇為什麼要存在

`s02` 先教你工具註冊和分發，這完全正確。  
因為如果你一開始連工具呼叫都沒做出來，後面的一切都無從談起。

但當系統長大以後，工具層會逐漸承載越來越多的責任：

- 許可權判斷
- MCP 接入
- 通知傳送
- subagent / teammate 共享狀態
- file state cache
- 當前訊息和當前會話環境
- 某些工具專屬限制

這時候，“工具層”就已經不是一張函式表了。

它更像一條匯流排：

**模型透過工具名發出動作意圖，系統透過工具控制平面決定這條意圖在什麼環境裡執行。**

## 先解釋幾個名詞

### 什麼是工具控制平面

這裡的“控制平面”可以繼續沿用上一份橋接文件的理解：

> 不直接做業務結果，而是負責協調工具如何執行的一層。

它關心的問題不是“這個工具最後返回了什麼”，而是：

- 它在哪執行
- 它有沒有許可權
- 它可不可以訪問某些共享狀態
- 它是本地工具還是外部工具

### 什麼是執行上下文

執行上下文，就是工具執行時能看到的環境。

例如：

- 當前工作目錄
- 當前 app state
- 當前訊息列表
- 當前許可權模式
- 當前可用 MCP client

### 什麼是能力來源

不是所有工具都來自同一個地方。

系統裡常見的能力來源有：

- 本地原生工具
- MCP 外部工具
- agent 工具
- task / worktree / team 這類平臺工具

## 最小心智模型

工具系統可以先畫成 4 層：

```text
1. ToolSpec
   模型看見的工具名字、描述、輸入 schema

2. Tool Router
   根據工具名把請求送去正確的能力來源

3. ToolUseContext
   工具執行時能訪問的共享環境

4. Tool Result Envelope
   把輸出包裝回主迴圈
```

最重要的升級點在第三層：

**更完整系統的核心，不是 tool table，而是 ToolUseContext。**

## 關鍵資料結構

### 1. ToolSpec

這還是最基礎的結構：

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

### 2. ToolDispatchMap

```python
handlers = {
    "read_file": read_file,
    "write_file": write_file,
    "bash": run_bash,
}
```

這依舊需要，但它不是全部。

### 3. ToolUseContext

教學版可以先做一個簡化版本：

```python
tool_use_context = {
    "tools": handlers,
    "permission_context": {...},
    "mcp_clients": {},
    "messages": [...],
    "app_state": {...},
    "notifications": [],
    "cwd": "...",
}
```

這個結構的關鍵點是：

- 工具不再只拿到“輸入引數”
- 工具還能拿到“共享執行環境”

### 4. ToolResultEnvelope

不要把返回值只想成字串。

更穩妥的形狀是：

```python
result = {
    "ok": True,
    "content": "...",
    "is_error": False,
    "attachments": [],
}
```

這樣後面你才能平滑承接：

- 普通文字結果
- 結構化結果
- 錯誤結果
- 附件類結果

## 為什麼更完整的系統一定會出現 ToolUseContext

想象兩個系統。

### 系統 A：只有 dispatch map

```python
output = handlers[tool_name](**tool_input)
```

這適合最小 demo。

### 系統 B：有 ToolUseContext

```python
output = handlers[tool_name](tool_input, tool_use_context)
```

這個版本才更接近一個真實平臺。

因為工具現在不只是“做一個動作”，而是在一個複雜系統裡做動作。

例如：

- `bash` 要看許可權
- `mcp__postgres__query` 要找對應 client
- `agent` 工具要建立子執行環境
- `task_output` 工具可能要寫磁碟併發通知

這些都要求它們共享同一個上下文匯流排。

## 最小實現

### 第一步：仍然保留 ToolSpec 和 handler

這個主線不要丟。

### 第二步：引入一個統一 context

```python
class ToolUseContext:
    def __init__(self):
        self.handlers = {}
        self.permission_context = {}
        self.mcp_clients = {}
        self.messages = []
        self.app_state = {}
        self.notifications = []
```

### 第三步：讓所有 handler 都能看到 context

```python
def run_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    handler = ctx.handlers[tool_name]
    return handler(tool_input, ctx)
```

### 第四步：在 router 層分不同能力來源

```python
def route_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    if tool_name.startswith("mcp__"):
        return run_mcp_tool(tool_name, tool_input, ctx)
    return run_native_tool(tool_name, tool_input, ctx)
```

## 一張應該講清楚的圖

```text
LLM tool call
  |
  v
Tool Router
  |
  +-- native tools ----------> local handlers
  |
  +-- mcp tools -------------> mcp client
  |
  +-- agent/task/team tools --> platform handlers
            |
            v
       ToolUseContext
         - permissions
         - messages
         - app state
         - notifications
         - mcp clients
```

## 它和 `s02`、`s19` 的關係

- `s02` 先教你工具呼叫為什麼成立
- 這篇解釋更完整的系統裡工具層為什麼會長成一個控制平面
- `s19` 再把 MCP 作為外部能力來源接進來

也就是說：

**MCP 不是另一套獨立系統，而是 Tool Control Plane 的一個能力來源。**

## 初學者最容易犯的錯

### 1. 以為工具上下文只是 `cwd`

不是。

更完整的系統裡，工具上下文往往還包含許可權、狀態、外部連線和通知介面。

### 2. 讓每個工具自己去全域性變數裡找環境

這樣工具層會變得非常散。

更清楚的做法，是顯式傳一個統一 context。

### 3. 把本地工具和 MCP 工具拆成完全不同體系

這會讓系統邊界越來越亂。

更好的方式是：

- 能力來源不同
- 但都匯入統一 router 和統一 result envelope

### 4. 把 tool result 永遠當成純字串

這樣後面接附件、錯誤、結構化資訊時會很彆扭。

## 教學邊界

這篇最重要的，不是把工具層做成一個龐大的企業匯流排，而是先把下面三層邊界講清：

- tool call 不是直接執行，而是先進入統一排程入口
- 工具 handler 不應該各自去偷拿環境，而應該共享一份顯式 `ToolUseContext`
- 本地工具、外掛工具、MCP 工具可以來源不同，但結果都應該回到統一控制面

型別化上下文、能力註冊中心、大結果儲存和更細的工具限額，都是你把這條最小控制匯流排講穩以後再補的擴充套件。

## 一句話記住

**最小工具系統靠 dispatch map，更完整的工具系統靠 ToolUseContext 這條控制匯流排。**
