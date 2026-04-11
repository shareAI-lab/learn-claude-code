# LangChain-Native Deep Agents s01-s05 Teaching Track

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
  `Command(update=...)` plus middleware. Its display path now uses a tiny
  renderer-first seam while preserving the terminal output and avoiding
  browser/API/event-bus scope.
- After review, the current `s01-s05` file names still describe the dominant
  behavior of each chapter well enough to keep the chapter shell useful.

## Chapter Map

| Original baseline | Current track | Dominant LangChain-native shape | Behavior preserved |
|---|---|---|---|
| `agents/s01_agent_loop.py` | `agents_deepagents/s01_agent_loop.py` | Minimal `create_agent_runtime(...)` loop with no future capabilities exposed early | Minimal loop + turn-by-turn interaction |
| `agents/s02_tool_use.py` | `agents_deepagents/s02_tool_use.py` | Thin invoke wrapper plus `ToolUseMiddleware`; no custom tool state | File/tool growth without rewriting the loop |
| `agents/s03_todo_write.py` | `agents_deepagents/s03_todo_write.py` | Tutorial-shaped planning state (`items`, `rounds_since_update`) plus middleware-driven `write_plan` updates and direct terminal rendering helpers | Visible session planning state |
| `agents/s04_subagent.py` | `agents_deepagents/s04_subagent.py` | Deep Agents `SubAgentMiddleware` maps original `run_subagent(prompt)` to `task(description, subagent_type)` with fresh child message context and summary-only return | Subagents as context isolation |
| `agents/s05_skill_loading.py` | `agents_deepagents/s05_skill_loading.py` | Deep Agents `SkillsMiddleware` advertises skill metadata; `read_file` loads `SKILL.md` only on demand | Discover light, load deep |
## Disclosure Status

This README currently records no intentional nonessential drops for `s01-s05`.
If a later chapter needs to omit nonessential behavior, record that fact in the
chapter report or this README instead of implying full parity by default.

## Run

```sh
python agents_deepagents/s01_agent_loop.py
python agents_deepagents/s02_tool_use.py
python agents_deepagents/s03_todo_write.py
python agents_deepagents/s04_subagent.py
python agents_deepagents/s05_skill_loading.py
```

Automated tests compile the files and import pure helpers only; they do not use
`OPENAI_API_KEY` and do not make network calls.
