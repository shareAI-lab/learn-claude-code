# s19a: MCP Capability Layers

> `s19` の主線は引き続き tools-first で進めるべきです。
> その上で、この bridge doc は次の心智を足します。
>
> **MCP は単なる外部 tool 接続ではなく、複数の capability layer を持つ platform です。**

## 主線とどう併読するか

MCP を主線から外れずに学ぶなら次の順がよいです。

- まず [`s19-mcp-plugin.md`](./s19-mcp-plugin.md) を読み、tools-first の入口を固める
- 次に [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) を見直し、外部 capability がどう unified tool bus に戻るかを見る
- state record が混ざり始めたら [`data-structures.md`](./data-structures.md) を見直す
- concept boundary が混ざり始めたら [`glossary.md`](./glossary.md) と [`entity-map.md`](./entity-map.md) を見直す

## なぜ別立てで必要か

教材 repo として、正文を external tools から始めるのは正しいです。

最も入りやすい入口は:

- 外部 server に接続する
- tool 定義を受け取る
- tool を呼ぶ
- 結果を agent へ戻す

しかし完成度を上げようとすると、すぐ次の問いに出会います。

- server は stdio / HTTP / SSE / WebSocket のどれでつながるのか
- なぜ `connected` の server もあれば `pending` や `needs-auth` の server もあるのか
- resources や prompts は tools とどう並ぶのか
- elicitation はなぜ特別な対話になるのか
- OAuth のような auth flow はどの層で理解すべきか

capability-layer map がないと、MCP は急に散らばって見えます。

## まず用語

### capability layer とは

capability layer は:

> 大きな system の中の 1 つの責務面

です。

MCP のすべてを 1 つの袋に入れないための考え方です。

### transport とは

transport は接続通路です。

- stdio
- HTTP
- SSE
- WebSocket

### elicitation とは

これは見慣れない用語ですが、教材版では次の理解で十分です。

> MCP server 側が追加情報を要求し、user からさらに入力を引き出す対話

つまり常に:

> agent calls tool -> tool returns result

だけとは限らず、server 側から:

> 続けるためにもっと入力が必要

と言ってくる場合があります。

## 最小の心智モデル

MCP を 6 層で見ると整理しやすいです。

```text
1. Config Layer
   server 設定がどう表現されるか

2. Transport Layer
   何の通路で接続するか

3. Connection State Layer
   connected / pending / failed / needs-auth

4. Capability Layer
   tools / resources / prompts / elicitation

5. Auth Layer
   認証が必要か、認証状態は何か

6. Router Integration Layer
   tool routing / permission / notifications にどう戻るか
```

ここで最重要なのは:

**tools は一層であって、MCP の全体ではない**

という点です。

## なぜ正文は tools-first のままでよいか

教材として大事なポイントです。

MCP に複数 layer があっても、正文主線はまず次で十分です。

### Step 1: 外部 tools から入る

これは読者がすでに学んだものと最も自然につながります。

- local tools
- external tools
- 1 本の shared router

### Step 2: その上で他の layer があると知らせる

例えば:

- resources
- prompts
- elicitation
- auth

### Step 3: どこまで実装するかを決める

これが教材 repo の目的に合っています。

**まず似た system を作り、その後で platform layer を厚くする**

## 主要 record

### 1. `ScopedMcpServerConfig`

教材版でも最低限この概念は見せるべきです。

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

`scope` が重要なのは、server config が 1 つの場所からだけ来るとは限らないからです。

### 2. MCP connection state

```python
server_state = {
    "name": "postgres",
    "status": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

### 3. `MCPToolSpec`

```python
tool = {
    "name": "mcp__postgres__query",
    "description": "...",
    "input_schema": {...},
}
```

### 4. `ElicitationRequest`

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

ここでの教材上の要点は、elicitation を今すぐ全部実装することではありません。

要点は:

**MCP は常に一方向の tool invocation だけとは限らない**

という点です。

## より整理された図

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

## なぜ auth を主線の中心にしない方がよいか

auth は platform 全体では本物の layer です。

しかし正文が早い段階で OAuth や vendor 固有 detail へ落ちると、初学者は system shape を失います。

教材としては次の順がよいです。

- まず auth layer が存在すると知らせる
- 次に `connected` と `needs-auth` が違う connection state だと教える
- さらに進んだ platform work の段階で auth state machine を詳しく扱う

これなら正確さを保ちつつ、主線を壊しません。

## `s19` と `s02a` との関係

- `s19` 本文は tools-first の external capability path を教える
- この note は broader platform map を補う
- `s02a` は MCP capability が unified tool control plane にどう戻るかを補う

三つを合わせて初めて、読者は本当の構図を持てます。

**MCP は外部 capability platform であり、tools はその最初の切り口にすぎない**

## 初学者がやりがちな間違い

### 1. MCP を外部 tool catalog だけだと思う

その理解だと resources / prompts / auth / elicitation が後で急に見えて混乱します。

### 2. transport や OAuth detail に最初から沈み込む

これでは主線が壊れます。

### 3. MCP tool を permission の外に置く

system boundary に危険な横穴を開けます。

### 4. server config・connection state・exposed capabilities を一つに混ぜる

この三層は概念的に分けておくべきです。
