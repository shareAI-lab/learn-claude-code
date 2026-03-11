# s06: Context Compact

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *"コンテキストはいつか溢れる、空ける手段が要る"* -- 3層圧縮で無限セッションを実現。

## 問題

コンテキストウィンドウは有限だ。1000行のファイルに対する`read_file`1回で約4000トークンを消費する。30ファイルを読み20回のbashコマンドを実行すると、100,000トークン超。圧縮なしでは、エージェントは大規模コードベースで作業できない。

## 解決策

積極性を段階的に上げる3層構成:

```
Every turn:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Layer 1: micro_compact]        (silent, every turn)
  Replace older non-read_file tool results
  with "[Previous: used {tool_name}]"
  Keep read_file results intact as reference material
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Layer 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Layer 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## 仕組み

1. **第1層 -- micro_compact**: 各LLM呼び出しの前に、古い非 `read_file` ツール結果をプレースホルダーに置換しつつ、以前の `read_file` 出力は参照材料として保持する。

```python
def micro_compact(messages: list) -> list:
    tool_results = []
    # ... tool_results を集め、tool_name_map を構築する ...
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for _, _, part in tool_results[:-KEEP_RECENT]:
        tool_name = tool_name_map.get(part.get("tool_use_id", ""), "unknown")
        if tool_name == "read_file":
            continue
        if len(part.get("content", "")) > 100:
            part["content"] = f"[Previous: used {tool_name}]"
    return messages
```

2. **第2層 -- auto_compact**: トークンが閾値を超えたら、完全なトランスクリプトをディスクに保存し、LLMに要約を依頼する。

```python
def auto_compact(messages: list) -> list:
    # Save transcript for recovery
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM summarizes
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
        {"role": "assistant", "content": "Understood. Continuing."},
    ]
```

3. **第3層 -- manual compact**: `compact`ツールが同じ要約処理をオンデマンドでトリガーする。

4. ループが3層すべてを統合する:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Layer 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Layer 2
        response = client.messages.create(...)
        # ... tool execution ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Layer 3
```

トランスクリプトがディスク上に完全な履歴を保持する。何も真に失われず、アクティブなコンテキストの外に移動されるだけ。

## s05からの変更点

| Component      | Before (s05)     | After (s06)                |
|----------------|------------------|----------------------------|
| Tools          | 5                | 5 (base + compact)         |
| Context mgmt   | None             | Three-layer compression    |
| Micro-compact  | None             | 古い非 read_file 結果 -> プレースホルダー; ファイル文脈は保持 |
| Auto-compact   | None             | Token threshold trigger    |
| Transcripts    | None             | Saved to .transcripts/     |

## 試してみる

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (micro-compact が古い `read_file` 文脈を保持しつつ、より古いコマンド出力を縮める様子を観察する)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`
