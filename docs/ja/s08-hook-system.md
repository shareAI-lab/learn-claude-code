# s08: Hook System

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > [ s08 ] > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *ループそのものを書き換えなくても、ライフサイクルの周囲に拡張点を置ける。*

## この章が解決する問題

`s07` までで、agent はかなり実用的になりました。

しかし実際には、ループの外側で足したい振る舞いが増えていきます。

- 監査ログ
- 実行追跡
- 通知
- 追加の安全チェック
- 実行前後の補助メッセージ

こうした周辺機能を毎回メインループに直接書き込むと、すぐに主線が読みにくくなります。

そこで必要なのが Hook です。

## 主線とどう併読するか

- Hook を「主ループの中へ if/else を足すこと」だと思い始めたら、まず [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) に戻ります。
- 主ループ、tool handler、hook の副作用が同じ層に見えてきたら、[`entity-map.md`](./entity-map.md) で「主状態を進めるもの」と「横から観測するもの」を分けます。
- この先で prompt、recovery、teams まで読むつもりなら、[`s00e-reference-module-map.md`](./s00e-reference-module-map.md) を近くに置いておくと、「control plane + sidecar 拡張」が何度も出てきても崩れにくくなります。

## Hook を最も簡単に言うと

Hook は:

**主ループの決まった節目で、追加動作を差し込む拡張点**

です。

ここで大切なのは、Hook が主ループの代わりになるわけではないことです。  
主ループは引き続き:

- モデル呼び出し
- ツール実行
- 結果の追記

を担当します。

## 最小の心智モデル

```text
tool_call from model
     |
     v
[PreToolUse hooks]
     |
     v
[execute tool]
     |
     v
[PostToolUse hooks]
     |
     v
append result and continue
```

この形なら、ループの主線を壊さずに拡張できます。

## まず教えるべき 3 つのイベント

| イベント | いつ発火するか | 主な用途 |
|---|---|---|
| `SessionStart` | セッション開始時 | 初期通知、ウォームアップ |
| `PreToolUse` | ツール実行前 | 監査、ブロック、補助判断 |
| `PostToolUse` | ツール実行後 | 結果記録、通知、追跡 |

これだけで教学版としては十分です。

## 重要な境界

### Hook は主状態遷移を置き換えない

Hook がやるのは「観察して補助すること」です。

メッセージ履歴、停止条件、ツール呼び出しの主責任は、あくまでメインループに残します。

### Hook には整ったイベント情報を渡す

理想的には、各 Hook は同じ形の情報を受け取ります。

たとえば:

- `event`
- `tool_name`
- `tool_input`
- `tool_output`
- `error`

この形が揃っていると、Hook を増やしても心智が崩れません。

## 最小実装

### 1. 設定を読む

```python
hooks = {
    "PreToolUse": [...],
    "PostToolUse": [...],
    "SessionStart": [...],
}
```

### 2. 実行関数を作る

```python
def run_hooks(event_name: str, ctx: dict):
    for hook in hooks.get(event_name, []):
        run_one_hook(hook, ctx)
```

### 3. ループに接続する

```python
run_hooks("PreToolUse", ctx)
output = handler(**tool_input)
run_hooks("PostToolUse", ctx)
```

## 初学者が混乱しやすい点

### 1. Hook を第二の主ループのように考える

そうすると制御が分裂して、一気に分かりにくくなります。

### 2. Hook ごとに別のデータ形を渡す

新しい Hook を足すたびに、読む側の心智コストが増えてしまいます。

### 3. 何でも Hook に入れようとする

Hook は便利ですが、メインの状態遷移まで押し込む場所ではありません。

## Try It

```sh
cd learn-claude-code
python agents/s08_hook_system.py
```

見るポイント:

1. どのイベントで Hook が走るか
2. Hook が主ループを壊さずに追加動作だけを行っているか
3. イベント情報の形が揃っているか
