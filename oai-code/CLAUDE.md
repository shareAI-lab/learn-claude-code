# oai-code 项目记忆

> 每次启动 oaic 时会自动注入到 system prompt。写在这里的内容 = Agent 每轮对话时都记住的背景。

## 项目定位

- **oai-code** 是一个基于 OpenAI 兼容协议的命令行编码 Agent（Claude Code 替代品）
- 通过 `base_url` 切换后端（OpenAI / DeepSeek / Qwen / Ollama / vLLM / 自建网关 fenbi 等）
- 主用 Python 3.10+，依赖管理用 `uv`
- 当前里程碑：M2 完成（103 tests），M3 未动工

## 目录约定

```
oai-code/
├── src/oai_code/          源码
│   ├── cli.py              入口 + argparse
│   ├── agent/              loop / dispatcher / system_prompt
│   ├── tools/              6 基础工具 + subagent/todo/tasks/skills/background/compact
│   ├── config/             四级合并加载 + Pydantic models
│   ├── llm/                OpenAI SDK 封装 + provider profiles
│   ├── context/            micro/auto-compact
│   ├── memory/             CLAUDE.md / @ref 展开
│   ├── session/            .oaic/sessions/*.jsonl 落盘
│   ├── mcp/                stdio 客户端(M2,仅 stdio)
│   └── ui/                 REPL
├── tests/                  103 tests(pytest)
├── docs/
│   ├── DESIGN.md           架构真源
│   ├── TOOLS.md            工具 schema 真源
│   ├── CONFIG.md           配置字段真源
│   └── milestones/         M0/M1/M2 各有 溯源 + 验收 两份
└── .oaic/                  运行时产物(sessions/blobs/transcripts/tasks)
```

## 开发规范

- **改代码后必须跑** `uv run pytest -q`，保证 103/103 通过再提交
- **工具错误串**统一以 `"Error:"` 开头（见 TOOLS.md §7）
- **文件类工具**必须走 `src/oai_code/tools/safety.py::safe_path` 审计
- **日志/session 落盘前**走 `redact` 脱敏
- **新工具 schema** 必须在 `docs/TOOLS.md` 同步登记
- **commit message** 前缀用 `ADD:` / `MOD:` / `FIX:` 三种，不加 Co-authored-by trailer

## 关键不变式

- Agent Loop 里任何工具失败都转 `"Error: ..."` 字符串回灌 tool_result，**不抛到 loop 外**
- 同路径 Write/Edit 在 dispatcher 里**强制串行**，不受 parallel_tools 影响
- Ctrl-C 中断时为每个未完成的 `tool_call_id` 补 `[interrupted by user]`，保 messages 合法
- Session 每轮追加写盘，不是退出时一次性写
- microcompact 在每轮 LLM 调用**之前**跑，keep 最近 3 条 tool_result，其余 >4 KiB 外置到 `.oaic/blobs/`

## 真源文档（术语与字段的唯一来源）

- 工具 name/schema/tool_result/错误串 → **`docs/TOOLS.md`**
- 配置字段/加载顺序/provider profile/CLI flag → **`docs/CONFIG.md`**
- 架构/Agent Loop/并行策略/威胁模型/测试矩阵 → **`docs/DESIGN.md`**

三份冲突时以真源为准，同步提 PR 修正其他文档。

## 记忆机制(本文件的更新规则)

- **目前**：本文件 `CLAUDE.md` 只由人手写 / 人修改，oaic 启动时只读不写
- **M3 规划**：新增 `/quit --summary` 和 `/exit-summary` slash，显式触发后由 `roles.summarize` 小模型从当前 session 提炼要点，**追加**到 `.oaic/MEMORY.md`（不写 CLAUDE.md）
- **原则**：机器自动产出与人手写分开存放；默认不主动总结，用户显式要求才触发

## 目前的里程碑边界

- **M0 ✅**：CLI + REPL + 6 基础工具 + 四级配置
- **M1 ✅**：Memory / TodoWrite / Tasks / Subagent / Skills / Compact + Roles
- **M2 ✅**：Session 持久化 / BackgroundRun / MCP stdio / Slash 完整集
- **M3 ⏳**：多 Agent teammate / Worktree 隔离 / MCP sse+http / **退出总结写 MEMORY.md** / PyPI 发布
