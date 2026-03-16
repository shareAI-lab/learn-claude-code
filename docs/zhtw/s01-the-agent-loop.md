# s01: Agent 迴圈

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"One loop & Bash is all you need"* -- 一個工具 + 一個迴圈 = 一個 agent。

## 問題

語言模型可以推理程式碼，但它無法直接*碰觸*真實世界 -- 不能讀檔、跑測試、檢查錯誤。沒有迴圈時，每次工具呼叫都得手動複製貼上結果回去。你就成了那個迴圈本身。

## 解法

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (loop until stop_reason != "tool_use")
```

整個流程只靠一個退出條件控制。只要模型還在呼叫工具，迴圈就持續執行。

## 運作方式

1. 把使用者輸入當成第一則訊息。

```python
messages.append({"role": "user", "content": query})
```

2. 把 messages 與 tool definitions 一起送進 LLM。

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. 先附加 assistant 回覆。接著檢查 `stop_reason` -- 如果模型沒有呼叫工具，就結束。

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. 依序執行每個工具呼叫，收集結果後以 user 訊息附加回去，再回到步驟 2。

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
messages.append({"role": "user", "content": results})
```

整合成單一方法：

```python
def agent_loop(query):
    messages = [{"role": "user", "content": query}]
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

這樣不到 30 行，就有完整 agent。後續課程都只是疊加在這個基礎上 -- 不會改動這個迴圈。

## 相較前一版的變更

| Component     | Before     | After                          |
|---------------|------------|--------------------------------|
| Agent loop    | (none)     | `while True` + stop_reason     |
| Tools         | (none)     | `bash` (one tool)              |
| Messages      | (none)     | 累積訊息佇列                     |
| Control flow  | (none)     | `stop_reason != "tool_use"`    |

## 動手試試

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
