# s06: Context Compact

`s01 > s02 > s03 > s04 > s05 > [ s06 ] > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *"コンテキストはいつか溢れる、空ける手段が要る"* -- 4レバー圧縮で無限セッションを実現。

## 問題

コンテキストウィンドウは有限だ。1000行のファイルに対する`read_file`1回で約4000トークンを消費する。30ファイルを読み20回のbashコマンドを実行すると、100,000トークン超。圧縮なしでは、エージェントは大規模コードベースで作業できない。

## 解決策

ツール出力時から手動トリガーまで、4つの圧縮レバー:

```
Every tool call:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Lever 0: persisted-output]     (at tool execution time)
  Large outputs (>50KB, bash >30KB) are written to disk
  and replaced with a <persisted-output> preview marker.
        |
        v
[Lever 1: micro_compact]        (silent, every turn)
  Replace tool_result > 3 turns old
  with "[Previous: used {tool_name}]"
  (preserves read_file results as reference material)
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Lever 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Lever 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## 仕組み

0. **レバー 0 -- persisted-output**: ツール出力がサイズ閾値を超えた場合、ディスクに書き込みプレビューマーカーに置換する。巨大な出力がコンテキストウィンドウに入るのを防ぐ。

```python
PERSIST_OUTPUT_TRIGGER_CHARS_DEFAULT = 50000
PERSIST_OUTPUT_TRIGGER_CHARS_BASH = 30000   # bashはより低い閾値を使用

def maybe_persist_output(tool_use_id, output, trigger_chars=None):
    if len(output) <= trigger:
        return output
    stored_path = _persist_tool_result(tool_use_id, output)
    return _build_persisted_marker(stored_path, output)
    # Returns: <persisted-output>
    #   Output too large (48.8KB). Full output saved to: .task_outputs/tool-results/abc123.txt
    #   Preview (first 2.0KB):
    #   ... first 2000 chars ...
    # </persisted-output>
```

モデルは後から`read_file`で保存パスにアクセスし、完全な内容を取得できる。

1. **レバー 1 -- micro_compact**: 各LLM呼び出しの前に、古いツール結果をプレースホルダーに置換する。`read_file`の結果は参照資料として保持する。

```python
PRESERVE_RESULT_TOOLS = {"read_file"}

def micro_compact(messages: list) -> list:
    tool_results = [...]  # collect all tool_result entries
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for part in tool_results[:-KEEP_RECENT]:
        if tool_name in PRESERVE_RESULT_TOOLS:
            continue   # keep reference material
        part["content"] = f"[Previous: used {tool_name}]"
    return messages
```

2. **レバー 2 -- auto_compact**: トークンが閾値を超えたら、完全なトランスクリプトをディスクに保存し、LLMに要約を依頼する。

```python
def auto_compact(messages: list) -> list:
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
    ]
```

3. **レバー 3 -- manual compact**: `compact`ツールが同じ要約処理をオンデマンドでトリガーする。

4. ループが4つのレバーすべてを統合する:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Lever 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Lever 2
        response = client.messages.create(...)
        # ... tool execution with persisted-output ... # Lever 0
        if manual_compact:
            messages[:] = auto_compact(messages)       # Lever 3
```

トランスクリプトがディスク上に完全な履歴を保持する。大きな出力は`.task_outputs/tool-results/`に保存される。何も真に失われず、アクティブなコンテキストの外に移動されるだけ。

## s05からの変更点

| Component         | Before (s05)     | After (s06)                |
|-------------------|------------------|----------------------------|
| Tools             | 5                | 5 (base + compact)         |
| Context mgmt      | None             | Four-lever compression     |
| Persisted-output  | None             | Large outputs -> disk + preview |
| Micro-compact     | None             | Old results -> placeholders|
| Auto-compact      | None             | Token threshold trigger    |
| Transcripts       | None             | Saved to .transcripts/     |

## 試してみる

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (micro-compactが古い結果を置換するのを観察する)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`

## 高完成度システムではどう広がるか

教材版は compact を理解しやすくするために、仕組みを大きく 4 本に絞っています。  
より完成度の高いシステムでは、その周りに追加の段階が増えます。

| レイヤー | 教材版 | 高完成度システム |
|---------|--------|------------------|
| 大きな出力 | 大きすぎる結果をディスクへ逃がす | 複数ツールの合計量も見ながら、文脈に入る前に予算調整する |
| 軽い整理 | 単純な micro-compact | フル要約の前に複数の軽量整理パスを入れる |
| フル compact | 閾値を超えたら要約 | 事前 compact、回復用 compact、エラー後 compact など役割分担が増える |
| 回復 | 要約 1 本に置き換える | compact 後に最近のファイル、計画、スキル、非同期状態などを戻す |
| 起動条件 | 自動または手動ツール | ユーザー操作、内部閾値、回復処理など複数の入口 |

ここで覚えるべき核心は変わりません。

**compact は「履歴を捨てること」ではなく、「細部をアクティブ文脈の外へ移し、連続性を保つこと」**  
です。
