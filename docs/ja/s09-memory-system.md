# s09: Memory System

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > [ s09 ] > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *memory は会話の全部を保存する場所ではない。次のセッションでも残すべき事実だけを小さく持つ場所である。*

## この章が解決する問題

memory がなければ、新しいセッションは毎回ゼロから始まります。

その結果、agent は何度も同じことを忘れます。

- ユーザーの好み
- すでに何度も訂正された注意点
- コードだけでは分かりにくいプロジェクト事情
- 外部参照の場所

そこで必要になるのが memory です。

## 最初に立てるべき境界

この章で最も大事なのは:

**何でも memory に入れない**

ことです。

memory に入れるべきなのは:

- セッションをまたいでも価値がある
- 現在のリポジトリを読み直すだけでは分かりにくい

こうした情報だけです。

## 主線とどう併読するか

- memory を「長い context の置き場」だと思ってしまうなら、[`s06-context-compact.md`](./s06-context-compact.md) に戻って compact と durable memory を分けます。
- `messages[]`、summary block、memory store が頭の中で混ざってきたら、[`data-structures.md`](./data-structures.md) を見ながら読みます。
- このあと `s10` へ進むなら、[`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) を横に置くと、memory が次の入力へどう戻るかをつかみやすくなります。

## 初学者向けの 4 分類

### 1. `user`

安定したユーザーの好み。

例:

- `pnpm` を好む
- 回答は短めがよい

### 2. `feedback`

ユーザーが明示的に直した点。

例:

- 生成ファイルは勝手に触らない
- テストの更新前に確認する

### 3. `project`

コードを見ただけでは分かりにくい持続的事情。

### 4. `reference`

外部資料や外部ボードへの参照先。

## 入れてはいけないもの

| 入れないもの | 理由 |
|---|---|
| ディレクトリ構造 | コードを読めば分かる |
| 関数名やシグネチャ | ソースが真実だから |
| 現在タスクの進捗 | task / plan の責務 |
| 一時的なブランチ名 | すぐ古くなる |
| 秘密情報 | 危険 |

## 最小の心智モデル

```text
conversation
   |
   | 長期的に残すべき事実が出る
   v
save_memory
   |
   v
.memory/
  ├── MEMORY.md
  ├── prefer_pnpm.md
  └── ask_before_codegen.md
   |
   v
次回セッション開始時に再読込
```

## 重要なデータ構造

### 1. 1 メモリ = 1 ファイル

```md
---
name: prefer_pnpm
description: User prefers pnpm over npm
type: user
---
The user explicitly prefers pnpm for package management commands.
```

### 2. 小さな索引

```md
# Memory Index

- prefer_pnpm [user]
- ask_before_codegen [feedback]
```

索引は内容そのものではなく、「何があるか」を素早く知るための地図です。

## 最小実装

```python
MEMORY_TYPES = ("user", "feedback", "project", "reference")
```

```python
def save_memory(name, description, mem_type, content):
    path = memory_dir / f"{slugify(name)}.md"
    path.write_text(render_frontmatter(name, description, mem_type) + content)
    rebuild_index()
```

次に、セッション開始時に読み込みます。

```python
memories = memory_store.load_all()
```

そして `s10` で prompt 組み立てに入れます。

## 近い概念との違い

### memory

次回以降も役立つ事実。

### task

いま何を完了したいか。

### plan

このターンでどう進めるか。

### `CLAUDE.md`

より安定した指示文書や standing rules。

## 初学者がよくやる間違い

### 1. コードを読めば分かることまで保存する

それは memory ではなく、重複です。

### 2. 現在の作業状況を memory に入れる

それは task / plan の責務です。

### 3. memory を絶対真実のように扱う

memory は古くなり得ます。

安全な原則は:

**memory は方向を与え、現在観測は真実を与える。**

## Try It

```sh
cd learn-claude-code
python agents/s09_memory_system.py
```
