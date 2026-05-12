# s11: Error Recovery

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > [ s11 ] > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *error は例外イベントではなく、main loop が最初から用意しておくべき通常分岐です。*

## この章が解く問題

`s10` まで来ると agent はもう demo ではありません。

すでに system には、

- main loop
- tool use
- planning
- compaction
- permission
- hook
- memory
- prompt assembly

があります。

こうなると failure も自然に増えます。

- model output が途中で切れる
- context が大きすぎて request が入らない
- API timeout や rate limit で一時的に失敗する

もし recovery がなければ、main loop は最初の失敗で止まります。

そして初心者はよく、

> agent が不安定なのは model が弱いからだ

と誤解します。

しかし実際には多くの failure は、

**task そのものが失敗したのではなく、この turn の続け方を変える必要があるだけ**

です。

この章の目標は 1 つです。

**「error が出たら停止」から、「error の種類を見て recovery path を選ぶ」へ進むこと**

です。

## 併読すると楽になる資料

- 今の query がなぜまだ続いているのか見失ったら [`s00c-query-transition-model.md`](./s00c-query-transition-model.md)
- compact と recovery が同じ mechanism に見えたら [`s06-context-compact.md`](./s06-context-compact.md)
- このあと `s12` へ進む前に、recovery state と durable task state を混ぜたくなったら [`data-structures.md`](./data-structures.md)

## 先に言葉をそろえる

### recovery とは何か

recovery は「error をなかったことにする」ことではありません。

意味は次です。

- これは一時的 failure かを判定する
- 一時的なら有限回の補救動作を試す
- だめなら明示的に fail として返す

### retry budget とは何か

retry budget は、

> 最大で何回までこの recovery path を試すか

です。

例:

- continuation は最大 3 回
- transport retry は最大 3 回

これがないと loop が無限に回る危険があります。

### state machine とは何か

この章での state machine は難しい theory ではありません。

単に、

> normal execution と各 recovery branch を、明確な状態遷移として見ること

です。

この章から query の進行は次のように見えるようになります。

- normal
- continue after truncation
- compact then retry
- backoff then retry
- final fail

## 最小心智モデル

最初は 3 種類の failure だけ区別できれば十分です。

```text
1. output truncated
   model はまだ言い終わっていないが token が尽きた

2. context too large
   request 全体が model window に入らない

3. transient transport failure
   timeout / rate limit / temporary connection issue
```

それぞれに対応する recovery path はこうです。

```text
LLM call
  |
  +-- stop_reason == "max_tokens"
  |      -> continuation message を入れる
  |      -> retry
  |
  +-- prompt too long
  |      -> compact する
  |      -> retry
  |
  +-- timeout / rate limit / connection error
         -> 少し待つ
         -> retry
```

これが最小ですが、十分に正しい recovery model です。

## この章の核になるデータ構造

### 1. Recovery State

```python
recovery_state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

役割は 2 つあります。

- 各 recovery path ごとの retry 回数を分けて数える
- 無限 recovery を防ぐ

### 2. Recovery Decision

```python
{
    "kind": "continue" | "compact" | "backoff" | "fail",
    "reason": "why this branch was chosen",
}
```

ここで大事なのは、

**error の見た目と、次に選ぶ動作を分ける**

ことです。

この分離があると loop が読みやすくなります。

### 3. Continuation Message

```python
CONTINUE_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped. "
    "Do not restart or repeat."
)
```

この message は地味ですが非常に重要です。

なぜなら model は「続けて」とだけ言うと、

- 最初から言い直す
- もう一度要約し直す
- 直前の内容を繰り返す

ことがあるからです。

## 最小実装を段階で追う

### 第 1 段階: recovery chooser を作る

```python
def choose_recovery(stop_reason: str | None, error_text: str | None) -> dict:
    if stop_reason == "max_tokens":
        return {"kind": "continue", "reason": "output truncated"}

    if error_text and "prompt" in error_text and "long" in error_text:
        return {"kind": "compact", "reason": "context too large"}

    if error_text and any(word in error_text for word in [
        "timeout", "rate", "unavailable", "connection"
    ]):
        return {"kind": "backoff", "reason": "transient transport failure"}

    return {"kind": "fail", "reason": "unknown or non-recoverable error"}
