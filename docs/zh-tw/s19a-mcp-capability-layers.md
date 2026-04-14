# s19a: MCP Capability Layers (MCP 能力層地圖)

> `s19` 的主線仍然應該堅持“先做 tools-first”。  
> 這篇橋接文件負責補上另一層心智：
>
> **MCP 不只是外部工具接入，它是一組能力層。**

## 建議怎麼聯讀

如果你希望 MCP 這塊既不學偏，也不學淺，推薦這樣看：

- 先看 [`s19-mcp-plugin.md`](./s19-mcp-plugin.md)，先把 tools-first 主線走通。
- 再看 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)，確認外部能力最後怎樣接回統一工具匯流排。
- 如果狀態結構開始混，再對照 [`data-structures.md`](./data-structures.md)。
- 如果概念邊界開始混，再回 [`glossary.md`](./glossary.md) 和 [`entity-map.md`](./entity-map.md)。

## 為什麼要單獨補這一篇

如果你是為了教學，從 0 到 1 手搓一個類似系統，那麼 `s19` 主線先只講外部工具，這是對的。

因為最容易理解的入口就是：

- 連線一個外部 server
- 拿到工具列表
- 呼叫工具
- 把結果帶回 agent

但如果你想把系統做到接近 95%-99% 的還原度，你遲早會遇到這些問題：

- server 是用 stdio、http、sse 還是 ws 連線？
- 為什麼有些 server 是 connected，有些是 pending，有些是 needs-auth？
- tools 之外，resources 和 prompts 是什麼位置？
- elicitation 為什麼會變成一類特殊互動？
- OAuth / XAA 這種認證流程該放在哪一層理解？

這時候如果沒有一張“能力層地圖”，MCP 就會越學越散。

## 先解釋幾個名詞

### 什麼是能力層

能力層，就是把一個複雜系統拆成幾層職責清楚的面。

這裡的意思是：

> 不要把所有 MCP 細節混成一團，而要知道每一層到底解決什麼問題。

### 什麼是 transport

`transport` 可以理解成“連線通道”。

比如：

- stdio
- http
- sse
- websocket

### 什麼是 elicitation

這個詞比較生。

你可以先把它理解成：

> 外部 MCP server 反過來向用戶請求額外輸入的一種互動。

也就是說，不再只是 agent 主動調工具，而是 server 也能說：

“我還需要你給我一點資訊，我才能繼續。”

## 最小心智模型

先把 MCP 畫成 6 層：

```text
1. Config Layer
   server 配置長什麼樣

2. Transport Layer
   用什麼通道連 server

3. Connection State Layer
   現在是 connected / pending / failed / needs-auth

4. Capability Layer
   tools / resources / prompts / elicitation

5. Auth Layer
   是否需要認證，認證狀態如何

6. Router Integration Layer
   如何接回 tool router / permission / notifications
```

最重要的一點是：

**tools 只是其中一層，不是全部。**

## 為什麼正文仍然應該堅持 tools-first

這點非常重要。

雖然 MCP 平臺本身有多層能力，但正文主線仍然應該這樣安排：

### 第一步：先教外部 tools

因為它和前面的主線最自然銜接：

- 本地工具
- 外部工具
- 同一條 router

### 第二步：再告訴讀者還有其他能力層

例如：

- resources
- prompts
- elicitation
- auth

### 第三步：再決定是否繼續實現

這才符合你的教學目標：

**先做出類似系統，再補平臺層高階能力。**

## 關鍵資料結構

### 1. ScopedMcpServerConfig

最小教學版建議至少讓讀者看到這個概念：

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

這裡的 `scope` 很重要。

因為 server 配置不一定都來自同一個地方。

### 2. MCP Connection State

```python
server_state = {
    "name": "postgres",
    "status": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

### 3. MCPToolSpec

```python
tool = {
    "name": "mcp__postgres__query",
    "description": "...",
    "input_schema": {...},
}
```

### 4. ElicitationRequest

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

這一步不是要求你主線立刻實現它，而是要讓讀者知道：

**MCP 不一定永遠只是“模型調工具”。**

## 一張更完整但仍然清楚的圖

```text
MCP Config
  |
  v
Transport
  |
  v
Connection State
  |
  +-- connected
  +-- pending
  +-- needs-auth
  +-- failed
  |
  v
Capabilities
  +-- tools
  +-- resources
  +-- prompts
  +-- elicitation
  |
  v
Router / Permission / Notification Integration
```

## Auth 為什麼不要在主線裡講太多

這也是教學取捨裡很重要的一點。

認證是真實系統裡確實存在的能力層。  
但如果正文一開始就掉進 OAuth/XAA 流程，初學者會立刻丟主線。

所以更好的講法是：

- 先告訴讀者：有 auth layer
- 再告訴讀者：connected / needs-auth 是不同連線狀態
- 只有做平臺層進階時，再詳細展開認證流程

這就既沒有幻覺，也沒有把人帶偏。

## 它和 `s19`、`s02a` 的關係

- `s19` 正文繼續負責 tools-first 教學
- 這篇負責補清平臺層地圖
- `s02a` 的 Tool Control Plane 則解釋 MCP 最終怎麼接回統一工具匯流排

三者合在一起，讀者才會真正知道：

**MCP 是外部能力平臺，而 tools 只是它最先進入主線的那個切面。**

## 初學者最容易犯的錯

### 1. 把 MCP 只理解成“外部工具目錄”

這會讓後面遇到 auth / resources / prompts / elicitation 時很困惑。

### 2. 一上來就沉迷 transport 和 OAuth 細節

這樣會直接打斷主線。

### 3. 讓 MCP 工具繞過 permission

這會在系統邊上開一個很危險的後門。

### 4. 不區分 server 配置、連線狀態、能力暴露

這三層一混，平臺層就會越學越亂。

## 教學邊界

這篇最重要的，不是把 MCP 所有外設細節都講完，而是先守住四層邊界：

- server 配置
- 連線狀態
- capability 暴露
- permission / routing 接入點

只要這四層不混，你就已經能自己手搓一個接近真實系統主脈絡的外部能力入口。  
認證狀態機、resource/prompt 接入、server 回問和重連策略，都屬於後續平臺擴充套件。

## 一句話記住

**`s19` 主線應該先教“外部工具接入”，而平臺層還需要額外理解 MCP 的能力層地圖。**
