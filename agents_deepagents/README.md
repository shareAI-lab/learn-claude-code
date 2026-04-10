# LangChain-Native Deep Agents s01-s11 Teaching Track

This directory is the parallel LangChain/Deep Agents track for the first
milestone of the course. The original `agents/*.py` files remain the
hand-written Anthropic SDK baseline; these files preserve the original
chapters' meaningful behavior while letting each `sNN` file use the most
natural LangChain-native implementation for that lesson.

The web UI does not surface this directory yet. Read and run these files from
the terminal.

## Migration Policy

- Preserve original project functionality before preserving tutorial-internal
  mechanism boundaries.
- Prefer natural LangChain / Deep Agents primitives over line-by-line tutorial
  fidelity.
- Keep the `sNN` chapter shell only while it remains a useful navigation aid.
- If a chapter intentionally drops nonessential behavior, document that drop
  explicitly instead of silently shrinking the feature.

## Environment

Configure the Deep Agents track with OpenAI-style variables:

```sh
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini        # optional; defaults to gpt-4.1-mini
OPENAI_BASE_URL=https://...      # optional OpenAI-compatible endpoint
```

`OPENAI_MODEL` is preferred for this track. `MODEL_ID` is accepted only as a
compatibility fallback if you already use the original `.env` file.

## Current Anchors

- `s02` is the current **state-light** example: a thin tool-use wrapper with
  normalized input and middleware, but no custom tool-use state object.
- `s03` is the current **naturally stateful** example: planning lives in
  explicit LangChain state (`PlanningState`) and is updated through
  `Command(update=...)` plus middleware.
- After review, the current `s01-s11` file names still describe the dominant
  behavior of each chapter well enough to keep the chapter shell useful.

## Chapter Map

| Original baseline | Current track | Dominant LangChain-native shape | Behavior preserved |
|---|---|---|---|
| `agents/s01_agent_loop.py` | `agents_deepagents/s01_agent_loop.py` | Minimal `create_agent_runtime(...)` loop with no future capabilities exposed early | Minimal loop + turn-by-turn interaction |
| `agents/s02_tool_use.py` | `agents_deepagents/s02_tool_use.py` | Thin invoke wrapper plus `ToolUseMiddleware`; no custom tool state | File/tool growth without rewriting the loop |
| `agents/s03_todo_write.py` | `agents_deepagents/s03_todo_write.py` | Explicit `PlanningState` + `todo` tool + middleware-driven `Command(update=...)` | Visible session planning state |
| `agents/s04_subagent.py` | `agents_deepagents/s04_subagent.py` | Parent tool spawns a child agent with fresh context and returns a short summary | Subagents as context isolation |
| `agents/s05_skill_loading.py` | `agents_deepagents/s05_skill_loading.py` | Lightweight prompt catalog plus on-demand `load_skill` retrieval | Discover light, load deep |
| `agents/s06_context_compact.py` | `agents_deepagents/s06_context_compact.py` | Harness-level compaction, persisted tool output, transcript summaries | Compaction keeps continuity while shrinking active context |
| `agents/s07_permission_system.py` | `agents_deepagents/s07_permission_system.py` | Explicit permission pipeline around tool execution | Safety remains a staged gate between intent and action |
| `agents/s08_hook_system.py` | `agents_deepagents/s08_hook_system.py` | Hook behavior mapped onto middleware around tool calls | Extension points without rewriting the loop |
| `agents/s09_memory_system.py` | `agents_deepagents/s09_memory_system.py` | File-backed memory plus middleware-injected prompt context | Durable cross-session memory stays explicit |
| `agents/s10_system_prompt.py` | `agents_deepagents/s10_system_prompt.py` | Prompt builder for stable sections plus dynamic-context middleware | System prompt is an assembly pipeline, not one string |
| `agents/s11_error_recovery.py` | `agents_deepagents/s11_error_recovery.py` | Retry middleware + auto-compaction fallback | Recover cleanly from long context and transient failures |

## Disclosure Status

This README currently records no intentional nonessential drops for `s01-s11`.
If a later chapter needs to omit nonessential behavior, record that fact in the
chapter report or this README instead of implying full parity by default.

## Run

```sh
python agents_deepagents/s01_agent_loop.py
python agents_deepagents/s02_tool_use.py
python agents_deepagents/s03_todo_write.py
python agents_deepagents/s04_subagent.py
python agents_deepagents/s05_skill_loading.py
python agents_deepagents/s06_context_compact.py
python agents_deepagents/s07_permission_system.py
python agents_deepagents/s08_hook_system.py
python agents_deepagents/s09_memory_system.py
python agents_deepagents/s10_system_prompt.py
python agents_deepagents/s11_error_recovery.py
```

Automated tests compile the files and import pure helpers only; they do not use
`OPENAI_API_KEY` and do not make network calls.
