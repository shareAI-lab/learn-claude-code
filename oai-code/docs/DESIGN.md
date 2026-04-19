# oai-code 设计文档（精简版 v0.1）

> 面向生产可用的、基于 OpenAI 兼容协议的命令行编码 Agent。目标是做一个真正能日常使用的 Claude Code 替代品，同时兼容 Claude Code 工具生态的语义。

---

## 1. 定位与目标

**一句话**：oai-code 是一个 Python CLI 编码 Agent，底层通过 OpenAI 兼容协议调用任意 LLM（OpenAI / DeepSeek / Qwen / OpenRouter / Ollama / vLLM 等），对外呈现与 Claude Code 类似的交互体验和工具集。

**核心目标**
- **实用优先**：日常能用，能跑完整任务（读代码、改代码、跑测试、提交）
- **供应商无关**：一套代码切换任意 OpenAI 兼容后端，仅改 `base_url` / `model` / `api_key`
- **Claude Code 生态兼容**：工具命名、语义、`CLAUDE.md` 记忆、`skills/` 结构尽量对齐
- **机制完整**：覆盖当前 learn-claude-code 的 s01-s11 全部能力

**非目标（至少 v1 不做）**
- 不做浏览器 Web UI
- 不做 TS/Node 版本
- 不追求完全复刻 Claude Code 的 TUI 细节
- 不做 s12 worktree 隔离（后续迭代）

---

## 2. 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 与现有项目一致；生态成熟 |
| LLM SDK | `openai>=1.0` | 官方 SDK 原生支持 `base_url` 切换任意兼容后端 |
| 终端 UI | `rich` + `prompt_toolkit` | Rich 做渲染、PT 做输入与快捷键 |
| 并发 | `asyncio` + `threading` | asyncio 跑 Agent Loop 与流式；线程池跑 Bash/后台任务 |
| 配置 | `pydantic` + `pyyaml` + `python-dotenv` | 类型安全的配置模型 |
| MCP | `mcp` 官方 Python SDK | 接入 MCP server 作为工具来源 |
| 打包 | `uv` / `pyproject.toml` | 单命令安装，可 `pipx install oai-code` |

---

## 3. 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                         REPL / CLI 入口                         │
│  oaic (交互)  │  oaic -p "..." (单次)  │  oaic /slash-cmd       │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                       Agent Orchestrator                       │
│   - 系统提示拼装（项目CLAUDE.md + skills 目录 + 工具清单）      │
│   - 消息历史 / 流式渲染 / 中断处理                              │
└─────┬────────────┬──────────────┬──────────────┬─────────────┘
      │            │              │              │
┌─────▼──┐   ┌─────▼─────┐  ┌─────▼──────┐ ┌─────▼──────┐
│ LLM    │   │ Tool      │  │ Context    │ │ Session    │
│ Client │   │ Registry  │  │ Manager    │ │ Store      │
│(OpenAI │   │ + Dispatcher│ │(microcompact│ │(.oaic/)   │
│  SDK)  │   │           │  │ + auto)     │ │           │
└────────┘   └─────┬─────┘  └────────────┘ └────────────┘
                   │
      ┌────────────┼─────────────────────────────┐
      │            │             │               │
  ┌───▼───┐  ┌─────▼────┐  ┌─────▼─────┐  ┌─────▼─────┐
  │ 内置  │  │ Skills   │  │ Subagent  │  │ MCP       │
  │ 工具  │  │ Loader   │  │ Runner    │  │ Servers   │
  │ 集    │  │          │  │           │  │           │
  └───────┘  └──────────┘  └───────────┘  └───────────┘
