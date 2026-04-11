# Agent Harness 工程哲学

> **模型本身已经会做 Agent；你的工作是给它构建一个值得行动的“世界”。**

## 基本事实

去掉框架、库、花哨架构后，剩下的核心只有：循环、模型、行动机会。

Agent 不是胶水代码本身。Agent 是“训练后的模型”。代码只是 Harness（工作外壳），为模型提供可感知、可行动的环境。

- **代码是 Harness**
- **模型是 Agent**

两者角色不能混淆。

## Agent 是什么

Agent 是能够“感知环境 -> 推理目标 -> 执行动作”的已训练模型（神经网络）。

无论是人类决策系统、强化学习模型，还是大型语言模型，本质都类似：
- 通过训练获得策略
- 在环境中基于观察做决策
- 通过动作影响环境并继续迭代

因此，Agent 的核心是模型，不是外围程序。

## Agent 不是什么

把 API 调用、if-else 分支、节点编排拼起来，不会自然“长出”真正智能体，只会得到脆弱流水线。

“能用规则覆盖一切”是错觉。真实开放环境里，规则系统很快失效；模型推理才是主引擎。

## Harness：我们真正要构建的东西

如果模型是 Agent，代码就是它的运行外壳：

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions
```

### Tools（手）

回答：**它能做什么**。

文件读写、命令执行、API 调用、浏览器操作、数据库查询等都属于工具。

**原则**：原子化、可组合、描述清晰。先 3~5 个，不够再加。

### Knowledge（专业知识）

回答：**它知道什么**。

产品文档、架构约定、规章制度、风格指南等应按需注入，而不是一次性塞入系统提示。

**原则**：可获取、可检索、按需加载。

### Context（记忆线程）

上下文把离散动作连接为连贯行为。

**原则**：上下文极其宝贵。高噪声子任务要隔离；历史过长要压缩；关键目标要可持久化。

### Permissions（边界）

回答：**它被允许做什么**。

文件沙箱、危险操作审批、外部系统边界控制都属于权限层。

**原则**：约束不是削弱能力，而是帮助聚焦与安全执行。

## 通用循环

所有高效 Agent 的核心都一样：

```
LOOP:
  Model sees: conversation history + available tools
  Model decides: act or respond
  If act: tool executed, result added to context, loop continues
  If respond: answer returned, loop ends
```

这不是简化版，而是主干架构本体。其他机制都是在其上叠加的增强层。

## Harness 工程原则

### 1) 信任模型

不要预设所有分支，不要过度搭规则树。

把工具和知识给到位，让模型自己规划路径；多数边缘场景里，模型推理优于硬编码分支。

### 2) 约束促进效果

好的约束会减少迷航，而不是微观操控。

例如：
- todo 只允许一个 `in_progress`，强制顺序聚焦
- 子 agent 只读，避免误改
- 超长上下文触发压缩，防止窗口污染

### 3) 渐进复杂度

永远不要一口气把全部机制堆满：

```
Level 0: Model + one tool (bash)
Level 1: + tool dispatch map
Level 2: + planning
Level 3: + subagents + skills
Level 4: + context management + persistence
Level 5: + teams + autonomy + isolation
```

从最小可行起步，基于真实使用反馈再升级。

## 思维转向

- 从“我该怎么让系统执行 X”
- 到“我该怎么让模型有能力完成 X”

- 从“用户说 Y 时流程怎么写死”
- 到“给模型什么工具最有助于处理 Y”

- 从“我在写 Agent”
- 到“我在给 Agent 构建 Harness”

## 结语

模型是 Agent，代码是 Harness。你不是在“写智能本身”，你是在构建智能运行的世界。

这个世界越清晰（感知更准、动作更稳、知识更可达、边界更明确），模型的能力就越能被稳定表达。
