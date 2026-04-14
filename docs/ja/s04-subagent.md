# s04: Subagents

`s00 > s01 > s02 > s03 > [ s04 ] > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *大きな仕事を全部 1 つの context に詰め込む必要はありません。*  
> subagent の価値は「model を 1 個増やすこと」ではなく、「clean な別 context を 1 つ持てること」にあります。

## この章が解く問題

agent がいろいろな調査や実装を進めると、親の `messages` はどんどん長くなります。

たとえば user の質問が単に

> 「この project は何の test framework を使っているの？」

だけでも、親 agent は答えるために、

- `pyproject.toml` を読む
- `requirements.txt` を読む
- `pytest` を検索する
- 実際に test command を走らせる

かもしれません。

でも本当に親に必要な最終答えは、

> 「主に `pytest` を使っています」

の一文だけかもしれません。

もしこの途中作業を全部親 context に積み続けると、あとで別の質問に答えるときに、

- さっきの局所調査の noise
- 大量の file read
- 一時的な bash 出力

が main context を汚染します。

subagent が解くのはこの問題です。

**局所 task を別 context に閉じ込め、親には必要な summary だけを持ち帰る**

のがこの章の主線です。

## 先に言葉をそろえる

### 親 agent とは何か

いま user と直接やり取りし、main `messages` を持っている actor が親 agent です。

### 子 agent とは何か

親が一時的に派生させ、特定の subtask だけを処理させる actor が子 agent、つまり subagent です。

### context isolation とは何か

これは単に、

- 親は親の `messages`
- 子は子の `messages`

を持ち、

> 子の途中経過が自動で親 history に混ざらないこと

を指します。

## 最小心智モデル

この章は次の図でほぼ言い切れます。

```text
Parent agent
  |
  | 1. 局所 task を外へ出すと決める
  v
Subagent
  |
  | 2. 自分の context で file read / search / tool execution
  v
Summary
  |
  | 3. 必要な結果だけを親へ返す
  v
Parent agent continues
```

ここで一番大事なのは次の 1 文です。

**subagent の価値は別 model instance ではなく、別 state boundary にある**

ということです。

## 最小実装を段階で追う

### 第 1 段階: 親に `task` tool を持たせる

親 agent は model が明示的に言える入口を持つ必要があります。

> この局所仕事は clean context に外注したい

その最小 schema は非常に簡単で構いません。

```python
{
    "name": "task",
    "description": "Run a subtask in a clean context and return a summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"}
        },
        "required": ["prompt"]
    }
}
```

### 第 2 段階: subagent は自分専用の `messages` で始める

subagent の本体はここです。

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    ...
```

親の `messages` をそのまま共有しないことが、最小の isolation です。

### 第 3 段階: 子に渡す tool は絞る

subagent は親と完全に同じ tool set を持つ必要はありません。

むしろ最初は絞った方がよいです。

たとえば、

- `read_file`
- 検索系 tool
- read-only 寄りの `bash`

だけを持たせ、

- さらに `task` 自体は子に渡さない

ようにすれば、無限再帰を避けやすくなります。

### 第 4 段階: 子は最後に summary だけ返す

一番大事なのはここです。

subagent は内部 history を親に全部戻しません。

戻すのは必要な summary だけです。

```python
return {
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": summary_text,
}
```

これにより親 context は、

- 必要な答え
- もしくは短い結論

だけを保持し、局所ノイズから守られます。

## この章の核になるデータ構造

この章で 1 つだけ覚えるなら、次の骨格です。

```python
class SubagentContext:
    messages: list
    tools: list
    handlers: dict
    max_turns: int
```

意味は次の通りです。

- `messages`: 子自身の context
- `tools`: 子が使える道具
- `handlers`: その tool が実際にどの code を呼ぶか
- `max_turns`: 子が無限に走り続けないための上限

つまり subagent は「関数呼び出し」ではなく、

**自分の state と tool boundary を持つ小さな agent**

です。

## なぜ本当に useful なのか

### 1. 親 context を軽く保てる

局所 task の途中経過が main conversation に積み上がりません。

### 2. subtask の prompt を鋭くできる

子に渡す prompt は次のように非常に集中できます。

- 「この directory の test framework を 1 文で答えて」
- 「この file の bug を探して原因だけ返して」
- 「3 file を読んで module 関係を summary して」

### 3. 後の multi-agent chapter の準備になる

subagent は long-lived teammate より前に学ぶべき最小の delegation model です。

まず「1 回限りの clean delegation」を理解してから、

- persistent teammate
- structured protocol
- autonomous claim

へ進むと心智がずっと滑らかになります。

## 0-to-1 の実装順序

### Version 1: blank-context subagent

最初はこれで十分です。

- `task` tool
- `run_subagent(prompt)`
- 子専用 `messages`
- 最後に summary を返す

### Version 2: tool set を制限する

親より小さく安全な tool set を渡します。

### Version 3: safety bound を足す

最低限、

- 最大 turn 数
- tool failure 時の終了条件

は入れてください。

### Version 4: fork を検討する

この順番を守ることが大事です。

最初から fork を入れる必要はありません。

## fork とは何か、なぜ「次の段階」なのか

最小 subagent は blank context から始めます。

でも subtask によっては、親が直前まで話していた内容を知らないと困ることがあります。

たとえば、

> 「さっき決めた方針に沿って、この module へ test を追加して」

のような場面です。

そのとき使うのが `fork` です。

```python
sub_messages = list(parent_messages)
sub_messages.append({"role": "user", "content": prompt})
```

fork の本質は、

**空白から始めるのではなく、親の既存 context を引き継いで子を始めること**

です。

ただし teaching order としては、blank-context subagent を理解してからの方が安全です。

先に fork を入れると、初心者は

- 何が isolation で
- 何が inherited context なのか

を混ぜやすくなります。

## 初学者が混ぜやすいポイント

### 1. subagent を「並列アピール機能」だと思う

subagent の第一目的は concurrency 自慢ではなく、context hygiene です。

### 2. 子の history を全部親へ戻してしまう

それでは isolation の価値がほとんど消えます。

### 3. 最初から役割を増やしすぎる

explorer、reviewer、planner、tester などを一気に作る前に、

**clean context の一回限り worker**

を正しく作る方が先です。

### 4. 子に `task` を持たせて無限に spawn させる

境界がないと recursion で system が荒れます。

### 5. `max_turns` のような safety bound を持たない

局所 task だからこそ、終わらない子を放置しない設計が必要です。

## この章を読み終えたら何が言えるべきか

1. subagent の価値は clean context を作ることにある
2. 子は親と別の `messages` を持つべきである
3. 親へ戻すのは内部 history 全量ではなく summary でよい

## 一文で覚える

**Subagent とは、局所 task を clean context へ切り出し、親には必要な結論だけを持ち帰るための最小 delegation mechanism です。**
