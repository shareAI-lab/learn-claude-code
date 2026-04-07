# s00b: 1 リクエストのライフサイクル

> これは橋渡し文書です。  
> 章ごとの説明を、1本の実行の流れとしてつなぎ直します。
>
> 問いたいのは次です。
>
> **ユーザーの一言が system に入ってから、どう流れ、どこで状態が変わり、どう loop に戻るのか。**

## なぜ必要か

章を順に読むと、個別の仕組みは理解できます。

- `s01`: loop
- `s02`: tools
- `s07`: permissions
- `s09`: memory
- `s12-s19`: tasks / teams / worktree / MCP

しかし実装段階では、次の疑問で詰まりやすいです。

- 先に走るのは prompt か memory か
- tool 実行前に permissions と hooks はどこへ入るのか
- task、runtime task、teammate、worktree はどの段で関わるのか

この文書はその縦の流れをまとめます。

## まず全体図

```text
ユーザー要求
  |
  v
Query State 初期化
  |
  v
system prompt / messages / reminders を組み立てる
  |
  v
モデル呼び出し
  |
  +-- 普通の応答 --------------------------> 今回の request は終了
  |
  +-- tool_use
        |
        v
    Tool Router
        |
        +-- permission gate
        +-- hook interception
        +-- native tool / task / teammate / MCP
        |
        v
    実行結果
        |
        +-- task / runtime / memory / worktree 状態を書き換える場合がある
        |
        v
    tool_result を messages へ write-back
        |
        v
    Query State 更新
        |
        v
    次ターン
```

## 第 1 段: Query State を作る

ユーザーが:

```text
tests/test_auth.py の失敗を直して、原因も説明して
```

と言ったとき、最初に起きるのは shell 実行ではありません。

まず「今回の request の状態」が作られます。

```python
query_state = {
    "messages": [{"role": "user", "content": user_text}],
    "turn_count": 1,
    "transition": None,
    "tool_use_context": {...},
}
```

ポイントは:

**1 リクエスト = 1 API call ではなく、複数ターンにまたがる処理**

ということです。

## 第 2 段: モデル入力を組み立てる

実システムは、生の `messages` だけをそのまま送らないことが多いです。

組み立てる対象はたとえば:

- system prompt blocks
- normalized messages
- memory section
- reminders
- tool list

つまりモデルが実際に見るのは:

```text
system prompt
+ normalized messages
+ optional memory / reminders / attachments
+ tools
```

ここで大事なのは:

**system prompt は入力全体ではなく、その一部**

だということです。

## 第 3 段: モデルは 2 種類の出力を返す

### 1. 普通の回答

結論や説明だけを返し、今回の request が終わる場合です。

### 2. 動作意図

tool call です。

例:

```text
read_file(...)
bash(...)
todo_write(...)
agent(...)
mcp__server__tool(...)
```

ここで system が受け取るのは単なる文章ではなく:

> モデルが「現実の動作を起こしたい」という意図

です。

## 第 4 段: Tool Router が受け取る

`tool_use` が出たら、次は tool control plane の責任です。

最低でも次を決めます。

1. これはどの tool か
2. どの handler / capability へ送るか
3. 実行前に permission が必要か
4. hook が割り込むか
5. どの共有状態へアクセスするか

## 第 5 段: Permission が gate をかける

危険な動作は、そのまま実行されるべきではありません。

たとえば:

- file write
- bash
- 外部 service 呼び出し
- worktree の削除

ここで system は:

```text
deny
  -> mode
  -> allow
  -> ask
```

のような判断経路を持ちます。

permission が扱うのは:

> この動作を起こしてよいか

です。

## 第 6 段: Hook が周辺ロジックを足す

hook は permission とは別です。

hook は:

- 実行前の補助チェック
- 実行後の記録
- 補助メッセージの注入

など、loop の周辺で side effect を足します。

つまり:

- permission は gate
- hook は extension

です。

## 第 7 段: 実行結果が状態を変える

tool は text だけを返すとは限りません。

実行によって:

- task board が更新される
- runtime task が生成される
- memory 候補が増える
- worktree lane が作られる
- teammate へ request が飛ぶ
- MCP resource / tool result が返る

といった状態変化が起きます。

ここでの大原則は:

**tool result は内容を返すだけでなく、system state を進める**

ということです。

## 第 8 段: tool_result を loop へ戻す

最後に system は結果を `messages` へ戻します。

```python
messages.append({
    "role": "user",
    "content": [
        {"type": "tool_result", ...}
    ],
})
```

そして query state を更新し:

- `turn_count`
- `transition`
- compact / recovery flags

などを整えて、次ターンへ進みます。

## 後半章はどこで関わるか

| 仕組み | 1 request の中での役割 |
|---|---|
| `s09` memory | 入力 assembly の一部になる |
| `s10` prompt pipeline | 各 source を 1 つの model input へ組む |
| `s12` task | durable work goal を持つ |
| `s13` runtime task | 今動いている execution slot を持つ |
| `s15-s17` teammate / protocol / autonomy | request を actor 間で回す |
| `s18` worktree | 実行ディレクトリを分離する |
| `s19` MCP | 外部 capability provider と接続する |

## 一文で覚える

**1 request の本体は「モデルを 1 回呼ぶこと」ではなく、「入力を組み、動作を実行し、結果を state に戻し、必要なら次ターンへ続けること」です。**
