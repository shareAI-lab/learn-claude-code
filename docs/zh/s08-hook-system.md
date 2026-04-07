# s08: Hook System (Hook 系统)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > [ s08 ] > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *不改主循环代码，也能在关键时机插入额外行为。*

## 这章要解决什么问题

到了 `s07`，我们已经能在工具执行前做权限判断。

但很多真实需求并不属于“允许 / 拒绝”这条线，而属于：

- 在某个固定时机顺手做一点事
- 不改主循环主体，也能接入额外规则
- 让用户或插件在系统边缘扩展能力

例如：

- 会话开始时打印欢迎信息
- 工具执行前做一次额外检查
- 工具执行后补一条审计日志

如果每增加一个需求，你都去修改主循环，主循环就会越来越重，最后谁都不敢动。

所以这一章要引入的机制是：

**主循环只负责暴露“时机”，真正的附加行为交给 hook。**

## 建议联读

- 如果你还在把 hook 想成“往主循环里继续塞 if/else”，先回 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)，重新确认主循环和控制面的边界。
- 如果你开始把主循环、tool handler、hook side effect 混成一层，建议先看 [`entity-map.md`](./entity-map.md)，把谁负责推进主状态、谁只是旁路观察分开。
- 如果你准备继续读后面的 prompt、recovery、teams，可以把 [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) 一起放在旁边，因为从这一章开始“控制面 + 侧车扩展”会反复一起出现。

## 什么是 hook

你可以把 `hook` 理解成一个“预留插口”。

意思是：

1. 主系统运行到某个固定时机
2. 把当前上下文交给 hook
3. hook 返回结果
4. 主系统再决定下一步怎么继续

最重要的一句话是：

**hook 让系统可扩展，但不要求主循环理解每个扩展需求。**

主循环只需要知道三件事：

- 现在是什么事件
- 要把哪些上下文交出去
- 收到结果以后怎么处理

## 最小心智模型

教学版先只讲 3 个事件：

- `SessionStart`
- `PreToolUse`
- `PostToolUse`

这样做不是因为系统永远只有 3 个事件，  
而是因为初学者先把这 3 个事件学明白，就已经能自己做出一套可用的 hook 机制。

可以把它想成这条流程：

```text
主循环继续往前跑
  |
  +-- 到了某个预留时机
  |
  +-- 调用 hook runner
  |
  +-- 收到 hook 返回结果
  |
  +-- 决定继续、阻止、还是补充说明
```

## 教学版统一返回约定

这一章最容易把人讲乱的地方，就是“不同 hook 事件的返回语义”。

教学版建议先统一成下面这套规则：

| 退出码 | 含义 |
|---|---|
| `0` | 正常继续 |
| `1` | 阻止当前动作 |
| `2` | 注入一条补充消息，再继续 |

这套规则的价值不在于“最真实”，而在于“最容易学会”。

因为它让你先记住 hook 最核心的 3 种作用：

- 观察
- 拦截
- 补充

等教学版跑通以后，再去做“不同事件采用不同语义”的细化，也不会乱。

## 关键数据结构

### 1. HookEvent

```python
event = {
    "name": "PreToolUse",
    "payload": {
        "tool_name": "bash",
        "input": {"command": "pytest"},
    },
}
```

它回答的是：

- 现在发生了什么事
- 这件事的上下文是什么

### 2. HookResult

```python
result = {
    "exit_code": 0,
    "message": "",
}
```

它回答的是：

- hook 想不想阻止主流程
- 要不要向模型补一条说明

### 3. HookRunner

```python
class HookRunner:
    def run(self, event_name: str, payload: dict) -> dict:
        ...
```

主循环不直接关心“每个 hook 的细节实现”。  
它只把事件交给统一的 runner。

这就是这一章的关键抽象边界：

**主循环知道事件名，hook runner 知道怎么调扩展逻辑。**

## 最小执行流程

