# s07: Permission System (权限系统)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > [ s07 ] > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *模型可以提出行动建议，但真正执行之前，必须先过安全关。*

## 这一章的核心目标

到了 `s06`，你的 agent 已经能读文件、改文件、跑命令、做规划、压缩上下文。

问题也随之出现了：

- 模型可能会写错文件
- 模型可能会执行危险命令
- 模型可能会在不该动手的时候动手

所以从这一章开始，系统需要一条新的管道：

**“意图”不能直接变成“执行”，中间必须经过权限检查。**

## 建议联读

- 如果你开始把“模型提议动作”和“系统真的执行动作”混成一件事，先回 [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)，重新确认 query 是怎么进入控制面的。
- 如果你还没彻底稳住“工具请求为什么不能直接落到 handler”，建议把 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) 放在手边一起读。
- 如果你在 `PermissionRule / PermissionDecision / tool_result` 这几层对象上开始打结，先回 [`data-structures.md`](./data-structures.md)，把状态边界重新拆开。

## 先解释几个名词

### 什么是权限系统

权限系统不是“有没有权限”这样一个布尔值。

它更像一条管道，用来回答：

1. 这次调用要不要直接拒绝？
2. 能不能自动放行？
3. 剩下的要不要问用户？

### 什么是权限模式

权限模式是系统当前的总体风格。

例如：

- 谨慎一点：大多数操作都问用户
- 保守一点：只允许读，不允许写
- 流畅一点：简单安全的操作自动放行

### 什么是规则

规则就是“遇到某种工具调用时，该怎么处理”的小条款。

最小规则通常包含三部分：

```python
{
    "tool": "bash",
    "content": "sudo *",
    "behavior": "deny",
}
```

意思是：

- 针对 `bash`
- 如果命令内容匹配 `sudo *`
- 就拒绝

## 最小权限系统应该长什么样

如果你是从 0 开始手写，一个最小但正确的权限系统只需要四步：

```text
tool_call
  |
  v
1. deny rules     -> 命中了就拒绝
  |
  v
2. mode check     -> 根据当前模式决定
  |
  v
3. allow rules    -> 命中了就放行
  |
  v
4. ask user       -> 剩下的交给用户确认
```

这四步已经能覆盖教学仓库 80% 的核心需要。

## 为什么顺序是这样

### 第 1 步先看 deny rules

因为有些东西不应该交给“模式”去决定。

比如：

- 明显危险的命令
- 明显越界的路径

这些应该优先挡掉。

### 第 2 步看 mode

因为模式决定当前会话的大方向。

例如在 `plan` 模式下，系统就应该天然更保守。

### 第 3 步看 allow rules

有些安全、重复、常见的操作可以直接过。

比如：

- 读文件
- 搜索代码
- 查看 git 状态

### 第 4 步才 ask

前面都没命中的灰区，才交给用户。

## 推荐先实现的 3 种模式

不要一上来就做特别多模式。  
先把下面三种做稳：

| 模式 | 含义 | 适合什么场景 |
|---|---|---|
| `default` | 未命中规则时问用户 | 日常交互 |
| `plan` | 只允许读，不允许写 | 计划、审查、分析 |
| `auto` | 简单安全操作自动过，危险操作再问 | 高流畅度探索 |

先有这三种，你就已经有了一个可用的权限系统。

## 这一章最重要的数据结构

### 1. 权限规则

```python
PermissionRule = {
    "tool": str,
    "behavior": "allow" | "deny" | "ask",
    "path": str | None,
    "content": str | None,
}
```

你不一定一开始就需要 `path` 和 `content` 都支持。  
但规则至少要能表达：

- 针对哪个工具
- 命中后怎么处理

### 2. 权限模式

```python
mode = "default" | "plan" | "auto"
```

### 3. 权限决策结果

```python
{
    "behavior": "allow" | "deny" | "ask",
    "reason": "why this decision was made"
}
```

