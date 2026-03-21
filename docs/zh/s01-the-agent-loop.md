# s01: The Agent Loop (智能体循环)

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"One loop & Bash is all you need"* -- 一个工具 + 一个循环 = 一个智能体。
>
> **Harness 层**: 循环 -- 模型与真实世界的第一道连接。

## 问题

语言模型能推理代码, 但碰不到真实世界 -- 不能读文件、跑测试、看报错。没有循环, 每次工具调用你都得手动把结果粘回去。你自己就是那个循环。

## 解决方案

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

一个退出条件控制整个流程。循环持续运行, 直到模型不再调用工具。

## 工作原理

1. 用户 prompt 作为第一条消息。

```python
# 先把用户问题放进对话历史里。
# 模型后续看到的上下文，全部来自这份 messages。
messages.append({"role": "user", "content": query})
```

2. 将消息和工具定义一起发给 LLM。

```python
# 把当前对话历史和工具定义一起发给模型。
# 只有传入 TOOLS，模型才知道自己能调用哪些动作。
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. 追加助手响应。检查 `stop_reason` -- 如果模型没有调用工具, 结束。

```python
# 先原样保存 assistant 这一轮的输出。
# 这里的 response.content 里可能同时有文本块和工具调用块。
messages.append({"role": "assistant", "content": response.content})
# 如果模型这轮没有继续请求工具，循环就结束。
if response.stop_reason != "tool_use":
    return
```

4. 执行每个工具调用, 收集结果, 作为 user 消息追加。回到第 2 步。

```python
# 先收集这一轮里所有工具执行结果，再统一喂回模型。
results = []
for block in response.content:
    # 同一个响应里可能混着普通文本块和 tool_use 块。
    # 真正需要执行的只有工具调用块。
    if block.type == "tool_use":
        # 读取模型生成的命令，并在本地执行它。
        output = run_bash(block.input["command"])
        results.append({
            # tool_result 会把执行结果挂回对应的那次工具调用。
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
# 作为下一条 user 消息追加，模型才能基于结果继续推理。
messages.append({"role": "user", "content": results})
```

组装为一个完整函数:

```python
def agent_loop(query):
    # 初始化对话历史，起点只有当前用户问题。
    messages = [{"role": "user", "content": query}]
    while True:
        # 每轮都让模型基于当前上下文决定下一步动作。
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        # 先保存模型输出，避免后面丢失上下文。
        messages.append({"role": "assistant", "content": response.content})

        # 没有工具调用时，说明 agent 已经得到最终回答。
        if response.stop_reason != "tool_use":
            return

        # 否则执行工具，并把结果整理成下一轮输入。
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        # 把工具结果追加回 messages，然后继续下一轮循环。
        messages.append({"role": "user", "content": results})
```

不到 30 行, 这就是整个智能体。后面 11 个章节都在这个循环上叠加机制 -- 循环本身始终不变。

## 变更内容

| 组件          | 之前       | 之后                           |
|---------------|------------|--------------------------------|
| Agent loop    | (无)       | `while True` + stop_reason     |
| Tools         | (无)       | `bash` (单一工具)              |
| Messages      | (无)       | 累积式消息列表                 |
| Control flow  | (无)       | `stop_reason != "tool_use"`    |

## 试一试

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
