# learn-claude-code 项目摘要

> 本文件由 `README.md` 与 `requirements.txt` 汇总整理而成。

## 一句话概括

一套 **17 节渐进式教程**，主题是 **Harness Engineering（载体工程）**：教你如何围绕一个不变
的 agent loop，逐步构建出让大模型在真实环境中干活的代码基础设施（工具、知识、上下文、
权限、协作、编排）。

核心命题：

> **Agency 来自模型训练。Agent 产品 = Model（驾驶员）+ Harness（载具）。**

- 智能（感知、推理、行动的能力）来自模型权重，不是靠外部 if-else / 节点图 / prompt 链
  编排"工程化"出来的。
- 工程师真正负责的是 harness，它由五部分构成：
  `Tools + Knowledge + Observation + Action Interfaces + Permissions`。

## 核心模式：唯一的 Agent Loop

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            return

        results = []
        for block in tool_calls:
            output = TOOL_HANDLERS[block.name](**block.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})
```

模型的职责：决定何时调工具、何时停止。
代码的职责：执行模型要求的事。**循环恒定不变，变的只是工具、知识与权限。**

## 17 节课程

| 阶段 | 章节 | 关键机制 |
|---|---|---|
| 1. 让 Agent 能行动 | s01 Agent Loop | 一个 `while True` + bash 工具 |
| | s02 Tool Use | `TOOL_HANDLERS` 分发表、并发执行 |
| | s03 Permission | 权限规则、审批流水线 |
| | s04 Hooks | `PreToolUse` / `PostToolUse` 扩展点 |
| 2. 处理复杂工作 | s05 TodoWrite | 先计划后执行，完成率翻倍 |
| | s06 Subagent | 独立 `messages[]`，只回传最终文本 |
| | s08 Context Compact | 工具结果预算 / snip / micro / 历史摘要四步压缩 |
| 3. 跨会话记忆 | s09 Memory | 选择、抽取、整合三个子系统 |
| 4. 长时间运行 | s10 Task System | `TaskRecord` / `blockedBy` / 落盘持久化 |
| | s11 Background Tasks | 后台线程 + 完成通知队列 |
| | s12 Cron Scheduler | 按时间自动触发任务 |
| 5. 多 Agent 协作 | s13 Agent Teams | 常驻队友、原子任务认领、任务绑定 worktree、类型化协议 |
| 6. 扩展与组装 | s07 Skill Loading | 技能目录按需展开 |
| | s14 MCP Plugin | 外部工具并入统一工具池 |
| | s15 Integrated Harness | 所有机制共用一套 harness |
| 7. 编排与目标闭环 | s16 Workflow Runtime | 脚本编排 + 生命周期事件 + 可恢复 journal |
| | s17 Goal Loop | 独立评估器把关，判定循环何时可以停止 |

推荐阅读顺序：s01 → s17；s15 串联完整运行时，s16 / s17 是聚焦的机制示例。

## 仓库结构

```
learn-claude-code/
  s01_agent_loop/ ... s17_goal_loop/   # 每章：README.md(英) + .zh.md + .ja.md + code.py + images/
  agents/                              # 旧版 12 课可运行副本 + s_full.py
  docs/                                # 旧版 12 课文档（迁移期保留）
  skills/                              # s07 使用的技能文件
  tests/                               # 测试
  web/                                 # 由根目录课程生成的网页面板
  README.md / README-zh.md / README-ja.md
  CONTRIBUTING.md / LICENSE (MIT)
```

两个教程轨道并存：**根目录 `s01-s17` 为当前正式版**，`docs/` + `agents/` 为旧版 12 课
（章节编号与新版本不对应，勿混用）。

## 依赖与运行

### requirements.txt（仅 3 个依赖）

| 包 | 版本约束 | 用途 |
|---|---|---|
| `anthropic` | `>=0.25.0` | Anthropic SDK，调用 Claude 的 `messages.create` 接口 |
| `python-dotenv` | `>=1.0.0` | 从 `.env` 加载 API Key |
| `pyyaml` | `>=6.0` | 解析技能的 YAML 元数据（s07 等） |

依赖极简——刻意验证了"harness 不需要庞大框架"这一主张。

### 快速开始

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env          # 配置 ANTHROPIC_API_KEY
python s01_agent_loop/code.py # 起点：一个循环 + bash
python s17_goal_loop/code.py  # 终点：直到目标达成才停
```

旧版轨道：`python agents/s01_agent_loop.py`、`agents/s_full.py`。
网页版：`cd web && npm install && npm run dev`（http://localhost:3000）。

> 注：当前仓库根目录只有 `.env`，**没有 `.env.example`**，首次配置需自行创建该文件并写入
> `ANTHROPIC_API_KEY=...`。

## 延伸

- `Kode-CLI`（`npm i -g @shareai-lab/kode`）：开源编码 Agent CLI，支持 Skill 与 LSP，兼容
  GLM / MiniMax / DeepSeek 等开放模型。
- `kode-agent-sdk`：可嵌入后端的无进程开销 Agent SDK。
- `claw0`：姊妹教程，用 **heartbeat + cron + IM 多通道 + 记忆 + Soul 人格** 把"用完即弃"的
  Agent 变成永远在线的个人助手。

## 设计哲学

- 以 Claude Code 为范例，但重点不是抄源码，而是理解它"不试图成为 Agent 本身"——只给模型
  工具、知识、上下文管理与权限边界，然后退到一边。
- 每个 agent 执行过的轨迹都是训练下一代模型的原料。
- **把 harness 造好，剩下的交给模型。**
