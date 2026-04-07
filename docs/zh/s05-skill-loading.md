# s05: Skills (按需知识加载)

`s00 > s01 > s02 > s03 > s04 > [ s05 ] > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *不是把所有知识永远塞进 prompt，而是在需要的时候再加载正确那一份。*

## 这一章要解决什么问题

到了 `s04`，你的 agent 已经会：

- 调工具
- 做会话内规划
- 把大任务分给子 agent

接下来很自然会遇到另一个问题：

> 不同任务需要的领域知识不一样。

例如：

- 做代码审查，需要一套审查清单
- 做 Git 操作，需要一套提交约定
- 做 MCP 集成，需要一套专门步骤

如果你把这些知识包全部塞进 system prompt，就会出现两个问题：

1. 大部分 token 都浪费在当前用不到的说明上
2. prompt 越来越臃肿，主线规则越来越不清楚

所以这一章真正要做的是：

**把“长期可选知识”从 system prompt 主体里拆出来，改成按需加载。**

## 先解释几个名词

### 什么是 skill

这里的 `skill` 可以先简单理解成：

> 一份围绕某类任务的可复用说明书。

它通常会告诉 agent：

- 什么时候该用它
- 做这类任务时有哪些步骤
- 有哪些注意事项

### 什么是 discovery

`discovery` 指“发现有哪些 skill 可用”。

这一层只需要很轻量的信息，例如：

- skill 名字
- 一句描述

### 什么是 loading

`loading` 指“把某个 skill 的完整正文真正读进来”。

这一层才是昂贵的，因为它会把完整内容放进当前上下文。

## 最小心智模型

把这一章先理解成两层：

```text
第 1 层：轻量目录
  - skill 名称
  - skill 描述
  - 让模型知道“有哪些可用”

第 2 层：按需正文
  - 只有模型真正需要时才加载
  - 通过工具结果注入当前上下文
```

可以画成这样：

```text
system prompt
  |
  +-- Skills available:
      - code-review: review checklist
      - git-workflow: branch and commit guidance
      - mcp-builder: build an MCP server
```

当模型判断自己需要某份知识时：

```text
load_skill("code-review")
   |
   v
tool_result
   |
   v
<skill name="code-review">
完整审查说明
</skill>
```

这就是这一章最核心的设计。

## 关键数据结构

### 1. SkillManifest

先准备一份很轻的元信息：

```python
{
    "name": "code-review",
    "description": "Checklist for reviewing code changes",
}
```

它的作用只是让模型知道：

> 这份 skill 存在，并且大概是干什么的。

### 2. SkillDocument

真正被加载时，再读取完整内容：

```python
{
    "manifest": {...},
    "body": "... full skill text ...",
}
```

### 3. SkillRegistry

你最好不要把 skill 散着读取。

更清楚的方式是做一个统一注册表：

```python
registry = {
    "code-review": SkillDocument(...),
    "git-workflow": SkillDocument(...),
}
```

它至少要能回答两个问题：

1. 有哪些 skill 可用
2. 某个 skill 的完整内容是什么

## 最小实现

### 第一步：把每个 skill 放成一个目录

最小结构可以这样：

```text
skills/
  code-review/
    SKILL.md
  git-workflow/
    SKILL.md
```

### 第二步：从 `SKILL.md` 里读取最小元信息

```python
class SkillRegistry:
    def __init__(self, skills_dir):
        self.skills = {}
        self._load_all()

    def _load_all(self):
        for path in skills_dir.rglob("SKILL.md"):
            meta, body = parse_frontmatter(path.read_text())
            name = meta.get("name", path.parent.name)
            self.skills[name] = {
                "manifest": {
                    "name": name,
                    "description": meta.get("description", ""),
                },
                "body": body,
            }
```

这里的 `frontmatter` 你可以先简单理解成：

> 放在正文前面的一小段结构化元数据。

### 第三步：把 skill 目录放进 system prompt

```python
SYSTEM = f"""You are a coding agent.
Skills available:
{SKILL_REGISTRY.describe_available()}
"""
```

注意这里放的是**目录信息**，不是完整正文。

### 第四步：提供一个 `load_skill` 工具

```python
TOOL_HANDLERS = {
    "load_skill": lambda **kw: SKILL_REGISTRY.load_full_text(kw["name"]),
}
```

当模型调用它时，把完整 skill 正文作为 `tool_result` 返回。

### 第五步：让 skill 正文只在当前需要时进入上下文

这一步的核心思想就是：

> 平时只展示“有哪些知识包”，真正工作时才把那一包展开。

## skill、memory、CLAUDE.md 的边界

这三个概念很容易混。

### skill

可选知识包。  
只有在某类任务需要时才加载。

### memory

跨会话仍然有价值的信息。  
它是系统记住的东西，不是任务手册。

### CLAUDE.md

更稳定、更长期的规则说明。  
它通常比单个 skill 更“全局”。

一个简单判断法：

- 这是某类任务才需要的做法或知识：`skill`
- 这是需要长期记住的事实或偏好：`memory`
- 这是更稳定的全局规则：`CLAUDE.md`

## 它如何接到主循环里

这一章以后，system prompt 不再只是一段固定身份说明。

它开始长出一个很重要的新段落：

- 可用技能目录

而消息流里则会出现新的按需注入内容：

- 某个 skill 的完整正文

也就是说，系统输入现在开始分成两层：

```text
稳定层：
  身份、规则、工具、skill 目录

按需层：
  当前真的加载进来的 skill 正文
```

这也是 `s10` 会继续系统化展开的东西。

## 初学者最容易犯的错

### 1. 把所有 skill 正文永远塞进 system prompt

这样会让 prompt 很快臃肿到难以维护。

### 2. skill 目录信息写得太弱

如果只有名字，没有描述，模型就不知道什么时候该加载它。

### 3. 把 skill 当成“绝对规则”

skill 更像“可选工作手册”，不是所有轮次都必须用。

### 4. 把 skill 和 memory 混成一类

skill 解决的是“怎么做一类事”，memory 解决的是“记住长期事实”。

### 5. 一上来就讲太多多源加载细节

教学主线真正要先讲清的是：

**轻量发现，重内容按需加载。**

## 教学边界

这章只要先守住两层就够了：

- 轻量发现：先告诉模型有哪些 skill
- 按需深加载：真正需要时再把正文放进输入

所以这里不用提前扩到：

- 多来源收集
- 条件激活
- skill 参数化
- fork 式执行
- 更复杂的 prompt 管道拼装

如果读者已经明白“为什么不能把所有 skill 永远塞进 system prompt，而应该先列目录、再按需加载”，这章就已经讲到位了。

## 一句话记住

**Skill 系统的核心，不是“多一个工具”，而是“把可选知识从常驻 prompt 里拆出来，改成按需加载”。**
