# s19: MCP & Plugin System (MCP 與外掛系統)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

> *工具不必都寫死在主程式裡。外部程序也可以把能力接進你的 agent。*

## 這一章到底在講什麼

前面所有章節裡，工具基本都寫在你自己的 Python 程式碼裡。

這當然是最適合教學的起點。

但真實系統走到一定階段以後，會很自然地遇到這個需求：

> “能不能讓外部程式也把工具接進來，而不用每次都改主程式？”

這就是 MCP 要解決的問題。

## 先用最簡單的話解釋 MCP

你可以先把 MCP 理解成：

**一套讓 agent 和外部工具程式對話的統一協議。**

在教學版裡，不必一開始就背很多協議細節。  
你只要先抓住這條主線：

1. 啟動一個外部工具服務程序
2. 問它“你有哪些工具”
3. 當模型要用它的工具時，把請求轉發給它
4. 再把結果帶回 agent 主迴圈

這已經夠理解 80% 的核心機制了。

## 為什麼這一章放在最後

因為 MCP 不是主迴圈的起點，而是主迴圈穩定之後的擴充套件層。

如果你還沒真正理解：

- agent loop
- tool call
- permission
- task
- worktree

那 MCP 只會看起來像又一套複雜介面。

但當你已經有了前面的心智，再看 MCP，你會發現它本質上只是：

**把“工具來源”從“本地硬編碼”升級成“外部可插拔”。**

## 建議聯讀

- 如果你只把 MCP 理解成“遠端 tools”，先看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)，把 tools、resources、prompts、plugin 中介層一起放回平臺邊界裡。
- 如果你想確認外部能力為什麼仍然要回到同一條執行面，回看 [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)。
- 如果你開始把“query 控制平面”和“外部能力路由”完全分開理解，建議配合看 [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)。

## 最小心智模型

```text
LLM
  |
  | asks to call a tool
  v
Agent tool router
  |
  +-- native tool  -> 本地 Python handler
  |
  +-- MCP tool     -> 外部 MCP server
                        |
                        v
                    return result
```

## 最小系統裡最重要的三件事

### 1. 有一個 MCP client

它負責：

- 啟動外部程序
- 傳送請求
- 接收響應

### 2. 有一個工具名字首規則

這是為了避免命名衝突。

最常見的做法是：

```text
mcp__{server}__{tool}
```

比如：

```text
mcp__postgres__query
mcp__browser__open_tab
```

這樣一眼就知道：

- 這是 MCP 工具
- 它來自哪個 server
- 它原始工具名是什麼

### 3. 有一個統一路由器

路由器只做一件事：

- 如果是本地工具，就交給本地 handler
- 如果是 MCP 工具，就交給 MCP client

## Plugin 又是什麼

如果 MCP 解決的是“外部工具怎麼通訊”，  
那 plugin 解決的是“這些外部工具配置怎麼被發現”。

最小 plugin 可以非常簡單：

```text
.claude-plugin/
  plugin.json
```

裡面寫：

- 外掛名
- 版本
- 它提供哪些 MCP server
- 每個 server 的啟動命令是什麼

## 最小配置長什麼樣

```json
{
  "name": "my-db-tools",
  "version": "1.0.0",
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"]
    }
  }
}
```

這個配置並不複雜。

它本質上只是在告訴主程式：

> “如果你想接這個 server，就用這條命令把它拉起來。”

## 最小實現步驟

### 第一步：寫一個 `MCPClient`

它至少要有三個能力：

- `connect()`
- `list_tools()`
- `call_tool()`

### 第二步：把外部工具標準化成 agent 能看懂的工具定義

也就是說，把 MCP server 暴露的工具，轉成 agent 工具池裡的統一格式。

### 第三步：加字首

這樣主程式就能區分：

- 本地工具
- 外部工具

### 第四步：寫一個 router

```python
if tool_name.startswith("mcp__"):
    return mcp_router.call(tool_name, arguments)
else:
    return native_handler(arguments)
```

### 第五步：仍然走同一條許可權管道

這是非常關鍵的一點：

**MCP 工具雖然來自外部，但不能繞開 permission。**

不然你等於在系統邊上開了個安全後門。

如果你想把這一層再收得更穩，最好再把結果也標準化回同一條匯流排：

```python
{
    "source": "mcp",
    "server": "figma",
    "tool": "inspect",
    "status": "ok",
    "preview": "...",
}
```

這表示：

- 路由前要過共享許可權閘門
- 路由後不論本地還是遠端，結果都要轉成主迴圈看得懂的統一格式

