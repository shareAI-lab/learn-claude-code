# s21: System Prompts 分析 — 读懂 Claude Code 的提示词设计

[中文](README.md) · [English](README.en.md)

s01 → ... → s10 → s11 → ... → s20 → `s21`
> *"读懂别人的提示词，才能写出自己的"* — 从 515+ 条真实提示词中提炼设计模式。
>
> **Harness 层**: 提示 — 分析、理解、提炼，而非搬运。

---

## 问题

s10 教了我们如何**构建**系统提示词——分段、按需组装、缓存。但 s10 的提示词是我们自己写的，只有 4 个 section，加起来不到 200 字。

真正的 Claude Code 呢？它的系统提示词有多少？长什么样？有什么设计模式？

三个关键问题：

1. **Claude Code 的提示词到底有多少？** 是一段文字还是 500 段？
2. **它们是怎么组织的？** 凭什么 515 条提示词不乱？
3. **有哪些可复用的设计模式？** 我们怎么把这些模式用到自己的项目里？

---

## 解决方案

![s21 Overview](images/s21-overview.svg)

s21 直接分析 [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) 仓库（基于 Claude Code v2.1.181，11.3k stars，515+ 条提示词），用 `code.py` 动态抓取、分类、统计，而不是手写一份静态文档。

核心思路：**教程自己就是分析器**。读者跑一遍 `code.py`，得到的是基于**最新数据**的分析报告，不受教程编写时间的限制。

```
Piebald-AI 仓库 (GitHub)           code.py 分析器              学习成果
+----------------------------+     +------------------+     +------------------+
| system-prompts/ (515+ .md) | --> | 抓取 README.md   | --> | 分类统计报告     |
| tools/ (20+ .md)           |     | 正则解析条目     |     | 设计模式识别     |
| README.md (分类索引)       |     | 分类 + 聚合      |     | 可复用原则       |
+----------------------------+     +------------------+     +------------------+
```

---

## 工作原理

### 1. 数据来源：Piebald-AI 仓库

Piebald-AI 团队在每次 Claude Code 发布后**几分钟内**更新这个仓库，从编译后的 JS 文件中提取系统提示词。数据来源可靠，且持续更新。

仓库结构（简化版）：

```
claude-code-system-prompts/
├── system-prompts/          ← 515+ 提示词文件（扁平目录）
│   ├── agent-prompt-explore.md
│   ├── agent-prompt-plan-mode-enhanced.md
│   ├── agent-prompt-code-review-part-1-*.md
│   ├── tool-description-bash.md
│   ├── tool-description-write.md
│   ├── data-anthropic-cli.md
│   ├── system-prompt-main.md
│   └── ... (500+ more)
├── tools/                   ← 工具描述（独立目录）
│   ├── bash.md
│   ├── write.md
│   └── ...
├── README.md                ← 分类索引（含 token 数）
└── CHANGELOG.md             ← 213 个版本的变更记录
```

**关键发现（修正）**：实际目录结构是 `system-prompts/` + `tools/` 两个扁平目录，不是之前估算的 `1-Agent Prompts/`、`4-Tools/` 等分类目录。分类信息在 README.md 中，不在目录结构里。

### 2. code.py 解析流程

```python
# 1. 从 GitHub 拉取 README.md
text = fetch_readme()

# 2. 正则解析所有条目（名称、token 数、分类）
prompts = parse_prompts_from_readme(text)
# → [PromptFile(name="Agent Prompt: Explore", tokens=575, category="sub_agent"), ...]

# 3. 聚合分析
analysis = analyze(prompts)
# → 分类统计、Top 10、设计模式检测

# 4. 生成报告
print(generate_report(analysis))
```

### 3. 分类体系

基于 README.md 的标题结构，自动分类：

| 分类 | 子类 | 示例 | 说明 |
|------|------|------|------|
| main | — | 核心身份提示词 | 仅 1 条 |
| sub_agent | Explore, Plan | 子代理提示词 | 独立的 agent |
| slash_command | /code-review, /security-review | 斜杠命令提示词 | 用户触发的命令 |
| creation_assistant | CLAUDE.md, Status line | 创建助手提示词 | 生成配置/文档 |
| utility | summarization, memory | 工具类提示词 | 内部功能 |
| data | API refs, CLI docs | 参考数据 | 知识注入 |
| tool | Bash, Write, TodoWrite | 工具描述 | 工具使用说明 |

### 4. 设计模式检测

`code.py` 自动检测 5 类设计模式：

| 模式 | 检测方法 | 实例 |
|------|---------|------|
| 多阶段分解 | 文件名含 `part N` | /code-review 拆成 9 个阶段 |
| 条件组装 | 文件名含 `condition`/`mode`/`override` | 不同模式加载不同提示词 |
| 安全约束 | 文件名含 `security`/`safety`/`guard` | 安全监控代理（7397+8328 tokens） |
| 记忆管理 | 文件名含 `memory`/`summariz`/`context` | 记忆合并、会话压缩 |
| Schema 驱动 | 文件名含 `structured`/`json`/`classifier` | 结构化输出、状态分类器 |