先看最重要的 `PreToolUse` / `PostToolUse`：

```text
model 发起 tool_use
    |
    v
run_hook("PreToolUse", ...)
    |
    +-- exit 1 -> 阻止工具执行
    +-- exit 2 -> 先补一条消息给模型，再继续
    +-- exit 0 -> 直接继续
    |
    v
执行工具
    |
    v
run_hook("PostToolUse", ...)
    |
    +-- exit 2 -> 追加补充说明
    +-- exit 0 -> 正常结束
```

再加上 `SessionStart`，一整套最小 hook 机制就立住了。

## 最小实现

### 第一步：准备一个事件到处理器的映射

```python
HOOKS = {
    "SessionStart": [on_session_start],
    "PreToolUse": [pre_tool_guard],
    "PostToolUse": [post_tool_log],
}
```

这里先用“一个事件对应一组处理函数”的最小结构就够了。

### 第二步：统一运行 hook

```python
def run_hooks(event_name: str, payload: dict) -> dict:
    for handler in HOOKS.get(event_name, []):
        result = handler(payload)
        if result["exit_code"] in (1, 2):
            return result
    return {"exit_code": 0, "message": ""}
```

教学版里先用“谁先返回阻止/注入，谁就优先”的简单规则。

### 第三步：接进主循环

```python
pre = run_hooks("PreToolUse", {
    "tool_name": block.name,
    "input": block.input,
})

if pre["exit_code"] == 1:
    results.append(blocked_tool_result(pre["message"]))
    continue

if pre["exit_code"] == 2:
    messages.append({"role": "user", "content": pre["message"]})

output = run_tool(...)

post = run_hooks("PostToolUse", {
    "tool_name": block.name,
    "input": block.input,
    "output": output,
})
```

这一步最关键的不是代码量，而是心智：

**hook 不是主循环的替代品，hook 是主循环在固定时机对外发出的调用。**

## 这一章的教学边界

如果你后面继续扩展平台，hook 事件面当然会继续扩大。

常见扩展方向包括：

- 生命周期事件：开始、结束、配置变化
- 工具事件：执行前、执行后、失败后
- 压缩事件：压缩前、压缩后
- 多 agent 事件：子 agent 启动、任务完成、队友空闲

但教学仓这里要守住一个原则：

**先把 hook 的统一模型讲清，再慢慢增加事件种类。**

不要一开始就把几十种事件、几十套返回语义全部灌给读者。

## 初学者最容易犯的错

### 1. 把 hook 当成“到处插 if”

如果还是散落在主循环里写条件分支，那还不是真正的 hook 设计。

### 2. 没有统一的返回结构

今天返回字符串，明天返回布尔值，后天返回整数，最后主循环一定会变乱。

### 3. 一上来就把所有事件做全

教学顺序应该是：

1. 先学会 3 个事件
2. 再学会统一返回协议
3. 最后才扩事件面

### 4. 忘了说明“教学版统一语义”和“高完成度细化语义”的区别

如果这层不提前说清，读者后面看到更复杂实现时会以为前面学错了。

其实不是学错了，而是：

**先学统一模型，再学事件细化。**

## 学完这一章，你应该真正掌握什么

学完以后，你应该能自己清楚说出下面几句话：

1. hook 的作用，是在固定时机扩展系统，而不是改写主循环。
2. hook 至少需要“事件名 + payload + 返回结果”这三样东西。
3. 教学版可以先用统一的 `0 / 1 / 2` 返回约定。
4. `PreToolUse` 和 `PostToolUse` 已经足够支撑最核心的扩展能力。

如果这 4 句话你已经能独立复述，说明这一章的核心心智已经建立起来了。

## 下一章学什么

这一章解决的是：

> 在固定时机插入行为。

下一章 `s09` 要解决的是：

> 哪些信息应该跨会话留下，哪些不该留。

也就是从“扩展点”进一步走向“持久状态”。