## 如何接到整個系統裡

如果你讀到這裡還覺得 MCP 像“外掛”，通常是因為沒有把它放回整條主迴路裡。

更完整的接法應該看成：

```text
啟動時
  ->
PluginLoader 找到 manifest
  ->
得到 server 配置
  ->
MCP client 連線 server
  ->
list_tools 並標準化名字
  ->
和 native tools 一起合併進同一個工具池

執行時
  ->
LLM 產出 tool_use
  ->
統一許可權閘門
  ->
native route 或 mcp route
  ->
結果標準化
  ->
tool_result 回到同一個主迴圈
```

這段流程裡最關鍵的不是“外部”兩個字，而是：

**進入方式不同，但進入後必須回到同一條控制面和執行面。**

## Plugin、MCP Server、MCP Tool 不要混成一層

這是初學者最容易在本章裡打結的地方。

可以直接按下面三層記：

| 層級 | 它是什麼 | 它負責什麼 |
|---|---|---|
| plugin manifest | 一份配置宣告 | 告訴系統要發現和啟動哪些 server |
| MCP server | 一個外部程序 / 連線物件 | 對外暴露一組能力 |
| MCP tool | server 暴露的一項具體呼叫能力 | 真正被模型點名呼叫 |

換成一句最短的話說：

- plugin 負責“發現”
- server 負責“連線”
- tool 負責“呼叫”

只要這三層還分得清，MCP 這章的主體心智就不會亂。

## 這一章最關鍵的資料結構

### 1. server 配置

```python
{
    "command": "npx",
    "args": ["-y", "..."],
    "env": {}
}
```

### 2. 標準化後的工具定義

```python
{
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...}
}
```

### 3. client 登錄檔

```python
clients = {
    "postgres": mcp_client_instance
}
```

## 初學者最容易被帶偏的地方

### 1. 一上來講太多協議細節

這章最容易失控。

因為一旦開始講完整協議生態，很快會出現：

- transports
- auth
- resources
- prompts
- streaming
- connection recovery

這些都存在，但不該擋住主線。

主線只有一句話：

**外部工具也能像本地工具一樣接進 agent。**

### 2. 把 MCP 當成一套完全不同的工具系統

不是。

它最終仍然應該匯入你原來的工具體系：

- 一樣要註冊
- 一樣要出現在工具池裡
- 一樣要過許可權
- 一樣要返回 `tool_result`

### 3. 忽略命名與路由

如果沒有統一字首和統一路由，系統會很快亂掉。

## 教學邊界

這一章正文先停在 `tools-first` 是對的。

因為教學主線最需要先講清的是：

- 外部能力怎樣被發現
- 怎樣被統一命名和路由
- 怎樣繼續經過同一條許可權與 `tool_result` 迴流

只要這一層已經成立，讀者就已經真正理解了：

**MCP / plugin 不是外掛，而是接回同一控制面的外部能力入口。**

transport、認證、resources、prompts、外掛生命週期這些更大範圍的內容，應該放到平臺橋接資料裡繼續展開。

## 正文先停在 tools-first，平臺層再看橋接文件

這一章的正文故意停在“外部工具如何接進 agent”這一層。  
這是教學上的刻意取捨，不是缺失。

如果你準備繼續補平臺邊界，再去看：

- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

那篇會把 MCP 再往上補成一張平臺地圖，包括：

- server 配置作用域
- transport 型別
- 連線狀態：`connected / pending / needs-auth / failed / disabled`
- tools 之外的 `resources / prompts / elicitation`
- auth 該放在哪一層理解

這樣安排的好處是：

- 正文不失焦
- 讀者又不會誤以為 MCP 只有一個 `list_tools + call_tool`

## 這一章和全倉庫的關係

如果說前 18 章都在教你把系統內部搭起來，  
那 `s19` 在教你：

**如何把系統向外開啟。**

從這裡開始，工具不再只來自你手寫的 Python 檔案，  
還可以來自別的程序、別的系統、別的服務。

這就是為什麼它適合作為最後一章。

## 學完這章後，你應該能回答

- MCP 的核心到底是什麼？
- 為什麼它應該放在整個學習路徑的最後？
- 為什麼 MCP 工具也必須走同一條許可權與路由邏輯？
- plugin 和 MCP 分別解決什麼問題？

---

**一句話記住：MCP 的本質，不是協議名詞堆砌，而是把外部工具安全、統一地接進你的 agent。**