这三个结构已经足够搭起最小系统。

## 最小实现怎么写

```python
def check_permission(tool_name: str, tool_input: dict) -> dict:
    # 1. deny rules
    for rule in deny_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "deny", "reason": "matched deny rule"}

    # 2. mode
    if mode == "plan" and tool_name in WRITE_TOOLS:
        return {"behavior": "deny", "reason": "plan mode blocks writes"}
    if mode == "auto" and tool_name in READ_ONLY_TOOLS:
        return {"behavior": "allow", "reason": "auto mode allows reads"}

    # 3. allow rules
    for rule in allow_rules:
        if matches(rule, tool_name, tool_input):
            return {"behavior": "allow", "reason": "matched allow rule"}

    # 4. fallback
    return {"behavior": "ask", "reason": "needs confirmation"}
```

然后在执行工具前接进去：

```python
decision = perms.check(tool_name, tool_input)

if decision["behavior"] == "deny":
    return f"Permission denied: {decision['reason']}"
if decision["behavior"] == "ask":
    ok = ask_user(...)
    if not ok:
        return "Permission denied by user"

return handler(**tool_input)
```

## Bash 为什么值得单独讲

所有工具里，`bash` 通常最危险。

因为：

- `read_file` 只能读文件
- `write_file` 只能写文件
- 但 `bash` 几乎能做任何事

所以你不能只把 bash 当成一个普通字符串。

一个更成熟的系统，通常会把 bash 当成一门小语言来检查。

哪怕教学版不做完整语法分析，也建议至少先挡住这些明显危险点：

- `sudo`
- `rm -rf`
- 命令替换
- 可疑重定向
- 明显的 shell 元字符拼接

这背后的核心思想只有一句：

**bash 不是普通文本，而是可执行动作描述。**

## 初学者怎么把这章做对

### 第一步：先做 3 个模式

不要一开始就做 6 个模式、10 个来源、复杂 classifier。

先稳稳做出：

- `default`
- `plan`
- `auto`

### 第二步：先做 deny / allow 两类规则

这已经足够表达很多现实需求。

### 第三步：给 bash 加最小安全检查

哪怕只是模式匹配版，也比完全裸奔好很多。

### 第四步：加拒绝计数

如果 agent 连续多次被拒绝，说明它可能卡住了。

这时可以：

- 给出提示
- 建议切到 `plan`
- 让用户重新澄清目标

## 教学边界

这一章先只讲透一条权限管道就够了：

- 工具意图先进入权限判断
- 权限结果只分成 `allow / ask / deny`
- 通过以后才真的执行

先把这条主线做稳，比一开始塞进很多模式名、规则来源、写回配置、额外目录、自动分类器都更重要。

换句话说，这章要先让读者真正理解的是：

**任何工具调用，都不应该直接执行；中间必须先过一条权限管道。**

## 这章不应该讲太多什么

为了不打乱初学者心智，这章不应该过早陷入：

- 企业策略源的全部优先级
- 非常复杂的自动分类器
- 产品环境里的所有无头模式细节
- 某个特定生产代码里的全部 validator 名称

这些东西存在，但不属于第一层理解。

第一层理解只有一句话：

**任何工具调用，都不应该直接执行；中间必须先过一条权限管道。**

## 这一章和后续章节的关系

- `s07` 决定“能不能执行”
- `s08` 决定“执行前后还能不能插入额外逻辑”
- `s10` 会把当前模式和权限说明放进 prompt 组装里

所以这章是后面很多机制的安全前提。

## 学完这章后，你应该能回答

- 为什么权限系统不是一个简单开关？
- 为什么 deny 要先于 allow？
- 为什么要先做 3 个模式，而不是一上来做很复杂？
- 为什么 bash 要被特殊对待？

---

**一句话记住：权限系统不是为了让 agent 更笨，而是为了让 agent 的行动先经过一道可靠的安全判断。**
