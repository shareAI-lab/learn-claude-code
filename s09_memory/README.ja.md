# s09: Memory — 重要な情報をセッションを越えて残す

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s07 → s08 → `s09` → [s10](../s10_task_system/) → s11 → ... → s16 → s17
> *「後のタスクでも使う情報を残す。」* ファイル保存 + index + 関連性の選択 + 必要時の recall。
>
> **Harness レイヤー**：Memory は会話の外に再利用できる知識を保存し、関係するタスクで取り出す。

---

## 問題

Agent が新しい session を始めると、`messages` に前回の会話はない。以前に伝えられた coding preference、project の背景、調査の手がかりは、次のタスクでも必要になることがある。永続的な保存先がなければ、ユーザーは同じ情報をもう一度伝えなければならない。

完全な transcript は記録には向いているが、毎回モデルへ送る方法は長続きしない。会話は増え続け、必要な情報を見つけにくくなり、古い事実が現在も正しいとは限らない。Memory が判断するのは、どの情報を session を越えて保存するか、現在のタスクでどの記録を取り出すかだ。

![Memory Overview](images/memory-overview.ja.svg)

---

## すべて system prompt に入れる方法が適さない理由

最も直接的な方法は、ユーザーの好みや project の事実を一つのファイルへ書き、起動時に全文を system prompt へ入れることだ。情報は残るが、LLM を呼ぶたびに全量を送り直す必要がある。記憶が増えるほど、現在のタスクと関係ない内容が input token と context を占有する。

s07 は別の読み方を示した。短い index を置き、必要なときだけ本文を読む。Skill は人が書く read-only の知識であり、Memory は Agent が会話から情報を抽出し、後のタスクで再利用できるようにする。

この章で扱うのは、保存、recall、抽出、整理の四つだ。

![Memory Subsystems](images/memory-subsystems.ja.svg)

---

## 保存：一つの記憶を一つのファイルへ

各 memory は `.memory/` の Markdown ファイルで、YAML frontmatter に `name`、`description`、`type` を持つ。

```markdown
---
name: user-preference-tabs
description: User prefers tabs for indentation
type: user
---

User prefers using tabs, not spaces, for indentation.
```

memory type は四種類ある。

| type | 保存する内容 | 例 |
|------|-------------|----|
| user | 長く使うユーザーの好み | 「indent には tab を使う」 |
| feedback | 今後も使える作業上の feedback | 「database を mock しない」 |
| project | 安定した project の事実 | 「認証の書き直しは compliance 要件による」 |
| reference | 外部資料や検索の手がかり | 「pipeline の問題は Linear INGEST にある」 |

`MEMORY.md` は index で、一行が一つの memory ファイルに対応する。書き込み後、`rebuild_memory_index()` がファイルから index を作り直す。

```python
def write_memory_file(name, mem_type, description, body):
    path = MEMORY_DIR / f"{memory_slug(name)}.md"
    path.write_text(
        memory_document(name, mem_type, description, body), encoding="utf-8"
    )
    rebuild_memory_index()
    return path
```

index は関連する記憶を選ぶために使い、本文は個別ファイルに残す。

---

## Recall：先に選び、その後で本文を読む

ユーザーの request が始まると、`select_relevant_memories()` は最近のユーザー発言と memory catalog を軽量なモデル呼び出しへ渡し、関係する記録を最大五件選ぶ。

```python
prompt = (
    "Select memory records that are relevant to the current user request. "
    "Return only a JSON array of catalog indices, such as [0, 2]. "
    "Return [] when none are relevant."
)
```

モデル呼び出しまたは JSON parse に失敗したら、keyword matching へ fallback する。選択後にだけ `load_memories()` が対応するファイルを読み、recall する本文の合計長も制限する。

```python
relevant_memories = load_memories(messages)
system = build_system(relevant_memories)
```

`build_system()` は、recall した内容が背景知識であり、新しいユーザー command ではないことを明示する。memory と現在の request が矛盾した場合は現在の request を優先する。これにより古い情報は利用できるが、古い記録がユーザーの代わりに命令することはない。

---

## 抽出：turn の終了後に再利用できる情報を保存する

ユーザーが毎回「覚えて」と言うとは限らない。Agent が現在の返答を終えた後、`extract_memories()` は会話を確認し、今後も役立つ可能性がある情報だけを取り出す。

