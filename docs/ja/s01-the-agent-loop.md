# s01: The Agent Loop

`s00 > [ s01 ] > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *loop がなければ agent は生まれません。*  
> この章では、最小だけれど正しい loop を先に作り、そのあとで「なぜ後ろの章で control plane が必要になるのか」を理解できる土台を作ります。

## この章が解く問題

言語 model 自体は「次にどんな文字列を出すか」を予測する存在です。

それだけでは自分で次のことはできません。

- file を開く
- command を実行する
- error を観察する
- その観察結果を次の判断へつなぐ

もし system 側に次の流れを繰り返す code がなければ、

```text
model に聞く
  ->
tool を使いたいと言う
  ->
本当に実行する
  ->
結果を model へ戻す
  ->
次の一手を考えさせる
```

model は「会話できる program」に留まり、「仕事を進める agent」にはなりません。

だからこの章の目標は 1 つです。

**model と tool を閉ループに接続し、仕事を継続的に前へ進める最小 agent を作ること**

です。

## 先に言葉をそろえる

### loop とは何か

ここでの `loop` は「無意味な無限ループ」ではありません。

意味は、

> 仕事がまだ終わっていない限り、同じ処理手順を繰り返す主循環

です。

### turn とは何か

`turn` は 1 ラウンドです。

最小版では 1 turn にだいたい次が入ります。

1. 現在の messages を model に送る
2. model response を受け取る
3. tool_use があれば tool を実行する
4. tool_result を messages に戻す

そのあとで次の turn へ進むか、終了するかが決まります。

### tool_result とは何か

`tool_result` は terminal 上の一時ログではありません。

正しくは、

> model が次の turn で読めるよう、message history へ書き戻される結果 block

です。

### state とは何か

`state` は、その loop が前へ進むために持ち続ける情報です。

この章の最小 state は次です。

- `messages`
- `turn_count`
- 次 turn に続く理由

## 最小心智モデル

まず agent 全体を次の回路として見てください。

```text
user message
   |
   v
LLM
   |
   +-- 普通の返答 ----------> 終了
   |
   +-- tool_use ----------> tool 実行
                              |
                              v
                         tool_result
                              |
                              v
                         messages へ write-back
                              |
                              v
                         次の turn
```

この図の中で一番重要なのは `while True` という文法ではありません。

最も重要なのは次の 1 文です。

**tool の結果は message history に戻され、次の推論入力になる**

ここが欠けると、model は現実の観察を踏まえて次の一手を考えられません。

## この章の核になるデータ構造

### 1. Message

最小教材版では、message はまず次の形で十分です。

```python
{"role": "user", "content": "..."}
{"role": "assistant", "content": [...]}
```

ここで忘れてはいけないのは、

**message history は UI 表示用の chat transcript ではなく、次 turn の作業 context**

だということです。

### 2. Tool Result Block

tool 実行後は、その出力を対応する block として messages へ戻します。

```python
{
    "type": "tool_result",
    "tool_use_id": "...",
    "content": "...",
}
```

`tool_use_id` は単純に、

> どの tool 呼び出しに対応する結果か

を model に示すための ID です。

### 3. LoopState

この章では散らばった local variable だけで済ませるより、

> loop が持つ state を 1 か所へ寄せて見る

癖を作る方が後で効きます。

最小形は次で十分です。

```python
state = {
    "messages": [...],
    "turn_count": 1,
    "transition_reason": None,
}
```

ここでの `transition_reason` はまず、

> なぜこの turn のあとにさらに続くのか

を示す field とだけ理解してください。

この章の最小版では、理由は 1 種類でも十分です。

```python
"tool_result"
```

つまり、

> tool を実行したので、その結果を踏まえてもう一度 model を呼ぶ

という continuation です。

## 最小実装を段階で追う

### 第 1 段階: 初期 message を作る

まず user request を history に入れます。

```python
messages = [{"role": "user", "content": query}]
```

### 第 2 段階: model を呼ぶ

messages、system prompt、tools をまとめて model に送ります。

```python
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)
```

### 第 3 段階: assistant response 自体も history へ戻す

```python
messages.append({
    "role": "assistant",
    "content": response.content,
})
```

ここは初心者がとても落としやすい点です。

「最終答えだけ取れればいい」と思って assistant response を保存しないと、次 turn の context が切れます。

### 第 4 段階: tool_use があればจริง行する

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

この段階で初めて、model の意図が real execution へ落ちます。

### 第 5 段階: tool_result を user-side message として write-back する

```python
messages.append({
    "role": "user",
    "content": results,
})
```

これで次 turn の model は、

- さっき自分が何を要求したか
- その結果が何だったか

を両方読めます。

### 全体を 1 つの loop にまとめる

```python
def agent_loop(state):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=state["messages"],
            tools=TOOLS,
            max_tokens=8000,
        )

        state["messages"].append({
            "role": "assistant",
            "content": response.content,
        })

        if response.stop_reason != "tool_use":
            state["transition_reason"] = None
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        state["messages"].append({
            "role": "user",
            "content": results,
        })
        state["turn_count"] += 1
        state["transition_reason"] = "tool_result"
```

これがこの course 全体の核です。

後ろの章で何が増えても、

**model を呼び、tool を実行し、result を戻して、必要なら続く**

という骨格自体は残ります。

## この章でわざと単純化していること

この章では最初から複雑な control plane を教えません。

まだ出していないもの:

- permission gate
- hook
- memory
- prompt assembly pipeline
- recovery branch
- compact 後の continuation

なぜなら初学者が最初に理解すべきなのは、

**agent の最小閉ループ**

だからです。

もし最初から複数の continuation reason や recovery branch を混ぜると、
読者は「loop そのもの」が見えなくなります。

## 高完成度 system ではどう広がるか

教材版は最も重要な骨格だけを教えます。

高完成度 system では、その同じ loop の外側に次の層が足されます。

| 観点 | この章の最小版 | 高完成度 system |
|---|---|---|
| loop 形状 | 単純な `while True` | event-driven / streaming continuation |
| 継続理由 | `tool_result` が中心 | retry、compact resume、recovery など複数 |
| tool execution | response 全体を見てから実行 | 並列実行や先行起動を含む runtime |
| state | `messages` 中心 | turn、budget、transition、recovery を explicit に持つ |
| error handling | ほぼなし | truncation、transport error、retry branch |
| observability | 最小 | progress event、structured logs、UI stream |

ここで覚えるべき本質は細かな branch 名ではありません。

本質は次の 1 文です。

**agent は最後まで「結果を model に戻し続ける loop」であり、周囲に state 管理と continuation の理由が増えていく**

ということです。

## この章を読み終えたら何が言えるべきか

1. model だけでは agent にならず、tool result を戻す loop が必要
2. assistant response 自体も history に残さないと次 turn が切れる
3. tool_result は terminal log ではなく、次 turn の input block である

## 一文で覚える

**agent loop とは、model の要求を現実の観察へ変え、その観察をまた model に返し続ける主循環です。**
