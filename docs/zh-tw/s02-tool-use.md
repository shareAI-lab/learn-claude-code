# s02: Tool Use (工具使用)

`s00 > s01 > [ s02 ] > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *"加一個工具, 只加一個 handler"* -- 迴圈不用動, 新工具註冊進 dispatch map 就行。
>
> **Harness 層**: 工具分發 -- 擴充套件模型能觸達的邊界。

## 問題

只有 `bash` 時, 所有操作都走 shell。`cat` 截斷不可預測, `sed` 遇到特殊字元就崩, 每次 bash 呼叫都是不受約束的安全面。專用工具 (`read_file`, `write_file`) 可以在工具層面做路徑沙箱。

關鍵洞察: 加工具不需要改迴圈。

## 解決方案

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

## 工作原理

1. 每個工具有一個處理函式。路徑沙箱防止逃逸工作區。

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

2. dispatch map 將工具名對映到處理函式。

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. 迴圈中按名稱查詢處理函式。迴圈體本身與 s01 完全一致。

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

加工具 = 加 handler + 加 schema。迴圈永遠不變。

## 相對 s01 的變更

| 元件           | 之前 (s01)         | 之後 (s02)                     |
|----------------|--------------------|--------------------------------|
| Tools          | 1 (僅 bash)        | 4 (bash, read, write, edit)    |
| Dispatch       | 硬編碼 bash 呼叫   | `TOOL_HANDLERS` 字典           |
| 路徑安全       | 無                 | `safe_path()` 沙箱             |
| Agent loop     | 不變               | 不變                           |

## 試一試

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

試試這些 prompt (英文 prompt 對 LLM 效果更好, 也可以用中文):

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`

## 如果你開始覺得“工具不只是 handler map”

到這裡為止，教學主線先把工具講成：

- schema
- handler
- `tool_result`

這是對的，而且必須先這麼學。

但如果你繼續把系統做大，很快就會發現工具層還會繼續長出：

- 許可權環境
- 當前訊息和 app state
- MCP client
- 檔案讀取快取
- 通知與 query 跟蹤

也就是說，在一個結構更完整的系統裡，工具層最後會更像一條“工具控制平面”，而不只是一張分發表。

這層不要搶正文主線。  
你先把這一章吃透，再繼續看：

- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## 訊息規範化

教學版的 `messages` 列表直接發給 API, 所見即所發。但當系統變複雜後 (工具超時、使用者取消、壓縮替換), 內部訊息列表會出現 API 不接受的格式問題。需要在傳送前做一次規範化。

### 為什麼需要

API 協議有三條硬性約束:
1. 每個 `tool_use` 塊**必須**有匹配的 `tool_result` (透過 `tool_use_id` 關聯)
2. `user` / `assistant` 訊息必須**嚴格交替** (不能連續兩條同角色)
3. 只接受協議定義的欄位 (內部後設資料會導致 400 錯誤)

### 實現

```python
def normalize_messages(messages: list) -> list:
    """將內部訊息列表規範化為 API 可接受的格式。"""
    normalized = []

    for msg in messages:
        # Step 1: 剝離內部欄位
        clean = {"role": msg["role"]}
        if isinstance(msg.get("content"), str):
            clean["content"] = msg["content"]
        elif isinstance(msg.get("content"), list):
            clean["content"] = [
                {k: v for k, v in block.items()
                 if k not in ("_internal", "_source", "_timestamp")}
                for block in msg["content"]
            ]
        normalized.append(clean)

    # Step 2: tool_result 配對補齊
    # 收集所有已有的 tool_result ID
    existing_results = set()
    for msg in normalized:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if block.get("type") == "tool_result":
                    existing_results.add(block.get("tool_use_id"))

    # 找出缺失配對的 tool_use, 插入佔位 result
    for msg in normalized:
        if msg["role"] == "assistant" and isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if (block.get("type") == "tool_use"
                        and block.get("id") not in existing_results):
                    # 在下一條 user 訊息中補齊
                    normalized.append({"role": "user", "content": [{
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": "(cancelled)",
                    }]})

    # Step 3: 合併連續同角色訊息
    merged = [normalized[0]] if normalized else []
    for msg in normalized[1:]:
        if msg["role"] == merged[-1]["role"]:
            # 合併內容
            prev = merged[-1]
            prev_content = prev["content"] if isinstance(prev["content"], list) \
                else [{"type": "text", "text": prev["content"]}]
            curr_content = msg["content"] if isinstance(msg["content"], list) \
                else [{"type": "text", "text": msg["content"]}]
            prev["content"] = prev_content + curr_content
        else:
            merged.append(msg)

    return merged
```

在 agent loop 中, 每次 API 呼叫前執行:

```python
response = client.messages.create(
    model=MODEL, system=system,
    messages=normalize_messages(messages),  # 規範化後再發送
    tools=TOOLS, max_tokens=8000,
)
```

**關鍵洞察**: `messages` 列表是系統的內部表示, API 看到的是規範化後的副本。兩者不是同一個東西。

## 教學邊界

這一章最重要的，不是把完整工具執行時一次講全，而是先講清 3 個穩定點：

- tool schema 是給模型看的說明
- handler map 是程式碼裡的分發入口
- `tool_result` 是結果迴流到主迴圈的統一齣口

只要這三點穩住，讀者就已經能自己在不改主迴圈的前提下新增工具。

許可權、hook、併發、流式執行、外部工具來源這些後續層次當然重要，但都應該建立在這層最小分發模型之後。
