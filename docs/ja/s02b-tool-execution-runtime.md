# s02b: Tool Execution Runtime

> この bridge doc は tool の登録方法ではなく、次の問いを扱います。
>
> **model が複数の tool call を出したとき、何を基準に並列化し、進捗を出し、結果順を安定させ、context をマージするのか。**

## なぜこの資料が必要か

`s02` では正しく次を教えています。

- tool schema
- dispatch map
- `tool_result` の main loop への回流

出発点としては十分です。

ただしシステムが大きくなると、本当に難しくなるのはもっと深い層です。

- どの tool は並列実行できるか
- どの tool は直列でなければならないか
- 遅い tool は途中 progress を出すべきか
- 並列結果を完了順で返すのか、元の順序で返すのか
- tool 実行が共有 context を変更するのか
- 並列変更をどう安全にマージするのか

これらはもはや「登録」の話ではありません。

それは:

**tool execution runtime**

の話です。

## まず用語

### tool execution runtime とは

ここでの runtime は言語 runtime の意味ではありません。

ここでは:

> tool call が実際に動き始めた後、システムがそれらをどう調度し、追跡し、回写するか

という実行規則のことです。

### concurrency safe とは

concurrency safe とは:

> 同種の仕事と同時に走っても共有 state を壊しにくい

という意味です。

よくある read-only tool は安全なことが多いです。

- `read_file`
- いくつかの search tool
- 読み取り専用の MCP tool

一方で write 系は安全でないことが多いです。

- `write_file`
- `edit_file`
- 共有 app state を変える tool

### progress message とは

progress message とは:

> tool はまだ終わっていないが、「今何をしているか」を先に上流へ見せる更新

のことです。

### context modifier とは

ある tool は text result だけでなく共有 runtime context も変更します。

例えば:

- notification queue を更新する
- 実行中 tool の状態を更新する
- app state を変更する

この共有 state 変更を context modifier と考えられます。

## 最小の心智モデル

tool 実行を次のように平坦化しないでください。

```text
tool_use -> handler -> result
```

より実像に近い理解は次です。

```text
tool_use blocks
  ->
concurrency safety で partition
  ->
並列 lane か直列 lane を選ぶ
  ->
必要なら progress を吐く
  ->
安定順で結果を回写する
  ->
queued context modifiers をマージする
```

ここで大事なのは二つです。

- 並列化は「全部まとめて走らせる」ではない
- 共有 context は完了順で勝手に書き換えない

## 主要 record

### 1. `ToolExecutionBatch`

教材版なら次の程度の batch 概念で十分です。

```python
batch = {
    "is_concurrency_safe": True,
    "blocks": [tool_use_1, tool_use_2, tool_use_3],
}
```

意味は単純です。

- tool を常に 1 個ずつ扱うわけではない
- runtime はまず execution batch に分ける

### 2. `TrackedTool`

完成度を上げたいなら各 tool を明示的に追跡します。

```python
tracked_tool = {
    "id": "toolu_01",
    "name": "read_file",
    "status": "queued",   # queued / executing / completed / yielded
    "is_concurrency_safe": True,
    "pending_progress": [],
    "results": [],
    "context_modifiers": [],
}
```

これにより runtime は次に答えられます。

- 何が待機中か
- 何が実行中か
- 何が完了したか
- 何がすでに progress を出したか

### 3. `MessageUpdate`

tool 実行は最終結果 1 個だけを返すとは限りません。

最小理解は次で十分です。

```python
update = {
    "message": maybe_message,
    "new_context": current_context,
}
```

高完成度 runtime では、更新は通常二つに分かれます。

- すぐ上流へ見せる message update
- 後で merge すべき内部 context update

### 4. queued context modifiers

これは見落とされやすいですが、とても重要です。

並列 batch で安全なのは:

> 先に終わった tool がその順で共有 context を先に変える

ことではありません。

より安全なのは:

> context modifier を一旦 queue し、最後に元の tool 順序で merge する

ことです。

```python
queued_context_modifiers = {
    "toolu_01": [modify_ctx_a],
    "toolu_02": [modify_ctx_b],
}
```

## 最小実装の進め方

### Step 1: concurrency safety を判定する

```python
def is_concurrency_safe(tool_name: str, tool_input: dict) -> bool:
    return tool_name in {"read_file", "search_files"}
```

### Step 2: 実行前に partition する

```python
batches = partition_tool_calls(tool_uses)

for batch in batches:
    if batch["is_concurrency_safe"]:
        run_concurrently(batch["blocks"])
    else:
        run_serially(batch["blocks"])
```

### Step 3: 並列 lane では progress を先に出せるようにする

```python
for update in run_concurrently(...):
    if update.get("message"):
        yield update["message"]
```

### Step 4: context merge は安定順で行う

```python
queued_modifiers = {}

for update in concurrent_updates:
    if update.get("context_modifier"):
        queued_modifiers[update["tool_id"]].append(update["context_modifier"])

for tool in original_batch_order:
    for modifier in queued_modifiers.get(tool["id"], []):
        context = modifier(context)
```

ここは教材 repo でも簡略化しすぎず、しかし主線を崩さずに教えられる重要点です。

## 開発者が持つべき図

```text
tool_use blocks
  |
  v
partition by concurrency safety
  |
  +-- safe batch ----------> concurrent execution
  |                            |
  |                            +-- progress updates
  |                            +-- final results
  |                            +-- queued context modifiers
  |
  +-- exclusive batch -----> serial execution
                               |
                               +-- direct result
                               +-- direct context update
```

## なぜ後半では dispatch map より重要になるのか

小さい demo では:

```python
handlers[tool_name](tool_input)
```

で十分です。

しかし高完成度 agent で本当に難しいのは、正しい handler を呼ぶことそのものではありません。

難しいのは:

- 複数 tool を安全に調度する
- progress を見えるようにする
- 結果順を安定させる
- 共有 context を非決定的にしない

だからこそ tool execution runtime は独立した bridge doc として教える価値があります。
