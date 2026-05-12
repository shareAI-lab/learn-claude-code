# s19: MCP & Plugin

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

> *すべての能力を主プログラムへ直書きする必要はない。外部能力も同じ routing 面へ接続できる。*

## この章が本当に教えるもの

前の章までは、ツールの多くが自分の Python コード内にありました。

これは教学として正しい出発点です。

しかしシステムが大きくなると、自然に次の要望が出ます。

> "外部プログラムの能力を、毎回主プログラムを書き換えずに使えないか?"

それに答えるのが MCP です。

## MCP を一番簡単に言うと

MCP は:

**agent が外部 capability server と会話するための標準的な方法**

と考えれば十分です。

主線は次の 4 ステップです。

1. 外部 server を起動する
2. どんなツールがあるか聞く
3. 必要な呼び出しをその server へ転送する
4. 結果を標準化して主ループへ戻す

## なぜ最後の章なのか

MCP は出発点ではありません。

先に理解しておくべきものがあります。

- agent loop
- tool routing
- permissions
- tasks
- worktree isolation

それらが見えてからだと、MCP は:

**新しい capability source**

として自然に理解できます。

## 主線とどう併読するか

- MCP を「遠隔 tool」だけで理解しているなら、[`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) を読んで tools、resources、prompts、plugin discovery を 1 つの platform boundary へ戻します。
- 外部 capability がなぜ同じ execution surface へ戻るのかを確かめたいなら、[`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md) を併読します。
- query control と外部 capability routing が頭の中で分離し始めたら、[`s00a-query-control-plane.md`](./s00a-query-control-plane.md) に戻ります。

## 最小の心智モデル

```text
LLM
  |
  | tool を呼びたい
  v
Agent tool router
  |
  +-- native tool  -> local Python handler
  |
  +-- MCP tool     -> external MCP server
                        |
                        v
                    return result
```

## 重要な 3 要素

### 1. `MCPClient`

役割:

- server へ接続
- tool 一覧取得
- tool 呼び出し

### 2. 命名規則

外部ツールとローカルツールが衝突しないように prefix を付けます。

```text
mcp__{server}__{tool}
```

例:

```text
mcp__postgres__query
mcp__browser__open_tab
```

### 3. 1 本の unified router

```python
if tool_name.startswith("mcp__"):
    return mcp_router.call(tool_name, arguments)
else:
    return native_handler(arguments)
```

## Plugin は何をするか

MCP が:

> 外部 server とどう会話するか

を扱うなら、plugin は:

> その server をどう発見し、どう設定するか

を扱います。

最小 plugin は:

```text
.claude-plugin/
  plugin.json
```

だけでも十分です。

## 最小設定

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

これは要するに:

> "この server が必要なら、このコマンドで起動する"

と主プログラムへ教えているだけです。

## システム全体へどう接続するか

MCP が急に難しく見えるのは、別世界の仕組みとして見てしまうときです。  
より安定した心智モデルは次です。

```text
startup
  ->
plugin loader が manifest を見つける
  ->
server config を取り出す
  ->
MCP client が connect / list_tools する
  ->
external tools を同じ tool pool に正規化して入れる

runtime
  ->
LLM が tool_use を出す
  ->
共有 permission gate
  ->
native route または MCP route
  ->
result normalization
  ->
同じ loop へ tool_result を返す
```

入口は違っても、control plane と execution plane は同じです。

## 重要なデータ構造

### 1. server config

```python
{
    "command": "npx",
    "args": ["-y", "..."],
    "env": {}
}
```

### 2. 標準化された外部ツール定義

```python
{
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...}
}
```

### 3. client registry

```python
clients = {
    "postgres": mcp_client_instance
}
```

## 絶対に崩してはいけない境界

この章で最も重要なのは:

**外部ツールも同じ permission 面を通る**

ということです。

MCP が permission を素通りしたら、外側に安全穴を開けるだけです。

## Plugin / Server / Tool を同じ層にしない

| 層 | 何か | 何を担当するか |
|---|---|---|
| plugin manifest | 設定宣言 | どの server を見つけて起動するかを教える |
| MCP server | 外部 process / connection | 能力の集合を expose する |
| MCP tool | server が出す 1 つの callable capability | モデルが実際に呼ぶ対象 |

最短で覚えるなら:

- plugin = discovery
- server = connection
- tool = invocation

## 初学者が迷いやすい点

### 1. いきなりプロトコル細部へ入る

先に見るべきは capability routing です。

### 2. MCP を別世界だと思う

実際には、同じ routing、同じ permission、同じ result append に戻します。

### 3. 正規化を省く

外部ツールをローカルツールと同じ形へ揃えないと、後の心智が急に重くなります。

## Try It

```sh
cd learn-claude-code
python agents/s19_mcp_plugin.py
```