```python
tool_calls = [
    block for block in response.content if block.type == "tool_use"
]
if not tool_calls:
    force = trigger_hooks("Stop", messages)
    if force:
        messages.append({"role": "user", "content": force})
        continue
    if extract_memories(messages):
        consolidate_memories()
    return
```

モデルの返答は候補であり、そのまま disk へ書く記録ではない。各候補には `scope` があり、`persistent` だけが後の session に残す内容を表す。`current_task` は一回だけの command、一時 path、現在のタスクだけの制約に使う。

最後の判定は `should_store_memory()` が行う。field が足りない候補、「この session」「現在の task」のような一時性を含む候補、既存 memory と重複する候補は拒否する。例えば「この session ではファイルを作らない」は現在の作業だけの制約であり、次の session まで有効にしてはいけない。

---

## 整理：重複した内容と古い内容をまとめる

memory ファイルが増えると、重複、矛盾、古い情報が混ざる。学習用実装は 10 件に達すると `consolidate_memories()` を呼び、整理後の記録一覧をモデルに生成させる。

新しい一覧を parse して検証してから旧ファイルを置き換える。置き換え前には現在の記録を snapshot し、削除や書き込みに失敗したら元のファイルを戻して index を再構築する。

```python
snapshot = {
    path.name: path.read_text(encoding="utf-8")
    for path in MEMORY_DIR.glob("*.md")
    if path.name != MEMORY_INDEX.name
}

try:
    for path in MEMORY_DIR.glob("*.md"):
        if path.name != MEMORY_INDEX.name:
            path.unlink()
    for record in consolidated:
        path = MEMORY_DIR / f"{memory_slug(record['name'])}.md"
        path.write_text(memory_document(
            record["name"], record["type"],
            record["description"], record["body"],
        ), encoding="utf-8")
    rebuild_memory_index()
except Exception:
    for path in MEMORY_DIR.glob("*.md"):
        if path.name != MEMORY_INDEX.name:
            path.unlink()
    for filename, content in snapshot.items():
        (MEMORY_DIR / filename).write_text(content, encoding="utf-8")
    rebuild_memory_index()
    raise
```

学習用コードでは件数だけを threshold にする。実際の application では data 量に合う実行時期を選び、複数 process が同じ store を同時に書き換えないようにする必要がある。

---

## この章のコード

| 部分 | 実装 |
|------|------|
| Agent Loop | messages、tool call、tool result、hook の trigger point を維持 |
| 基本 tools | `bash`、`read_file`、`write_file`、`edit_file`、`glob` |
| 保存 | `.memory/MEMORY.md` index + `.memory/*.md` records |
| Recall | catalog の選択 + keyword fallback + 本文サイズ上限 |
| 書き込み | turn 終了後の抽出 + 永続性チェック + 重複除外 |
| 整理 | threshold 到達後に統合し、置き換え失敗時は旧ファイルを復元 |

> **s08 との境界：** s08 は現在の session の context budget を管理し、s09 は会話の外にある再利用可能な知識を管理する。Memory は選択的な保存であり、transcript の lossless backup ではなく、context compaction の代わりにもならない。

---

## 試してみる

```sh
cd learn-claude-code
python s09_memory/code.py
```

1. `I prefer using tabs for indentation. Remember that.` と入力し、turn の後に `.memory/` へ新しい record が増え、`MEMORY.md` に index entry が作られたか確認する。
2. `q` で終了し、program を再起動して `What indentation style do I prefer?` と聞く。新しい session でも preference を recall できることを確認する。
3. code formatting と関係ない別の preference を保存してから indentation を質問し、現在の request に関係する memory だけが読み込まれるか確認する。
4. `Do not create files in this session.` と入力し、この一時的な条件が次の session の永続ルールにならないことを確認する。

モデルによって表現や抽出件数は変わる。確認するのは `.memory/` に何が保存されたか、後の session が関係する情報だけを recall したかだ。

---

## 次へ

Memory は情報をセッション間で保持する。しかし複雑なタスクには、各作業の状態と依存関係も永続的に記録する必要がある。会話内の TODO だけでは、プロセス終了後に進捗を追跡できない。

s10 Task System → タスク、状態、依存関係をディスクへ保存する。

<!-- translation-sync: zh@v3, en@v3, ja@v3 -->
