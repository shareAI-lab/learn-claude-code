# s02: Tool Use (工具使用)

`s00 > s01 > [ s02 ] > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *"加一个工具, 只加一个 handler"* -- 循环不用动, 新工具注册进 dispatch map 就行。
>
> **Harness 层**: 工具分发 -- 扩展模型能触达的边界。

## 问题

只有 `bash` 时, 所有操作都走 shell。`cat` 截断不可预测, `sed` 遇到特殊字符就崩, 每次 bash 调用都是不受约束的安全面。专用工具 (`read_file`, `write_file`) 可以在工具层面做路径沙箱。

关键洞察: 加工具不需要改循环。

## 解决方案

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

1. 每个工具有一个处理函数。路径沙箱防止逃逸工作区。

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

2. dispatch map 将工具名映射到处理函数。

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. 循环中按名称查找处理函数。循环体本身与 s01 完全一致。

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

加工具 = 加 handler + 加 schema。循环永远不变。

## 相对 s01 的变更

| 组件           | 之前 (s01)         | 之后 (s02)                     |
|----------------|--------------------|--------------------------------|
| Tools          | 1 (仅 bash)        | 4 (bash, read, write, edit)    |
| Dispatch       | 硬编码 bash 调用   | `TOOL_HANDLERS` 字典           |
| 路径安全       | 无                 | `safe_path()` 沙箱             |
| Agent loop     | 不变               | 不变                           |

## 试一试

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`

## 如果你开始觉得“工具不只是 handler map”

到这里为止，教学主线先把工具讲成：

- schema
- handler
- `tool_result`

这是对的，而且必须先这么学。

但如果你继续把系统做大，很快就会发现工具层还会继续长出：

- 权限环境
- 当前消息和 app state
- MCP client
- 文件读取缓存
- 通知与 query 跟踪

也就是说，在一个结构更完整的系统里，工具层最后会更像一条“工具控制平面”，而不只是一张分发表。

这层不要抢正文主线。  
你先把这一章吃透，再继续看：

- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## 消息规范化

教学版的 `messages` 列表直接发给 API, 所见即所发。但当系统变复杂后 (工具超时、用户取消、压缩替换), 内部消息列表会出现 API 不接受的格式问题。需要在发送前做一次规范化。

### 为什么需要

API 协议有三条硬性约束:
1. 每个 `tool_use` 块**必须**有匹配的 `tool_result` (通过 `tool_use_id` 关联)
2. `user` / `assistant` 消息必须**严格交替** (不能连续两条同角色)
3. 只接受协议定义的字段 (内部元数据会导致 400 错误)

### 实现

```python
def normalize_messages(messages: list) -> list:
    """将内部消息列表规范化为 API 可接受的格式。"""
    normalized = []

    for msg in messages:
        # Step 1: 剥离内部字段
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

    # Step 2: tool_result 配对补齐
    # 收集所有已有的 tool_result ID
    existing_results = set()
    for msg in normalized:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if block.get("type") == "tool_result":
                    existing_results.add(block.get("tool_use_id"))

    # 找出缺失配对的 tool_use, 插入占位 result
    for msg in normalized:
        if msg["role"] == "assistant" and isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if (block.get("type") == "tool_use"
                        and block.get("id") not in existing_results):
                    # 在下一条 user 消息中补齐
                    normalized.append({"role": "user", "content": [{
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": "(cancelled)",
                    }]})

    # Step 3: 合并连续同角色消息
    merged = [normalized[0]] if normalized else []
    for msg in normalized[1:]:
        if msg["role"] == merged[-1]["role"]:
            # 合并内容
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

在 agent loop 中, 每次 API 调用前运行:

```python
response = client.messages.create(
    model=MODEL, system=system,
    messages=normalize_messages(messages),  # 规范化后再发送
    tools=TOOLS, max_tokens=8000,
)
```

**关键洞察**: `messages` 列表是系统的内部表示, API 看到的是规范化后的副本。两者不是同一个东西。

## 教学边界

这一章最重要的，不是把完整工具运行时一次讲全，而是先讲清 3 个稳定点：

- tool schema 是给模型看的说明
- handler map 是代码里的分发入口
- `tool_result` 是结果回流到主循环的统一出口

只要这三点稳住，读者就已经能自己在不改主循环的前提下新增工具。

权限、hook、并发、流式执行、外部工具来源这些后续层次当然重要，但都应该建立在这层最小分发模型之后。
