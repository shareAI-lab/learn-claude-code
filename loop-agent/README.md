# Loop Engineering Agent

中文 | [English](README.en.md)

一个基于 **Loop Engineering** 理念构建的自主编码 Agent 系统，参考 Addy Osmani 的 Loop Engineering 方法论，结合 learn-claude-code 教学仓库（s01-s20）的核心模式实现。

## 核心理念

```
Agent = Model + Harness
```

- **Model**：Claude API 提供推理和代码生成能力
- **Harness**：Trigger → Discover → Allocate → Execute → Verify → Integrate → Persist 七阶段循环

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        REPL (main.py)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  普通文本 → s20.agent_loop() (26 个工具全可用)            │   │
│  │  /loop <task> → orchestrator → maker/checker             │   │
│  │  /goal <cmd> → orchestrator.run_loop(goal)               │   │
│  │  /status /cron /quit                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     s20_comprehensive (基座)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  agent_loop, assemble_system_prompt, update_context,     │   │
│  │  prepare_context, assemble_tool_pool, trigger_hooks,     │   │
│  │  register_hook, scan_skills, list_skills, load_skill,    │   │
│  │  consume_cron_queue, collect_background_results,         │   │
│  │  create_worktree                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，设置 ANTHROPIC_API_KEY
```

### 2. 运行方式

```bash
# REPL 模式（默认）— 交互式命令行，支持三种模式
python loop-agent/main.py

# 单次执行模式 — Maker-Checker 流水线
python loop-agent/main.py --once

# 目标模式 — 持续执行直到验证命令成功
python loop-agent/main.py --goal "python -m pytest loop-agent/tests/"
```

### 3. REPL 命令

```bash
loop-agent >> /loop 修复登录 bug           # Maker-Checker 流水线
loop-agent >> /goal python -m pytest tests/ # 循环直到测试通过
loop-agent >> /status                       # 查看状态
loop-agent >> cron: */5 * * * * check issues # 添加定时任务
loop-agent >> 这个项目是做什么的？           # 直接对话（s20 全部能力）
loop-agent >> quit                          # 退出
```

## 七阶段工作流

| 阶段 | 说明 | 模块 |
|------|------|------|
| **Trigger** | 四种触发源：手动、Goal、Cron、CI/CD 失败 | `triggers.py` |
| **Discover** | 从触发事件提取任务项，过滤已处理 | `task_discovery.py` |
| **Allocate** | 创建 Git Worktree 隔离工作区 | `loop_agent.py` (调用 s20) |
| **Execute** | Maker 子代理执行编码（读写工具，50 轮） | `loop_agent.py` |
| **Verify** | Checker 子代理审查代码（只读工具，20 轮） | `loop_agent.py` |
| **Integrate** | 创建 PR 或直接提交 | `orchestrator.py` |
| **Persist** | 原子写入状态文件 | `state.py` |

## Maker-Checker 模式

```
任务 ──→ Maker (读写, 50轮) ──→ diff + 测试 ──→ Checker (只读, 20轮)
                │                                      │
                │          ┌──── APPROVED ─────────────┘
                │          ▼
                │     创建 PR / 提交
                │
                └──── REJECTED (带修改建议)
                       │
                       ▼
                  重试（最多 3 次，超过需人工介入）
```

- **Maker**：拥有 `bash`, `read_file`, `write_file`, `edit_file`, `glob` 工具（来自 s20）
- **Checker**：拥有 `bash`(只读), `read_file`, `glob` 工具，输出 `APPROVED` 或 `REJECTED` + 理由

## 文件结构

```
loop-agent/
├── main.py              # 入口（REPL/once/goal 三种模式）
├── config.py            # 集中配置（路径、轮次限制，模型由 s20 管理）
├── loop_agent.py        # s20 封装层（chat、init_context、run_maker、run_checker）
├── orchestrator.py      # 七阶段编排器
├── triggers.py          # 四种触发源（Manual/Goal/Cron/CI）
├── task_discovery.py    # 任务发现与过滤
├── state.py             # 文件状态管理（原子写入）
├── github_mock.py       # GitHub API Mock（演示用）
├── skills/              # 技能文件目录
│   └── loop-engineering/SKILL.md
├── mock_data/           # Mock 数据
│   ├── issues.json      # 模拟 Issue
│   ├── ci_results.json  # 模拟 CI 失败
│   └── pr_template.json # PR 模板
├── state/               # 状态文件目录
│   └── .loop-state.json
└── tests/               # 测试（57 个，全部通过）
    ├── test_state.py
    ├── test_triggers.py
    ├── test_github_mock.py
    ├── test_maker_checker.py
    └── test_orchestrator.py
```

## 来自 learn-claude-code 的模式

| 模式 | 来源 | 应用位置 |
|------|------|----------|
| `while stop_reason == "tool_use"` | s01 Agent Loop | `s20_comprehensive/code.py` |
| `TOOL_HANDLERS` 分发表 | s02 Tool Use | `s20_comprehensive/code.py` |
| `safe_path()` 工作区隔离 | s02 Tool Use | `s20_comprehensive/code.py` |
| 子代理 fresh context | s06 Subagent | `s20_comprehensive/code.py` |
| 两层技能加载 | s07 Skill Loading | `s20_comprehensive/code.py` |
| 原子文件状态 | s10 Memory | `state.py` |
| Cron 调度器 | s14 Cron Scheduler | `s20_comprehensive/code.py` |
| Worktree 命名规则 | s18 Worktree | `s20_comprehensive/code.py` |

## 配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | - | Claude API Key |
| `ANTHROPIC_BASE_URL` | - | 自定义 API 地址（可选） |
| `MODEL_ID` | `claude-sonnet-4-20250514` | 主模型（由 s20 管理） |
| `FALLBACK_MODEL_ID` | `claude-haiku-4-5-20251001` | 备用模型（由 s20 管理） |
| `GITHUB_TOKEN` | - | GitHub Token（Mock 模式可忽略） |
| `GITHUB_REPO` | `owner/repo` | 目标仓库 |

## 运行测试

```bash
pytest loop-agent/tests/ -v
```

## 许可证

MIT