---

## 相对 s10 的演进

| 维度 | s10 | s21 |
|------|-----|-----|
| 视角 | 构建者（build） | 分析者（read & learn） |
| 数据来源 | 自己写的 4 个 section | Piebald-AI 仓库的 515+ 条真实提示词 |
| 提示词数量 | 4 | 515+ |
| 设计模式 | 条件组装 + 缓存 | 5 类设计模式 |
| 可运行性 | 需要 API key | 仅需网络，无 API key |
| 数据时效性 | 静态 | 动态（每次跑都拉最新数据） |

---

## 试一下

```sh
cd learn-claude-code
python s21_system_prompts_analysis/code.py
```

观察重点：

1. 输出第一行会显示实时抓取状态（`Fetching...`）
2. 分类统计表显示各分类的 token 分布
3. Top 10 显示最"重"的提示词是哪些
4. 设计模式部分展示检测到的 5 类模式
5. Key Insights 提炼关键数字

试试这些实验：

1. `python s21_system_prompts_analysis/code.py` — 查看完整分析报告
2. `python s21_system_prompts_analysis/code.py --json` — 输出 JSON 格式
3. `python s21_system_prompts_analysis/code.py --raw` — 输出原始解析数据
4. 过几周再跑一次 — 观察 Piebald-AI 仓库更新后的数据变化

---

## 设计原则提炼

从 515+ 条真实提示词中提炼的 6 条核心原则：

### 1. 具体约束优于泛泛而谈

Claude Code 的提示词**不说**"Be careful with commands"，而是**具体到命令级别**：

> "Never execute commands that escape the working directory."
> "Never delete files outside the workspace."

### 2. 多阶段分解复杂任务

/code-review 不是一条提示词，而是 9 条（part 1-9），每条负责一个阶段：
- part 1: 基础扫描角度
- part 2: 低强度模式
- part 3: 超高强度模式
- ...
- part 9: 修复应用

**原则**：一条提示词做一件事。复杂任务拆成流水线。

### 3. Schema 驱动的结构化输出

TodoWrite 用 JSON Schema 定义 4 个状态（pending/in_progress/completed），明确每个状态的含义和转换规则。不是用自然语言描述"你要管理任务"。

**原则**：用 Schema 代替自然语言，减少歧义。

### 4. 条件组装而非全量加载

Claude Code 不是在所有场景下都加载 515 条提示词。它根据环境、模式、配置**选择性加载**。例如：
- `is_headless` → 切换部分提示词
- `mcp_servers` → 注入 MCP 工具描述
- `sub_agent_type` → 切换整个代理提示词

**原则**：提示词要"懒加载"，用多少加载多少。

### 5. 安全约束始终存在

安全监控代理（7397 + 8328 = 15,725 tokens）是 Claude Code 中 **token 数最大的组合**。安全不是"附加功能"，而是提示词设计的**第一优先级**。

**原则**：安全约束不是"安全模块"，而是渗透到每个工具描述中。

### 6. 记忆系统是独立的提示词体系

memory consolidation、memory pruning、memory synthesis、memory file attachment——记忆不是一段文本，而是一个**独立的子代理体系**，有自己的提示词、工具、流程。

**原则**：把"记忆"当成一个独立 agent，而不是一个功能。

---

## 接下来

读懂了 Claude Code 的提示词设计，下一步是：**修改它**。

Piebald-AI 提供了 [tweakcc](https://github.com/Piebald-AI/tweakcc) 工具，可以修改 Claude Code 的任意提示词片段并注入到本地安装中。这是"读懂→修改→验证"的闭环。

<details>
<summary>深入 Piebald-AI 仓库</summary>

### 数据提取方法

Piebald-AI 使用脚本从 Claude Code 的 npm 包中提取提示词。提示词存储在编译后的 JS 文件中，通过正则匹配和字符串提取得到。提取的提示词与 Claude Code 实际使用的**完全一致**。

### 版本追踪

仓库维护了 213 个版本的 CHANGELOG（从 v2.0.14 到 v2.1.181），记录了每次版本更新中提示词的变化：
- 新增/删除哪些提示词
- token 数变化（+/- N tokens）
- 提示词内容修改摘要

### 数据规模演进

- 初始版本（2025.12）：~350 条提示词
- v2.1.181（2026.06）：~515 条提示词（+165 条）
- 平均每月新增 ~25 条提示词

### 提示词插值

许多提示词包含运行时插值变量，如 `{tool_list}`、`{sub_agent_list}`、`{cwd}`。Piebald-AI 仓库中的 token 计数基于**插值前的模板**，实际运行时的 token 数会有 ±20 的偏差。

</details>

<!-- translation-sync: zh@v1, en@v1 -->