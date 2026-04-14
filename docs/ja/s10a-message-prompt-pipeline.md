# s10a: Message / Prompt 組み立てパイプライン

> これは `s10` を補う橋渡し文書です。  
> ここでの問いは:
>
> **モデルが実際に見る入力は、system prompt 1 本だけなのか。**

## 結論

違います。

高完成度の system では、モデル入力は複数 source の合成物です。

たとえば:

- stable system prompt blocks
- normalized messages
- memory section
- dynamic reminders
- tool instructions

つまり system prompt は大事ですが、**入力全体の一部**です。

## 最小の心智モデル

```text
stable rules
  +
tool surface
  +
memory / CLAUDE.md / skills
  +
normalized messages
  +
dynamic reminders
  =
final model input
```

## 主要な構造

### `PromptParts`

入力 source を組み立て前に分けて持つ構造です。

```python
parts = {
    "core": "...",
    "tools": "...",
    "memory": "...",
    "skills": "...",
    "dynamic": "...",
}
```

### `SystemPromptBlock`

1 本の巨大文字列ではなく、section 単位で扱うための単位です。

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

### `NormalizedMessage`

API に渡す前に整えられた messages です。

```python
{
    "role": "user",
    "content": [
        {"type": "text", "text": "..."}
    ],
}
```

## なぜ分ける必要があるか

### 1. 何が stable で何が dynamic かを分けるため

- system rules は比較的 stable
- current messages は dynamic
- reminders はより短命

### 2. どの source が何を足しているか追えるようにするため

source を混ぜて 1 本にすると:

- memory がどこから来たか
- skill がいつ入ったか
- reminder がなぜ入ったか

が見えにくくなります。

### 3. compact / recovery / retry の説明がしやすくなるため

入力 source が分かれていると:

- 何を再利用するか
- 何を要約するか
- 何を次ターンで作り直すか

が明確になります。

## 初学者が混ぜやすい境界

### `Message` と `PromptBlock`

- `Message`: 会話履歴
- `PromptBlock`: system 側の説明断片

### `Memory` と `Prompt`

- memory は内容 source
- prompt pipeline は source を組む仕組み

### `Tool instructions` と `Messages`

- tool instructions は model が使える surface の説明
- messages は今まで起きた対話 / 結果

## 一文で覚える

**system prompt は入力の全部ではなく、複数 source を束ねた pipeline の 1 つの section です。**