```

この関数がやっている本質は、

**まず分類し、そのあと branch を返す**

という 1 点です。

### 第 2 段階: main loop に差し込む

```python
while True:
    try:
        response = client.messages.create(...)
        decision = choose_recovery(response.stop_reason, None)
    except Exception as e:
        response = None
        decision = choose_recovery(None, str(e).lower())

    if decision["kind"] == "continue":
        messages.append({"role": "user", "content": CONTINUE_MESSAGE})
        continue

    if decision["kind"] == "compact":
        messages = auto_compact(messages)
        continue

    if decision["kind"] == "backoff":
        time.sleep(backoff_delay(...))
        continue

    if decision["kind"] == "fail":
        break

    # normal tool handling
```

ここで一番大事なのは、

- catch したら即 stop

ではなく、

- 何の失敗かを見る
- どの recovery path を試すか決める

という構造です。

## 3 つの主 recovery path が埋めている穴

### 1. continuation

これは「model が言い終わる前に output budget が切れた」問題を埋めます。

本質は、

> task が失敗したのではなく、1 turn の出力空間が足りなかった

ということです。

最小形はこうです。

```python
if response.stop_reason == "max_tokens":
    if state["continuation_attempts"] >= 3:
        return "Error: output recovery exhausted"
    state["continuation_attempts"] += 1
    messages.append({"role": "user", "content": CONTINUE_MESSAGE})
    continue
```

### 2. compact

これは「task が無理」ではなく、

> active context が大きすぎて request が入らない

ときに使います。

ここで大事なのは、compact を delete と考えないことです。

compact は、

**過去を、そのままの原文ではなく、まだ続行可能な summary へ変換する**

操作です。

最小例:

```python
def auto_compact(messages: list) -> list:
    summary = summarize_messages(messages)
    return [{
        "role": "user",
        "content": "This session was compacted. Continue from this summary:\n" + summary,
    }]
```

最低限 summary に残したいのは次です。

- 今の task は何か
- 何をすでに終えたか
- 重要 decision は何か
- 次に何をするつもりか

### 3. backoff

これは timeout、rate limit、temporary connection issue のような

**時間を置けば通るかもしれない failure**

に対して使います。

考え方は単純です。

```python
if decision["kind"] == "backoff":
    if state["transport_attempts"] >= 3:
        break
    state["transport_attempts"] += 1
    time.sleep(backoff_delay(state["transport_attempts"]))
    continue
```

ここで大切なのは「retry すること」よりも、

**retry にも budget があり、同じ速度で無限に叩かないこと**

です。

## compact と recovery を混ぜない

これは初学者が特に混ぜやすい点です。

- `s06` の compact は context hygiene のために行うことがある
- `s11` の compact recovery は request failure から戻るために行う

同じ compact という操作でも、

**目的が違います。**

目的が違えば、それを呼ぶ branch も別に見るべきです。

## recovery は query の continuation 理由でもある

`s11` の重要な学びは、error handling を `except` の奥へ隠さないことです。

むしろ次を explicit に持つ方が良いです。

- なぜまだ続いているのか
- 何回その branch を試したのか
- 次にどの branch を試すのか

すると recovery は hidden plumbing ではなく、

**query transition を説明する状態**

になります。

## 初学者が混ぜやすいポイント

### 1. すべての failure に同じ retry をかける

truncation と transport error は同じ問題ではありません。

### 2. retry budget を持たない

無限 loop の原因になります。

### 3. compact と recovery を 1 つの話にしてしまう

context hygiene と failure recovery は目的が違います。

### 4. continuation message を曖昧にする

「続けて」だけでは model が restart / repeat しやすいです。

### 5. なぜ続行しているのかを state に残さない

debug も teaching も急に難しくなります。

## この章を読み終えたら何が言えるべきか

1. 多くの error は task failure ではなく、「この turn の続け方を変えるべき」信号である
2. recovery は `continue / compact / backoff / fail` の branch として考えられる
3. recovery path ごとに budget を持たないと loop が壊れやすい

## 一文で覚える

**Error Recovery とは、failure を見た瞬間に止まるのではなく、failure の種類に応じて continuation path を選び直す control layer です。**
