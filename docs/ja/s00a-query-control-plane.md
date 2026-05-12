# s00a: Query Control Plane

> これは主線章ではなく橋渡し文書です。  
> ここで答えたいのは次の問いです。
>
> **なぜ高完成度の agent は `messages[]` と `while True` だけでは足りないのか。**

## なぜこの文書が必要か

`s01` では最小の loop を学びます。

```text
ユーザー入力
  ->
モデル応答
  ->
tool_use があれば実行
  ->
tool_result を戻す
  ->
次ターン
```

これは正しい出発点です。

ただし実システムが成長すると、支えるのは loop 本体だけではなく:

- 今どの turn か
- なぜ続行したのか
- compact を試したか
- token recovery 中か
- hook が終了条件に影響しているか

といった **query 制御状態** です。

この層を明示しないと、動く demo は作れても、高完成度 harness へ育てにくくなります。

## まず用語を分ける

### Query

ここでの `query` は database query ではありません。

意味は:

> 1つのユーザー要求を完了するまで続く、多ターンの処理全体

です。

### Control Plane

`control plane` は:

> 実際の業務動作をする層ではなく、流れをどう進めるかを管理する層

です。

ここでは:

- model 応答や tool result は内容
- 「次に続けるか」「なぜ続けるか」は control plane

と考えると分かりやすいです。

### Transition Reason

`transition reason` は:

> 前のターンが終わらず、次ターンへ進んだ理由

です。

たとえば:

- tool が終わった
- 出力が切れて続きを書く必要がある
- compact 後に再実行する
- hook が続行を要求した

などがあります。

## 最小の心智モデル

```text
1. 入力層
   - messages
   - system prompt
   - runtime context

2. 制御層
   - query state
   - turn count
   - transition reason
   - compact / recovery flags

3. 実行層
   - model call
   - tool execution
   - write-back
```

この層は loop を置き換えるためではありません。

**小さな loop を、分岐と状態を扱える system に育てるため**にあります。

## なぜ `messages[]` だけでは足りないか

最小 demo では、多くのことを `messages[]` に押し込めても動きます。

しかし次の情報は会話内容ではなく制御状態です。

- reactive compact を既に試したか
- 出力続行を何回したか
- 今回の続行が tool によるものか recovery によるものか
- 今だけ output budget を変えているか

これらを全部 `messages[]` に混ぜると、状態の境界が崩れます。

## 主要なデータ構造

### `QueryParams`

query に入るときの外部入力です。

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

これは「入口で既に分かっているもの」です。

### `QueryState`

query の途中で変わり続ける制御状態です。

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "turn_count": 1,
    "continuation_count": 0,
    "has_attempted_compact": False,
    "max_output_tokens_override": None,
    "stop_hook_active": False,
    "transition": None,
}
```

重要なのは:

- 内容状態と制御状態を分ける
- どの continue site も同じ state を更新する

ことです。

### `TransitionReason`

続行理由は文字列でも enum でもよいですが、明示する方がよいです。

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "stop_hook_continuation",
)
```

これで:

- log
- test
- debug
- 教材説明

がずっと分かりやすくなります。

## 最小実装の流れ

### 1. 外部入力と内部状態を分ける

```python
def query(params):
    state = {
        "messages": params["messages"],
        "tool_use_context": params["tool_use_context"],
        "turn_count": 1,
        "continuation_count": 0,
        "has_attempted_compact": False,
        "transition": None,
    }
```

### 2. 各ターンで state を読んで実行する

```python
while True:
    response = call_model(...)
```

### 3. 続行時は必ず state に理由を書き戻す

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["transition"] = "tool_result_continuation"
    state["turn_count"] += 1
    continue
```

大事なのは:

**ただ `continue` するのではなく、なぜ `continue` したかを状態に残すこと**

です。

## 初学者が混ぜやすいもの

### 1. 会話内容と制御状態

- `messages` は内容
- `turn_count` や `transition` は制御

### 2. Loop と Control Plane

- loop は反復の骨格
- control plane はその反復を管理する層

### 3. Prompt assembly と query state

- prompt assembly は「このターンに model へ何を渡すか」
- query state は「この query が今どういう状態か」

## 一文で覚える

**高完成度の agent では、会話内容を持つ層と、続行理由を持つ層を分けた瞬間に system の見通しが良くなります。**
