# s00c: Query Transition Model

> この bridge doc は次の一点を解くためのものです。
>
> **高完成度の agent では、なぜ query が次の turn へ続くのかを明示しなければならないのか。**

## なぜこの資料が必要か

主線では次を順に学びます。

- `s01`: 最小 loop
- `s06`: context compact
- `s11`: error recovery

流れ自体は正しいです。

ただし、章ごとに別々に読むと多くの読者は次のように理解しがちです。

> 「とにかく `continue` したから次へ進む」

これは toy demo なら動きます。

しかし高完成度システムではすぐに破綻します。

なぜなら query が継続する理由は複数あり、それぞれ本質が違うからです。

- tool が終わり、その結果を model に戻す
- 出力が token 上限で切れて続きが必要
- compact 後に再試行する
- transport error の後で backoff して再試行する
- stop hook がまだ終わるなと指示する
- budget policy がまだ継続を許している

これら全部を曖昧な `continue` に潰すと、すぐに次が悪化します。

- log が読みにくくなる
- test が書きにくくなる
- 学習者の心智モデルが濁る

## まず用語

### transition とは

ここでの `transition` は:

> 前の turn が次の turn へ移った理由

を指します。

message 内容そのものではなく、制御上の原因です。

### continuation とは

continuation は:

> この query がまだ終わっておらず、先へ進むべき状態

のことです。

ただし continuation は一種類ではありません。

### query boundary とは

query boundary は turn と次の turn の境目です。

この境界を越えるたびに、システムは次を知っているべきです。

- なぜ続くのか
- 続く前にどの state を変えたのか
- 次の turn がその変更をどう解釈するのか

## 最小の心智モデル

query を一本の直線だと思わないでください。

より実像に近い理解は次です。

```text
1 本の query
  = 明示された continuation reason を持つ
    state transition の連鎖
```

例えば:

```text
user input
  ->
model emits tool_use
  ->
tool finishes
  ->
tool_result_continuation
  ->
model output is truncated
  ->
max_tokens_recovery
  ->
compact_retry
  ->
final completion
```

重要なのは:

> システムは while loop を漫然と回しているのではなく、
> 明示された transition reason の列で進んでいる

ということです。

## 主要 record

### 1. query state の `transition`

教材版でも次のような field は明示しておくべきです。

```python
state = {
    "messages": [...],
    "turn_count": 3,
    "continuation_count": 1,
    "has_attempted_compact": False,
    "transition": None,
}
```

この field は飾りではありません。

これによって:

- この turn がなぜ存在するか
- log がどう説明すべきか
- test がどの path を assert すべきか

が明確になります。

### 2. `TransitionReason`

教材版の最小集合は次の程度で十分です。

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "transport_retry",
    "stop_hook_continuation",
    "budget_continuation",
)
```

これらは同じではありません。

- `tool_result_continuation`
  は通常の主線継続
- `max_tokens_recovery`
  は切れた出力の回復継続
- `compact_retry`
  は context 再構成後の継続
- `transport_retry`
  は基盤失敗後の再試行継続
- `stop_hook_continuation`
  は外部制御による継続
- `budget_continuation`
  は budget policy による継続

### 3. continuation budget

高完成度システムは単に続行するだけではなく、続行回数を制御します。

```python
state = {
    "max_output_tokens_recovery_count": 2,
    "has_attempted_reactive_compact": True,
}
```

本質は:

> continuation は無限の抜け道ではなく、制御された資源

という点です。

## 最小実装の進め方

### Step 1: continue site を明示する

初心者の loop はよくこうなります。

```python
continue
```

教材版は一歩進めます。

```python
state["transition"] = "tool_result_continuation"
continue
```

### Step 2: continuation と state patch を対にする

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["turn_count"] += 1
    state["transition"] = "tool_result_continuation"
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({
        "role": "user",
        "content": CONTINUE_MESSAGE,
    })
    state["max_output_tokens_recovery_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

大事なのは「1 行増えた」ことではありません。

大事なのは:

> 続行する前に、理由と state mutation を必ず知っている

ことです。

### Step 3: 通常継続と recovery 継続を分ける

```python
if should_retry_transport(error):
    time.sleep(backoff(...))
    state["transition"] = "transport_retry"
    continue

if should_recompact(error):
    state["messages"] = compact_messages(state["messages"])
    state["transition"] = "compact_retry"
    continue
```

ここまで来ると `continue` は曖昧な動作ではなく、型付きの control transition になります。

## 何を test すべきか

教材 repo では少なくとも次を test しやすくしておくべきです。

- tool result が `tool_result_continuation` を書く
- truncated output が `max_tokens_recovery` を書く
- compact retry が古い reason を黙って使い回さない
- transport retry が通常 turn に見えない

これが test しづらいなら、まだ model が暗黙的すぎます。

## 何を教えすぎないか

vendor 固有の transport detail や細かすぎる enum を全部教える必要はありません。

教材 repo で本当に必要なのは次です。

> 1 本の query は明示された transition の連鎖であり、
> 各 transition は reason・state patch・budget rule を持つ

ここが分かれば、開発者は高完成度 agent を 0 から組み直せます。
