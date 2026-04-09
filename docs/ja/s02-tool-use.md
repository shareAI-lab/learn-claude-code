# s02: Tool Use

`s01 > [ s02 ] > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *"ツールを足すなら、ハンドラーを1つ足すだけ"* -- ループは変わらない。新ツールは dispatch map に登録するだけ。
>
> **Harness 層**: ツール分配 -- モデルが届く範囲を広げる。

## 問題

`bash`だけでは、エージェントは何でもシェル経由で行う。`cat`は予測不能に切り詰め、`sed`は特殊文字で壊れ、すべてのbash呼び出しが制約のないセキュリティ面になる。`read_file`や`write_file`のような専用ツールなら、ツールレベルでパスのサンドボックス化を強制できる。

重要な点: ツールを追加してもループの変更は不要。

## 解決策

```
+--------+      +-------+      +------------------+
|  User  | ---> |  LLM  | ---> | Tool Dispatch    |
| prompt |      |       |      | {                |
+--------+      +---+---+      |   bash: run_bash |
                    ^           |   read: run_read |
                    |           |   write: run_wr  |
                    +-----------+   edit: run_edit |
                    tool_result | }                |
                                +------------------+

The dispatch map is a dict: {tool_name: handler_function}.
One lookup replaces any if/elif chain.
```

## 仕組み

1. 各ツールにハンドラ関数を定義する。パスのサンドボックス化でワークスペース外への脱出を防ぐ。

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    if limit and limit < len(lines):
        lines = lines[:limit]
    return "\n".join(lines)[:50000]
```

2. ディスパッチマップがツール名とハンドラを結びつける。

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. ループ内で名前によりハンドラをルックアップする。ループ本体はs01から不変。

```python
for block in response.content:
    if block.type == "tool_use":
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Unknown tool: {block.name}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

ツール追加 = ハンドラ追加 + スキーマ追加。ループは決して変わらない。

## s01からの変更点

| Component      | Before (s01)       | After (s02)                |
|----------------|--------------------|----------------------------|
| Tools          | 1 (bash only)      | 4 (bash, read, write, edit)|
| Dispatch       | Hardcoded bash call | `TOOL_HANDLERS` dict       |
| Path safety    | None               | `safe_path()` sandbox      |
| Agent loop     | Unchanged          | Unchanged                  |

## 試してみる

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`

## tool が handler map 以上に見え始めたら

ここまでは、教学上の主線として tool を次の 3 つに絞って捉えます。

- schema
- handler
- `tool_result`

この順番で学ぶのは正しいですし、まずはここを固める必要があります。

ただし system を大きくしていくと、tool 層はすぐに次のようなものを抱え込み始めます。

- 権限コンテキスト
- 現在の messages と app state
- MCP client
- file read cache
- 通知と query tracking

つまり、より完全な system では tool 層は単なる dispatch table というより、
小さな「tool control plane」に近づいていきます。

この層にいま主線を奪わせないでください。まずはこの章を理解してから、
次へ進むのがよいです。

- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## メッセージ正規化

教学版では内部の `messages` リストをそのまま API に送っています。見えている
ものがそのまま送信内容です。しかし system が複雑になると
(tool timeout、user cancel、compaction / replacement など)、内部メッセージ列が
API に拒否される形へ崩れていくことがあります。そこで API 呼び出し前に
1 回正規化が必要になります。

### なぜ必要か

API プロトコルには 3 つの強い制約があります。

1. 各 `tool_use` block には、`tool_use_id` で対応づけられた `tool_result`
   block が必ず必要
2. `user` / `assistant` メッセージは厳密に交互である必要がある
3. プロトコルで定義された field しか受け付けない。内部 metadata は
   400 error の原因になる

### 実装

```python
def normalize_messages(messages: list) -> list:
    """内部メッセージ列を API が受け取れる形式へ正規化する。"""
    cleaned = []

    for msg in messages:
        # Step 1: 内部用 metadata field を剥がす
        clean = {"role": msg["role"]}
        if isinstance(msg.get("content"), str):
            clean["content"] = msg["content"]
        elif isinstance(msg.get("content"), list):
            clean["content"] = [
                {k: v for k, v in block.items()
                 if not k.startswith("_")}
                for block in msg["content"]
                if isinstance(block, dict)
            ]
        else:
            clean["content"] = msg.get("content", "")
        cleaned.append(clean)

    # Step 2: 欠けている tool_result の対応を補う
    existing_results = set()
    for msg in cleaned:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    existing_results.add(block.get("tool_use_id"))

    repaired = []
    for msg in cleaned:
        repaired.append(msg)

        if msg["role"] != "assistant" or not isinstance(msg.get("content"), list):
            continue

        missing_results = []
        for block in msg["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("id") not in existing_results:
                missing_results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": "(cancelled)",
                })

        if missing_results:
            repaired.append({"role": "user", "content": missing_results})

    cleaned = repaired

    # Step 3: 連続する同一 role のメッセージを結合する
    if not cleaned:
        return cleaned

    merged = [cleaned[0]]
    for msg in cleaned[1:]:
        if msg["role"] == merged[-1]["role"]:
            prev = merged[-1]
            prev_content = prev["content"] if isinstance(prev["content"], list) \
                else [{"type": "text", "text": str(prev["content"])}]
            curr_content = msg["content"] if isinstance(msg["content"], list) \
                else [{"type": "text", "text": str(msg["content"])}]
            prev["content"] = prev_content + curr_content
        else:
            merged.append(msg)

    return merged
```

agent loop では、各 API 呼び出しの前に実行します。

```python
response = client.messages.create(
    model=MODEL, system=system,
    messages=normalize_messages(messages),
    tools=TOOLS, max_tokens=8000,
)
```

**重要な洞察**: メモリ上の `messages` リストは system の内部表現です。
API が見るのは、そのままの内部列ではなく、正規化後のコピーです。

## 教学上の簡略化

この章で本当に学ぶべきなのは、細かな production 差分ではありません。

学ぶべき中心は次の 4 点です。

1. モデルに見せる tool schema がある
2. 実装側には handler がある
3. 両者は dispatch map で結ばれる
4. 実行結果は `tool_result` として主ループへ戻る

より完成度の高い system では、この周りに権限、hook、並列実行、結果永続化、外部 capability routing などが増えていきます。

しかし、それらをここで全部追い始めると、初学者は

- schema と handler の違い
- dispatch map の役割
- `tool_result` がなぜ主ループへ戻るのか

という本章の主眼を見失いやすくなります。

この段階では、まず

**新しい tool を足しても主ループ自体は作り替えなくてよい**

という設計の強さを、自分で実装して理解できれば十分です。
