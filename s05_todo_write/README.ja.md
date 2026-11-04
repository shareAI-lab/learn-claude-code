# s05: TodoWrite — 計画なき Agent は途中で道を外れる

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → s02 → s03 → s04 → `s05` → [s06](../s06_subagent/) → s07 → ... → s16 → s17

> *"計画なき agent は風の向くままに"* — まず手順を列挙してから実行。長いタスクで見落としが減る。
>
> **Harness レイヤー**: 計画 — Agent が行動する前に考えさせる。

---

## 課題

Agent に複雑なタスクを与える：「全 Python ファイルを snake_case にリネームし、テストを実行し、失敗を修正して。」

Agent は作業を開始する。3 つのファイルをリネーム、テストを実行、2 つの失敗を発見、修正を開始。修正しているうちに、本来の目的が「snake_case にリネーム」だったことを忘れる。テストの失敗に注意を全て持っていかれる。

会話が長くなるほど悪化する：ツールの結果がコンテキストを埋め続け、システムプロンプトの影響力が希釈される。10 ステップのリファクタリング：ステップ 1-3 を終えた時点で Agent は即興で動き始める。ステップ 4-10 は既に注意の外に追い出されているから。

---

## ソリューション

![Todo Overview](images/todo-overview.ja.svg)

S05 は S04 のツールディスパッチ、権限チェック、Hooks を保持し、`todo_write` とリマインダーカウンターを追加する。`todo_write` は計画状態だけを更新し、実際の作業は既存のツールが行う。

新しいツールも `TOOL_HANDLERS[block.name]` を経由する。3 回連続のツール使用ラウンドで `todo_write` が呼ばれなければ、Harness は 3 回目のツール結果にリマインダーを追加する。

---

## 仕組み

**TodoManager** はメモリ上のタスクリストを保持し、更新を検証して、描画結果をモデルへ返す。`run_todo_write` は同じ状態を端末にも表示する：

```python
class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, todos: list | str) -> str:
        # Parse and validate before replacing the current list.
        validated = []
        ...
        self.items = validated
        return self.render()

    def render(self) -> str:
        # [ ] pending, [>] in progress, [x] completed
        ...


TODO = TodoManager()

def run_todo_write(todos: list | str) -> str:
    output = TODO.update(todos)
    print(output)
    return output
```

1 回の更新は最大 20 項目で、各項目には空でない `content` が必要となり、`in_progress` にできる項目は同時に 1 つだけ。文字列入力は JSON または Python のリスト表現として、`eval` を使わずに解析する。

ツール定義は他の 5 つと一緒にディスパッチマップに追加される：

```python
TOOLS = [
    {"name": "bash",       ...},
    {"name": "read_file",  ...},
    {"name": "write_file", ...},
    {"name": "edit_file",  ...},
    {"name": "glob",       ...},
    # s05: 新規追加
    {"name": "todo_write", "description": "Create and manage a task list ...",
     "input_schema": {
         "type": "object",
         "properties": {
             "todos": {
                 "type": "array",
                 "items": {
                     "type": "object",
                     "properties": {
                         "content": {"type": "string"},
                         "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                     },
                 },
             },
         },
     },
    },
]

TOOL_HANDLERS["todo_write"] = run_todo_write
```

**リマインダー**：3 回連続のツール使用ラウンドで `todo_write` が呼ばれなければ、リマインダーを 3 回目の結果に追加し、カウンターをリセットする：

```python
rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
if rounds_since_todo >= 3:
    results.append({
        "type": "text",
        "text": "<reminder>Update your todos.</reminder>",
    })
    rounds_since_todo = 0
```

Agent がタスクを受け取った後の典型的な流れ：まず `todo_write` を呼び出して全手順を列挙（全て `pending`）→ 一つの手順に取り掛かり、`in_progress` に変更 → 完了したら `completed` に変更 → 次の `pending` を見る → 続行。

**重要な洞察**：todo_write は Agent に**実行能力**を何も追加しない。追加するのは**計画能力**だ。

---

## s04 からの変更

| コンポーネント | 変更前 (s04) | 変更後 (s05) |
|--------------|-------------|-------------|
| ツール数 | 5 (bash, read, write, edit, glob) | 6 (+todo_write) |
| 計画能力 | なし | ステータス付き TODO リスト + リマインダー |
| SYSTEM プロンプト | 汎用プロンプト | 「先に計画してから実行」のガイダンスを追加 |
| ループ | ツールディスパッチと Hooks | 同じ分配経路に rounds_since_todo とリマインダー注入を追加 |

---

## 試してみよう

```sh
cd learn-claude-code
python s05_todo_write/code.py
```

以下のプロンプトを試してみよう：

1. `Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard`（まず 3 手順を列挙してから実行するはず）
2. `Create a Python package under s05_todo_write/example/demo_pkg with __init__.py, utils.py, and tests/test_utils.py`
3. `Review Python files under s05_todo_write/example and fix any style issues`

観察のポイント：最初のツール呼び出しは `todo_write` か？ TODO は何手順列挙されたか？ 実行中にステータスが `pending` から `in_progress` / `completed` に変わったか？

---

## 次へ

Agent は計画できるようになった。しかしタスクが大きすぎる場合、例えば「認証モジュール全体をリファクタリング」、TODO リストだけでは不十分。そのタスク自体が数十のサブタスクの集合体で、同じ会話のコンテキストに押し込めると溢れてしまう。

→ s06 Subagent：大きなタスクをサブタスクに分割し、それぞれを独立した Agent に任せる。それぞれが独自のクリーンなコンテキストを持ち、相互汚染がない。


<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
