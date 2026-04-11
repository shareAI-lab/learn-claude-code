---
name: agent-builder
description: |
  面向任意领域设计并构建 AI Agent。适用于用户：
  (1) 提出“创建 agent / 构建助手 / 设计 AI 系统”
  (2) 想理解 agent 架构、agentic 模式或自治 AI
  (3) 需要能力设计、子 agent、规划或技能机制支持
  (4) 询问 Claude Code、Cursor 等 agent 内部实现
  (5) 希望将 agent 用于业务、研究、创作或运营任务
  关键词：agent, assistant, autonomous, workflow, tool use, multi-step, orchestration
---

# Agent 构建技能

为任意领域构建 AI Agent：客服、研究、运营、创作、行业流程自动化等。

## 核心理念

> **模型本身已经会“成为 agent”，你的工作是别挡路。**

Agent 的最小本质不是复杂工程，而是一个可行动循环：

```
LOOP:
  Model sees: context + available capabilities
  Model decides: act or respond
  If act: execute capability, add result, continue
  If respond: return to user
```

重点不在“技巧代码”，而在模型推理能力；代码负责提供行动环境。

## 三个要素

### 1) Capabilities（它能做什么）

原子动作：搜索、读取、创建、发送、查询、修改等。

**原则**：先从 3~5 个能力开始；只有在真实失败且确认缺能力时再加。

### 2) Knowledge（它知道什么）

按需注入的领域知识：规范、流程、最佳实践、Schema 等。

**原则**：知识应“可获取”而非“强灌入”。相关时加载，不要一次性塞满。

### 3) Context（它经历了什么）

会话历史把动作串成连贯行为。

**原则**：上下文稀缺且昂贵。噪声子任务要隔离；冗长输出要截断；保持清晰。

## 设计思路

开始构建前先回答：

- **Purpose**：要达成什么目标？
- **Domain**：在哪个业务世界运行？
- **Capabilities**：最关键的 3~5 个动作是什么？
- **Knowledge**：需要访问哪些专业知识？
- **Trust**：哪些决策可交给模型？

**关键**：信任模型，不要过度工程化，不要把流程写死。给能力与边界，让模型推理。

## 渐进复杂度

先简单，按真实需求升级：

| 级别 | 增加内容 | 何时增加 |
|---|---|---|
| Basic | 3-5 个能力 | 起步必备 |
| Planning | 进度跟踪 | 多步骤任务失去连贯性时 |
| Subagents | 子 Agent 隔离 | 探索型任务污染主上下文时 |
| Skills | 按需知识 | 需要领域专家知识时 |

多数 Agent 不需要超过 Level 2。

## 典型场景

- **Business**：CRM 查询、邮件、日历、审批
- **Research**：检索、文档分析、引用整理
- **Operations**：监控、工单、告警、升级处理
- **Creative**：素材生成、编辑、协作、审阅

模式通用，变化的是能力集合。

## 关键原则

1. 模型才是 Agent，代码只是循环与执行外壳
2. 能力决定“能做什么”
3. 知识决定“知道如何做什么”
4. 约束帮助聚焦
5. 信任释放模型潜力
6. 从最小可用开始、按使用反馈迭代

## 反模式

| 反模式 | 问题 | 建议 |
|---|---|---|
| 过度工程化 | 在需求出现前引入复杂性 | 先做最小版 |
| 能力过多 | 模型选择困难、混乱 | 先 3~5 个 |
| 流程写死 | 无法适应新情况 | 让模型决策 |
| 知识前置灌入 | 上下文膨胀 | 按需加载 |
| 微观管控 | 削弱模型推理 | 给边界并信任 |

## 资源

**理念与理论**
- `references/agent-philosophy.md`：Agent/Harness 思维深挖

**实现参考**
- `references/minimal-agent.py`：完整最小可运行 agent（约 80 行）
- `references/tool-templates.py`：能力定义模板
- `references/subagent-pattern.py`：上下文隔离模式

**脚手架**
- `scripts/init_agent.py`：生成新 agent 项目

## 心智转变

**从**：如何让系统执行 X？
**到**：如何让模型有能力完成 X？

**从**：这个任务流程是什么？
**到**：给模型哪些能力最有助于完成任务？

优秀的 agent 代码通常很朴素：循环简单、能力清晰、上下文干净。

**给模型能力和知识，剩下让它自己推理。**
