# s01: Agent Loop — ループ一つで十分

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

`s01` → [s02](../s02_tool_use/) → s03 → s04 → ... → s16 → s17
> *"One loop & Bash is all you need"* — ツール一つ + ループ一つ = 一つの Agent。
>
> **Harness レイヤー**: ループ — モデルと現実世界をつなぐ最初の架け橋。

---

## 課題

モデルにこう頼んだとする：「ディレクトリ内のファイル一覧を取得して、XXX.py を実行して」。

モデルは bash コマンドを出力できるが、出力が終わると止まってしまう — 自分で実行することも、結果を見て推論を続けることもない。

手動で実行し、出力をチャットに貼り付ければ、モデルは続きを生成できる。次のコマンドが出たら、また実行して貼り付ける。

毎回の往復で、あなたが中間層になっている。これを自動化するのが、この章の目的だ。

---

## ソリューション

![Agent Loop](images/agent-loop.ja.svg)

一つの `while True` ループ — モデルがツールを呼べば続き、呼ばなければ停止。ループは response の content block を直接確認する：

| シグナル | 意味 | ループの動作 |
|----------|------|-------------|
| `tool_use` block を含む | モデルがツール呼び出しを要求 | 実行 → 結果を戻す → 続行 |
| `tool_use` block を含まない | モデルがツールを呼ばなかった | ループ終了 |

---

## 仕組み

このプロセスをコードに変換してみよう。ステップごとに：

**ステップ 1**：ユーザーの質問を最初のメッセージとして設定する。

```python
messages = [{"role": "user", "content": query}]
```

**ステップ 2**：メッセージとツール定義を一緒に LLM に送信する。

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

**ステップ 3**：モデルの応答を追加し、ツールを呼び出したか確認する。呼び出しなし → 終了。

```python
messages.append({"role": "assistant", "content": response.content})
tool_calls = [
    block for block in response.content if block.type == "tool_use"
]
if not tool_calls:
    return
```

実際の `tool_use` block だけが実行段階に進むため、空の tool result メッセージは追加されない。

**ステップ 4**：モデルが要求したツールを実行し、結果を収集する。

```python
results = []
for block in tool_calls:
    output = run_bash(block.input["command"])
    results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": output,
    })
```

**ステップ 5**：ツールの結果を新しいメッセージとして追加し、ステップ 2 に戻る。

```python
messages.append({"role": "user", "content": results})
```

完全な関数に組み立てる：

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [
            block for block in response.content if block.type == "tool_use"
        ]
        if not tool_calls:
            return

        results = []
        for block in tool_calls:
            output = run_bash(block.input["command"])
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})
```

30 行あまり — これが最小実行可能な agent harness のカーネルだ。これは知能そのものではなく、モデルが継続的に行動できるための最小ランタイムフレームワーク。モデルが決定し（ツールを呼ぶか、どれを呼ぶか）、harness が実行を担う（ツールを呼び出し、結果を新しいメッセージとして追加する）。次の 16 章はすべてこのループの上に仕組みを積み重ねていく。ループ自体は永遠に変わらない。

---

## 試してみよう

> **安全上の注意**: このコードはモデルが生成したシェルコマンドを実行します。プロジェクトファイルへの影響を避けるため、一時テストディレクトリで実行してください。s03 で権限制御を追加します。

**準備**（初回のみ）：

```sh
pip install -r requirements.txt
cp .env.example .env
# .env を編集し、ANTHROPIC_API_KEY と MODEL_ID を入力
```

**実行**：

```sh
python s01_agent_loop/code.py
```

以下のプロンプトを試してみよう：

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`

観察のポイント：モデルがツールを呼び出すとき（ループ継続）、呼び出さないとき（ループ終了）の違い。

---

## 次へ

現在、モデルが持っているのは bash だけだ — ファイルを読むには `cat`、書くには `echo ... >`、探すには `find`。不便でエラーも起きやすい。

→ s02 Tool Use：5 つの本格的なツールを与えたらどうなる？ モデルは複数のツールを同時に呼び出すか？ 並列実行で競合は起きないか？


<!-- translation-sync: zh@v2, en@v2, ja@v2 -->
