# oai-code

基于 OpenAI 兼容协议的命令行编码 Agent —— 一个 Claude Code 替代品，可对接任意 OpenAI 兼容后端（OpenAI / DeepSeek / Qwen / OpenRouter / Ollama / vLLM / 自建网关等）。

> **当前状态**：M0 骨架 —— 核心 agent loop + 6 个内置工具（Bash / Read / Write / Edit / Glob / Grep）。

## 快速开始

```bash
# 安装依赖（首次）
uv sync

# 查看命令行帮助
uv run oaic --help

# 交互式 REPL（需要先配好 API key，见 .env.example）
uv run oaic --provider fenbi

# 单次执行模式
uv run oaic --provider fenbi -p "总结一下 README.md"
```

## 配置

最小配置示例（`~/.oaic/settings.json`）：

```json
{
  "provider": "deepseek",
  "api_key_env": "DEEPSEEK_API_KEY"
}
```

支持的 provider profile：`openai` / `deepseek` / `qwen` / `openrouter` / `ollama` / `vllm` / `fenbi` / `custom`。

完整字段说明见 [`docs/CONFIG.md`](./docs/CONFIG.md)。

## 文档

- [`docs/DESIGN.md`](./docs/DESIGN.md) —— 架构、Agent Loop、并行与中断策略、威胁模型、测试策略
- [`docs/TOOLS.md`](./docs/TOOLS.md) —— 工具规格（真源）：所有工具的 name / schema / tool_result / 错误串格式
- [`docs/CONFIG.md`](./docs/CONFIG.md) —— 配置字段总表、四级加载顺序、provider profile、CLI flag

## 路线图

- **M0** ✅ CLI + REPL + 流式渲染 + 6 个基础工具 + 四级配置 + 27 个测试
- **M1** TodoWrite / 持久化任务 / Subagent / Skills / 上下文压缩 / CLAUDE.md 记忆
- **M2** 后台任务 / MCP 客户端 / Session resume / Slash 命令完整集
- **M3** 多 Agent 协作 / Worktree 隔离 / 发布 PyPI
