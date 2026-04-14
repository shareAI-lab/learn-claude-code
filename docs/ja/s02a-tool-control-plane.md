# s02a: Tool Control Plane

> これは `s02` を深く理解するための橋渡し文書です。  
> 問いたいのは:
>
> **なぜ tool system は単なる `tool_name -> handler` 表では足りないのか。**

## 先に結論

最小 demo では dispatch map だけでも動きます。

しかし高完成度の system では tool layer は次の責任をまとめて持ちます。

- tool schema をモデルへ見せる
- tool 名から実行先を解決する
- 実行前に permission を通す
- hook / classifier / side check を差し込む
- 実行中 progress を扱う
- 結果を整形して loop へ戻す
- 実行で変わる共有 state へアクセスする

つまり tool layer は:

**関数表ではなく、共有 execution plane**

です。

## 最小の心智モデル

```text
model emits tool_use
  |
  v
tool spec lookup
  |
  v
permission / hook / validation
  |
  v
actual execution
  |
  v
tool result shaping
  |
  v
write-back to loop
```

## `dispatch map` だけでは足りない理由

単なる map だと、せいぜい:

- この名前ならこの関数

しか表せません。

でも実システムで必要なのは:

- モデルへ何を見せるか
- 実行前に何を確認するか
- 実行中に何を表示するか
- 実行後にどんな result block を返すか
- どの shared context を触れるか

です。

## 主要なデータ構造

### `ToolSpec`

モデルに見せる tool の定義です。

```python
tool = {
    "name": "read_file",
    "description": "...",
    "input_schema": {...},
}
```

### `ToolDispatchMap`

名前から handler を引く表です。

```python
dispatch = {
    "read_file": run_read,
    "bash": run_bash,
}
```

これは必要ですが、これだけでは足りません。

### `ToolUseContext`

tool が共有状態へ触るための文脈です。

たとえば:

- app state getter / setter
- permission context
- notifications
- file-state cache
- current agent identity

などが入ります。

### `ToolResultEnvelope`

loop へ返すときの整形済み result です。

```python
{
    "type": "tool_result",
    "tool_use_id": "...",
    "content": "...",
}
```

高完成度版では content だけでなく:

- progress
- warnings
- structured result

なども関わります。

## 実行面として見ると何が変わるか

### 1. Tool は「名前」ではなく「実行契約」になる

1つの tool には:

- 入力 schema
- 実行権限
- 実行時 context
- 出力の形

がひとまとまりで存在します。

### 2. Permission と Hook の差が見えやすくなる

- permission: 実行してよいか
- hook: 実行の周辺で何を足すか

### 3. Native / Task / Agent / MCP を同じ平面で見やすくなる

参照実装でも重要なのは:

**能力の出どころが違っても、loop から見れば 1 つの tool execution plane に入る**

という点です。

## 初学者がやりがちな誤り

### 1. tool spec と handler を混同する

- spec はモデル向け説明
- handler は実行コード

### 2. permission を handler の中へ埋め込む

これをやると gate が共有層にならず、system が読みにくくなります。

### 3. result shaping を軽く見る

tool 実行結果は「文字列が返ればよい」ではありません。

loop が読み戻しやすい形に整える必要があります。

### 4. 実行状態を `messages[]` だけで持とうとする

tool 実行は app state や runtime state を触ることがあります。

## 一文で覚える

**tool system が本物らしくなるのは、名前から関数を呼べた瞬間ではなく、schema・gate・context・result を含む共有 execution plane として見えた瞬間です。**
