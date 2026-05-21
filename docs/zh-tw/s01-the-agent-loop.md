# s01: The Agent Loop (Agent 迴圈)

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"One loop & Bash is all you need"* -- 一個工具 + 一個迴圈 = 一個 Agent。
>
> **Harness 層**: 迴圈 -- 模型與真實世界的第一道連線。

## 問題

語言模型能推理程式碼, 但碰不到真實世界 -- 不能讀檔案、跑測試、看報錯。沒有迴圈, 每次工具呼叫你都得手動把結果粘回去。你自己就是那個迴圈。

## 解決方案

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

一個退出條件控制整個流程。迴圈持續執行, 直到模型不再呼叫工具。

## 工作原理	

1. 使用者 prompt 作為第一條訊息。

```python
messages.append({"role": "user", "content": query})
```

2. 將訊息和工具定義一起發給 LLM。

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. 追加助手響應。檢查 `stop_reason` -- 如果模型沒有呼叫工具, 結束。

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. 執行每個工具呼叫, 收集結果, 作為 user 訊息追加。回到第 2 步。

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

組裝為一個完整函式:

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

不到 30 行, 這就是整個 Agent。後面 11 個章節都在這個迴圈上疊加機制 -- 迴圈本身始終不變。

## 變更內容

| 元件          | 之前       | 之後                           |
|---------------|------------|--------------------------------|
| Agent loop    | (無)       | `while True` + stop_reason     |
| Tools         | (無)       | `bash` (單一工具)              |
| Messages      | (無)       | 累積式訊息列表                 |
| Control flow  | (無)       | `stop_reason != "tool_use"`    |

## 試一試

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

試試這些 prompt (英文 prompt 對 LLM 效果更好, 也可以用中文):

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