```

---

## 4. 模块划分

### 4.1 `oai_code/llm/` — LLM 抽象层
- 统一封装 OpenAI Chat Completions API（包括 `tool_calls` / 流式 / 多模态）
- 支持 provider profile（预置 openai/deepseek/qwen/openrouter/ollama 的 base_url）
- 负责 **token 估算**、**自动重试**、**速率限制**
- 不做 LiteLLM 层，保持协议单纯

### 4.2 `oai_code/tools/` — 内置工具
对齐 Claude Code 的命名与语义（底层依旧用 OpenAI function calling 协议）：

| 名称 | 对应 s0x | 说明 |
|------|---------|------|
| `Bash` | s02 | 跑 shell，带超时和危险命令拦截 |
| `Read` / `Write` / `Edit` | s02 | 文件读写与精确替换 |
| `Glob` / `Grep` | 新增 | ripgrep 驱动的代码检索（原项目没有） |
| `TodoWrite` | s03 | 短期 checklist |
| `Task` (subagent) | s04 | 派发子 agent 做隔离探索/执行 |
| `LoadSkill` | s05 | 按名载入 skill 正文 |
| `Compact` | s06 | 手动压缩上下文 |
| `TaskCreate/Update/List/Get` | s07 | 持久化任务系统（`.oaic/tasks/`） |
| `BackgroundRun/Check` | s08 | 后台任务与通知回流 |
| `SpawnTeammate/SendMessage/ReadInbox/Broadcast/...` | s09-s11 | 多 agent 协作（v1 可选开关）；**完整列表见 `TOOLS.md §6`** |

### 4.3 `oai_code/context/` — 上下文管理
- **microcompact**：每轮 LLM 调用前的量化规则
  - 保留最近 **N=3** 轮完整 tool_result 原文
  - 更早的 tool_result：体积 > **4KB** 时落盘到 `.oaic/blobs/<hash>.txt`，in-memory 替换为 `[evicted: Read .oaic/blobs/<hash>.txt]`
  - 所有 user 文本消息与 assistant 消息（含 tool_calls 结构）**永不删除**
- **auto-compact**：超过阈值时 LLM 摘要 + 落盘完整 transcript 到 `.oaic/transcripts/`
- 阈值按**模型 context window 百分比**（默认 75%），而非硬编码 100k

### 4.4 `oai_code/session/` — 会话与持久化
- 项目根目录下自动创建 `.oaic/`：
  - `sessions/<id>.jsonl` — 会话历史
  - `tasks/task_*.json` — 持久化任务
  - `transcripts/` — auto-compact 触发后的完整记录
  - `blobs/<hash>.txt` — microcompact 外置的大 tool_result（见 §4.3）
  - `inbox/` — teammate 消息总线
  - `debug/` — `--debug-raw` 写入的未脱敏日志（见 §7.2）
- 支持 `oaic --resume <session-id>` 恢复

### 4.5 `oai_code/skills/` — Skills 机制
- 兼容 Claude Code 的 `SKILL.md` frontmatter 格式
- 启动时只加载 **name + description**，模型按需 `LoadSkill` 读正文
- 同时扫描 **项目级** `./skills/` 和 **用户级** `~/.oaic/skills/`

### 4.6 `oai_code/memory/` — 记忆文件
- 读取 `config.memory_files` 指定的所有文件（默认见 `CONFIG.md §3.4`）
- 项目级文件按数组顺序读取；用户级 `~/.oaic/CLAUDE.md` 固定**追加在数组末尾**（见 CONFIG.md 默认值）
- 按顺序拼到系统提示开头（与 Claude Code 语义一致）

### 4.7 `oai_code/mcp/` — MCP 客户端
- 通过 `.oaic/settings.json` 配置 MCP servers
- 启动时把 MCP 工具清单并入 tool registry
- 工具命名加前缀 `mcp__<server>__<tool>` 避免冲突
- **长度策略**：部分模型 / 网关限制 tool name ≤ 64 字符。拼接后超限时取 `mcp__<server>__<sha1(tool)[:8]>`，并在 registry 保存双向映射；向模型暴露的 description 里附原始名，便于人工排错

### 4.8 `oai_code/ui/` — 终端交互
- REPL：`rich.live.Live` 流式渲染 + `prompt_toolkit` 多行输入 / 历史 / 补全
- Slash 命令：`/compact` `/tasks` `/team` `/resume` `/clear` `/model` `/help`
- **中断语义**（两层）：
  - 一次 `Ctrl-C`：取消当前 in-flight HTTP 流 + 本地工具执行；若已产生 `tool_calls` 但尚未回灌 `tool_result`，为**每个未完成的 `tool_call_id` 补一条 `{role: "tool", tool_call_id: <id>, content: "[interrupted by user]"}`**，然后追加一条 `user: "<interrupted/>"` 让模型知晓；保持 messages 合法、避免「半条 assistant + 无 tool_result」的畸形历史
  - 两次 `Ctrl-C`（1s 内）：退出进程；`Ctrl-D` 同效

### 4.9 `oai_code/config/` — 配置系统
- **四级优先级**（高 → 低）：CLI flag > 项目 `.oaic/settings.json` > 用户 `~/.oaic/settings.json` > 环境变量
- 环境变量仅作**默认值来源**，不与 JSON 字段同级 merge；JSON 里缺失字段才 fallback 到 env
- **完整字段结构以 `CONFIG.md` 为真源**，本节不重复示例；DESIGN 与 CONFIG 冲突时以 CONFIG 为准

---

## 5. 核心数据流

**一轮对话**：
1. 用户输入 → 合并到 messages
2. Context Manager 跑 microcompact + 阈值检查 → 必要时 auto-compact
3. 拉取后台任务通知 / teammate inbox → 注入为 user message
4. 组装 system prompt（CLAUDE.md + skills 目录 + MCP 工具描述）
5. OpenAI SDK 流式调用 → 实时渲染 assistant 文本 + tool_calls
6. Tool Dispatcher 并行执行 tool_calls（I/O 密集可并发）→ 收集 tool_result
7. 把 tool_result 追加到 messages，回到第 2 步；直到 `finish_reason != "tool_calls"`

**关键不变式**：所有 tool 调用失败都转为字符串形式的 tool_result 回传，**不抛到 loop 外**，避免半截对话污染历史。

**并行 tool_calls 策略**（默认开启，按下列规则降级为串行）：
- 写同一文件路径的多个 `Write` / `Edit` / `Bash`（命令含重定向到同路径）→ 按出现顺序串行
- 任一工具是 `Bash` 且后续工具存在 `Read`/`Grep` 读同路径 → 串行
- 后台类（`BackgroundRun`、`SpawnTeammate`）与其余工具之间不串行化（它们本就异步）
- 其余情况走并发，最大并行度由 `config.parallel_tools`（默认 4）限制
- 提供全局开关 `config.serial_only = true` 兜底给 parallel tool calls 支持不稳的模型

---

## 6. OpenAI 兼容性与 Claude Code 语义的桥接

这是本项目的关键权衡，明确规则如下：

| 层面 | 策略 |
|------|------|
| **传输协议** | 严格用 OpenAI `tools` / `tool_calls` / `tool` role |
| **工具命名** | 采用 Claude Code 风格的 PascalCase（`Bash`、`Read`、`Edit`）|
| **参数 schema** | JSON Schema，字段名与 Claude Code 对齐（`file_path`、`old_string`、`new_string`）|
| **system prompt** | 语气与结构参考 Claude Code，但不照抄 |
| **流式语义** | OpenAI delta 格式，UI 层做增量拼装 |
| **并行工具调用** | 依赖模型原生支持（gpt-4o/deepseek-v3 等支持 parallel tool calls）|

这样做的好处：**用户能把现有的 `CLAUDE.md`、skills、MCP 配置几乎无缝迁移过来**，而我们不用碰 Anthropic SDK。

> **真源约束**：上表是方向，工具字段/错误格式/role 映射的最终规格以 `TOOLS.md` 为**唯一真源**；设计文档与 TOOLS.md 冲突时以后者为准。
>
> **关于 Responses API**：v1 仅封装 Chat Completions。Responses API 虽是 OpenAI 新方向，但大多数第三方兼容网关（DeepSeek / Qwen / OpenRouter / Ollama / vLLM / fenbi 内部网关）仍只实现 Chat Completions，过早抽象会增加分叉维护成本。待兼容生态迁移完成后再在 `llm/` 下增加 `responses_client.py`。
>
> **M3 复核（2026-04）**：维持原决策。当前流式已通过 `chat.completions.create(stream=True)` 实现；Responses API 独占能力（reasoning tokens / 官方托管工具 / 服务器侧会话 / background mode）对目前用户的主力 provider（fenbi）不可用。**触发条件**：当主要使用的后端开始透传 `/v1/responses` 端点时再做。

---

## 7. 安全边界与密钥处理

### 7.1 威胁模型（v1 立场）
- **仓库信任**：默认信任当前工作目录（允许 `git`、`npm`、`pip` 等），但所有 shell 命令仍受 `Bash` 的 deny-list + 超时约束
- **MCP 子进程**：启动时**只继承白名单环境变量**（`PATH`、`HOME`、`LANG`、`LC_*`，以及 `mcp_servers[*].env` 里显式声明的键），其余一律 drop。**不做 `*_API_KEY` 通配继承**——所有 API key 必须通过 `env` 字段的 `_env` 后缀规则显式声明（详见 `CONFIG.md §3.7`）
- **路径越界**：所有文件类工具走 `safe_path()`，拒绝 `denied_paths` 命中项（默认 `~/.ssh`、`~/.aws`、`~/.gnupg`、`.env*`）
- **权限标签**（预埋，v1 仅白名单实现）：每个工具声明 `requires: [exec | write | network | delegate]`（完整枚举见 `TOOLS.md §0.4`），为 M2+ 的 `allow/deny/ask` 三态留扩展点；开放问题 2 的结论并入此处

### 7.2 密钥与日志
- `api_key_env` 是唯一推荐方式；禁止在 settings.json 里明文写 key
- 写 session jsonl 前过一次**脱敏滤镜**：`Authorization`、`api_key`、`.env` 文件内容、`openai.api_key=` 形式一律替换为 `[REDACTED]`
- debug 日志默认脱敏；`--debug-raw` flag 才输出原文，仅写到 `.oaic/debug/` 且不随 session 走

---

## 8. 目录结构（v1 规划）

```
oai-code/
├── pyproject.toml
├── README.md
├── docs/
│   ├── DESIGN.md            # 本文件
│   ├── TOOLS.md             # 工具清单 spec
│   ├── CONFIG.md            # 配置字段与 provider profile
│   └── MIGRATION.md         # 从 Claude Code 迁移指南
├── src/oai_code/
│   ├── __main__.py
│   ├── cli.py               # argparse + REPL 入口
│   ├── config/
│   ├── llm/
│   │   ├── client.py        # OpenAI SDK 封装
│   │   └── providers.py     # 预置 provider profile
│   ├── agent/
│   │   ├── loop.py          # 主循环（对应 s01 + s_full）
│   │   └── system_prompt.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── builtin/         # Bash/Read/Edit/...
│   │   ├── todo.py          # s03
│   │   ├── subagent.py      # s04
│   │   ├── skills.py        # s05
│   │   ├── tasks.py         # s07
│   │   ├── background.py    # s08
│   │   └── team.py          # s09-s11
│   ├── context/
│   │   └── compact.py       # s06
│   ├── session/
│   ├── memory/
│   ├── mcp/
│   └── ui/
└── tests/
```

---

## 9. 路线图

**M0 — 骨架（1 周）**
- CLI 入口 + REPL + 流式渲染
- OpenAI Client + provider profile
- Bash / Read / Write / Edit / Glob / Grep 六个基础工具
- 简单 agent loop（对应 s01+s02）
- 跑通「看代码、改代码、执行命令」闭环

**M1 — 对齐 Claude Code（1-2 周）**
- TodoWrite + Tasks 持久化 + Subagent + Skills + CLAUDE.md 记忆
- 上下文 compact（micro + auto）
- 项目/用户双级配置
- **分角色模型**（对齐 Claude Code 静态分配策略）：
  - `roles.main`：主对话模型（用户选的 profile）—— 一次会话内不中途切换
  - `roles.summarize`：auto-compact / microcompact 摘要用（默认推荐小模型，如 `fenbi-mini`）
  - `roles.subagent`：Task 工具派发的子 agent（可与 main 相同，或显式指定）
  - 配置结构见 `CONFIG.md`（M1 开工时补充 `roles` 字段总表）
  - **不做动态路由**：不在 loop 中按任务难度切换模型（理由：KV cache 作废 / 风格跳变 / 工具协议差异；Claude Code 也未采用）

**M2 — 高级能力（1-2 周）**
- 后台任务 + 通知回流
- MCP 客户端接入
- Slash 命令完整集
- Session resume

**M3 — 可选**
- 多 agent teammate（s09-s11）
- Worktree 隔离（s12）
- MCP sse + http 传输（补齐 stdio 之外的两种）
- **退出时记忆总结**（显式触发）：
  - 命令形式：`/quit --summary` 或 `/exit-summary` slash
  - 总结目标：从当前 session 的 messages 里提炼"值得跨会话保留"的要点（决策、规范、用户偏好）
  - 使用模型：`roles.summarize`（复用 auto-compact 的小模型）
  - 写入位置：**追加**到 `.oaic/MEMORY.md`（不动用户手写的 `CLAUDE.md`）
  - 条目格式：带时间戳的 Markdown 块，便于后期人工审核删除
  - 默认行为：不主动触发，需用户显式指令
- 发布到 PyPI（包名 `oai-code`、CLI `oaic`；发布前需检索 PyPI 占用，结论**待确认**）

---

## 10. 质量与测试

| 层次 | 手段 | 触发时机 |
|------|------|---------|
| 工具 schema | `pytest` + JSON Schema 校验所有 builtin tool 的 input_schema 合法 | 每次 PR |
| LLM 协议 | 用 `respx` / `vcrpy` 录制各 provider 的 Chat Completions 响应 → snapshot 回放 | 每次 PR |
| 工具集成 | 每个 builtin 工具至少 1 条端到端用例（真实 tmpdir + 真实 shell） | 每次 PR |
| 黄金对话 | 固定几个 seed prompt（"读 README 并改一行"、"跑测试并修失败"），录制轨迹做回归对比 | M1 结束起每周跑 |
| 中断安全 | 单测覆盖 Ctrl-C 在 HTTP 流中 / 工具执行中 / 并行 tool_calls 中的 messages 合法性 | M0 结束必须过 |
| 脱敏 | 单测覆盖日志 / session 里 API key、`.env` 内容不外泄 | 每次 PR |

---

## 11. 开放问题（结论或待定）

1. **并行工具调用**：✅ **已决策** —— 默认并行 + 同路径串行规则（见 §5）；兜底开关 `serial_only`
2. **权限模型**：✅ **已决策** —— v1 走静态白名单（`allowed_tools` + `denied_paths`），工具预埋 `requires` 标签；`allow/deny/ask` 三态排到 M2
3. **多模态**：⏸ **v1 不做** —— `Read` 仅处理文本；PNG/PDF 返回 `[binary, N bytes]` 占位。M3 评估
4. **Windows 支持**：⏸ **v1 只保证 macOS/Linux** —— Bash 工具不封装 PowerShell；Windows 用户走 WSL

---

## 12. 文档权威矩阵

| 主题 | 真源文件 |
|------|---------|
| 工具名、schema、tool_result 格式、错误串前缀 | `TOOLS.md` |
| 配置字段、加载顺序、provider profile、CLI flag | `CONFIG.md` |
| 架构、agent loop、并行/中断策略、威胁模型、测试策略 | `DESIGN.md`（本文件） |

任一文档与真源文件冲突时，**以真源为准**，同时提 PR 修正冲突文档。

---

> **下一步**：进入 M0 骨架实现（见 §9 路线图）。
