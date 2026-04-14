# s10: System Prompt

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > [ s10 ] > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *system prompt は巨大な固定文字列ではなく、複数ソースから組み立てるパイプラインである。*

## なぜこの章が必要か

最初は 1 本の system prompt 文字列でも動きます。

しかし機能が増えると、入力の材料が増えます。

- 安定した役割説明
- ツール一覧
- skills
- memory
- `CLAUDE.md`
- 現在ディレクトリや日時のような動的状態

こうなると、1 本の固定文字列では心智が崩れます。

## 主線とどう併読するか

- prompt をまだ「大きな謎の文字列」として見てしまうなら、[`s00a-query-control-plane.md`](./s00a-query-control-plane.md) に戻って、モデル入力がどの control 層を通るかを見直します。
- どの順で何を組み立てるかを安定させたいなら、[`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) をこの章の橋渡し資料として併読します。
- system rules、tool docs、memory、runtime state が 1 つの入力塊に見えてきたら、[`data-structures.md`](./data-structures.md) で入力片の出所を分け直します。

## 最小の心智モデル

```text
1. core identity
2. tools
3. skills
4. memory
5. CLAUDE.md chain
6. dynamic runtime context
```

最後に順に連結します。

```text
core
+ tools
+ skills
+ memory
+ claude_md
+ dynamic_context
= final model input
```

## 最も重要な境界

分けるべきなのは:

- 安定したルール
- 毎ターン変わる補足情報

安定したもの:

- 役割
- 安全ルール
- ツール契約
- 長期指示

動的なもの:

- 現在日時
- cwd
- 現在モード
- このターンだけの注意

## 最小 builder

```python
class SystemPromptBuilder:
    def build(self) -> str:
        parts = []
        parts.append(self._build_core())
        parts.append(self._build_tools())
        parts.append(self._build_skills())
        parts.append(self._build_memory())
        parts.append(self._build_claude_md())
        parts.append(self._build_dynamic())
        return "\n\n".join(p for p in parts if p)
```

ここで重要なのは、各メソッドが 1 つの責務だけを持つことです。

## 1 本の大文字列より良い理由

### 1. どこから来た情報か分かる

### 2. 部分ごとにテストしやすい

### 3. 安定部分と動的部分を分けて育てられる

## `system prompt` と `system reminder`

より分かりやすい考え方は:

- `system prompt`: 安定した土台
- `system reminder`: このターンだけの追加注意

こうすると、長期ルールと一時的ノイズが混ざりにくくなります。

## `CLAUDE.md` が独立した段なのはなぜか

`CLAUDE.md` は memory でも skill でもありません。

より安定した指示文書の層です。

教学版では、次のように積み上げると理解しやすいです。

1. ユーザー級
2. プロジェクト根
3. サブディレクトリ級

重要なのは:

**指示源は上書き一発ではなく、層として積める**

ということです。

## memory とこの章の関係

memory は保存するだけでは意味がありません。

モデル入力に再び入って初めて、agent の行動に効いてきます。

だから:

- `s09` で記憶する
- `s10` で入力に組み込む

という流れになります。

## 初学者が混乱しやすい点

### 1. system prompt を固定文字列だと思う

### 2. 毎回変わる情報も全部同じ塊に入れる

### 3. skills、memory、`CLAUDE.md` を同じものとして扱う

似て見えても責務は違います。

- `skills`: 任意の能力パッケージ
- `memory`: セッションをまたぐ事実
- `CLAUDE.md`: 立ち続ける指示文書

## Try It

```sh
cd learn-claude-code
python agents/s10_system_prompt.py
```
