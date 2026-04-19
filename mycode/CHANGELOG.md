# Changelog

All notable changes to mycode are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-04

First public release. Covers M0 through M5; 241+ tests passing.

### Added

**M0 — Core skeleton**
- CLI entry `mycode` with REPL + one-shot (`-p`) + resume (`--resume`) modes.
- OpenAI Chat Completions streaming via the official `openai` SDK (`chat.completions.create`).
- 7 pre-configured provider profiles (openai / deepseek / qwen / openrouter / ollama / vllm / custom) plus 4 fenbi gateway shortcuts.
- Six built-in tools: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`.
- Four-level config loading: env → user → project → `--config` / `MYCODE_CONFIG` → CLI flags. Pydantic validation, fail-fast.
- Parallel tool calls with same-path serialization; Ctrl-C interrupt preserves `messages` integrity.

**M1 — Claude Code feature parity**
- `TodoWrite` short-term checklist; `/todos` slash.
- Persistent `TaskCreate` / `TaskGet` / `TaskUpdate` / `TaskList` under `.mycode/tasks/`; cascade unblock on completion; `/tasks` slash.
- `Task` subagent tool with Explore / Plan / general-purpose whitelists.
- `LoadSkill` + SKILL.md discovery from `skills_dirs`.
- `CLAUDE.md` / `AGENTS.md` memory with `@ref` expansion and cycle protection.
- microcompact (evict large tool_result to `.mycode/blobs/`) and auto-compact (summarize with `roles.summarize` → `.mycode/transcripts/`).
- Role-based models: `roles.main` / `roles.summarize` / `roles.subagent`.

**M2 — Long-running workflows**
- Session persistence: `.mycode/sessions/<id>.jsonl` appended per turn; redacted before write; `--resume <id|latest>`; `--list-sessions`; `/sessions` / `/resume` / `/save`.
- `BackgroundRun` / `BackgroundCheck` with notification queue; loop drains into `<background-results>` user message.
- MCP stdio client; dynamic tool registration as `mcp__<server>__<tool>`; SHA-1 name shortening over 64 chars; `_env` suffix rule for secret injection.
- Slash command suite: `/help`, `/clear`, `/compact`, `/tools`, `/todos`, `/tasks`, `/bg`, `/mcp`, `/models [id]`, `/provider <name>`, `/sessions`, `/resume`, `/save`, `/debug`, `/system`, `/history [N]`, `/quit`.

**M3 — Ecosystem and team**
- MCP sse + streamable-http transports; `headers` supports the same `_env` rule as `env`.
- Exit-time summary: `/exit-summary` or `/quit --summary` → `.mycode/MEMORY.md` (append-only, never overwrites `CLAUDE.md`).
- Multi-agent teammates (s09): file-backed inbox under `.team/inbox/*.jsonl`, append-only + drain-on-read; `TeammateManager` roster.
- Team tools (s09): `SpawnTeammate` / `SendMessage` / `Broadcast` / `ReadInbox` / `ListTeammates`; per-teammate agent loop in its own thread.
- Team protocols (s10): `ShutdownRequest` + `PlanApproval` with `request_id` handshake state machine.
- Autonomy (s11): teammates poll `.mycode/tasks/` during IDLE and auto-claim unblocked tasks; identity re-injection after compact.
- PyPI packaging metadata: classifiers, LICENSE (MIT), project URLs, `uv build` produces wheel + sdist; `docs/PUBLISH.md`.

**M4 — Quality and ergonomics**
- Teammate `auto_compact` support: long teammate conversations no longer exceed context window.
- `BackgroundKill` tool + `Popen`/`killpg` refactor: background tasks can be terminated (process group, not just shell).
- `AskUserQuestion` tool: agent can ask the user 1–4 questions (2–4 options each) and block for an answer; graceful fallback in non-interactive mode.
- `MultiEdit` tool: multiple edits on one file, atomic (all succeed or file is untouched), cascade semantics (later edits see earlier results).
- `Plan Mode`: `EnterPlanMode` / `ExitPlanMode`; dispatcher gates write / exec / delegate tools while active; `ExitPlanMode` routes through `AskUserQuestion` for user approval.
- `WebFetch` tool: pulls `http`/`https` URLs, strips HTML tags/scripts, 2 MiB / 30 s limits.

**M5 — Isolation, coverage, release**
- Worktree isolation: `EnterWorktree` / `ExitWorktree` / `WorktreeStatus` back a git worktree under `.mycode/worktrees/<name>/`; `workspace_root` swaps via a PrivateAttr (no `os.chdir`); `state.json` enables resume across restarts.
- MCP real end-to-end tests: a `FastMCP`-based stub server is launched as a stdio subprocess and exercised through `list_tools` + `call_tool` + registry injection.
- Teammate loop end-to-end regression: `respx`-mocked OpenAI responses drive full WORK → IDLE → wake-up → shutdown / auto-claim flows in threads.
- UI polish: per-tool elapsed-time display, `✓/✗` status icons, dedicated `TodoWrite` renderer with `●/○/✓` markers.
- First public release version `0.1.0`; PyPI name `mycode` confirmed available at time of publish.

### Notes

- This is a pre-1.0 release. APIs in `src/mycode/` may still change without deprecation. The tool names and schemas in `docs/TOOLS.md` are the stable contract for LLM interaction.
- Windows: works under WSL / Git Bash; native `cmd.exe` behaviour is best-effort (no integration tests).
- Only Chat Completions is supported. The OpenAI Responses API is intentionally not wired up yet; see `docs/DESIGN.md` §6 for the rationale.

### Dependencies

Runtime: `openai>=1.30`, `pydantic>=2.6`, `rich>=13.7`, `prompt_toolkit>=3.0`, `python-dotenv>=1.0`, `pyyaml>=6.0`, `mcp>=1.27.0`.

Dev: `pytest>=8.0`, `pytest-asyncio>=0.23`, `respx>=0.21`.
