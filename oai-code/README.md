# oai-code

OpenAI-compatible coding agent CLI — a Claude Code alternative that talks to any OpenAI-compatible backend (OpenAI / DeepSeek / Qwen / OpenRouter / Ollama / vLLM / self-hosted gateways).

> **Status**: M0 skeleton — core agent loop + 6 built-in tools (Bash/Read/Write/Edit/Glob/Grep).

## Quick start

```bash
uv sync
uv run oaic --help
```

See `docs/DESIGN.md`, `docs/TOOLS.md`, `docs/CONFIG.md` for the full spec.
