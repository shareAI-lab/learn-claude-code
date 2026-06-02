# s13: Slash Commands (斜杠命令)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ] s14 > s15 > s16 > s17 > s18 > s19`

> *"用户快捷键, 绕过模型直接执行"* -- 零 API 成本的瞬时操作。
>
> **Harness 层**: 输入拦截 -- 在消息到达模型之前,harness 截获命令。

## 问题

s12 之后, Agent 功能强大,但每次交互都走 LLM。"显示任务"消耗 token,"清空历史"消耗 token,"有哪些工具"也消耗 token。这些是 harness 操作,不需要模型参与。

## 解决方案

```
用户输入:
+-------------+
| "/tasks"    |
+-----+-------+
      |
      v
[斜杠命令路由器]  <--- harness 拦截,模型看不到
      |
+----+-----+------------+
|     |     |            |
v     v     v            v
列出  清空  显示      注入上下文
任务   历史   工具    (如 /plan)

两类命令:
  1. 独立命令 (不调用模型): /tasks, /clear, /tools
     - 零 API 成本,零延迟
  2. 上下文注入 (变成消息): /plan, /debug
     - 短输入 -> 丰富的预设指令
```

## 工作原理

1. **解析输入。** 以 `/` 开头则路由到命令处理器。

```python
def handle_slash_command(query):
    if not query.startswith("/"):
        return (None, query)  # 不是命令
    cmd = query[1:].split()[0]
    handler = SLASH_COMMANDS.get(cmd)
    ...
```

2. **执行独立命令。** 打印输出,跳过模型。

```python
if action == "standalone":
    if payload == "__CLEAR__":
        history.clear()
    else:
        print(payload)
    continue  # 永远不走到 agent_loop()
```

3. **注入上下文命令。** 展开为丰富 prompt,发给模型。

```python
if action == "inject":
    history.append({"role": "user", "content": payload})
    agent_loop(history)
```

## 试一试

```sh
cd learn-claude-code
python agents/s13_slash_commands.py
```

试试这些:

1. `/tasks` -- 列出任务 (无 API 调用)
2. `/tools` -- 显示可用工具 (无 API 调用)
3. `/plan` -- 进入结构化规划模式
4. `/clear` -- 清空对话历史
5. 普通文本 -- 正常路由给模型
