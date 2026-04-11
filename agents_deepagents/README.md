# LangChain-Native Deep Agents s01-s06 Teaching Track

This directory is the parallel LangChain/Deep Agents track for the first
milestone of the course. The original `agents/*.py` files remain the
hand-written Anthropic SDK baseline; these files preserve the original
chapters' meaningful behavior while letting each `sNN` file use the most
natural LangChain-native implementation for that lesson.

`s06_context_compact.py` extends the track with a tutorial-only context
compression chapter that structurally models Claude Code / `cc-haha`'s
pre-request compaction pipeline using LangChain/LangGraph-style state and
deterministic summarizer callables. It is intentionally honest about where the
public cc-haha source is strong enough to mirror stage order directly and where
the teaching track must infer an equivalent.

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
- After review, the current `s01-s06` file names still describe the dominant
  behavior of each chapter well enough to keep the chapter shell useful.

## Chapter Map

| Original baseline | Current track | Dominant LangChain-native shape | Behavior preserved |
|---|---|---|---|
| `agents/s01_agent_loop.py` | `agents_deepagents/s01_agent_loop.py` | Minimal `create_agent_runtime(...)` loop with no future capabilities exposed early | Minimal loop + turn-by-turn interaction |
| `agents/s02_tool_use.py` | `agents_deepagents/s02_tool_use.py` | Thin invoke wrapper plus `ToolUseMiddleware`; no custom tool state | File/tool growth without rewriting the loop |
| `agents/s03_todo_write.py` | `agents_deepagents/s03_todo_write.py` | Tutorial-shaped planning state (`items`, `rounds_since_update`) plus middleware-driven `write_plan` updates and direct terminal rendering helpers | Visible session planning state |
| `agents/s04_subagent.py` | `agents_deepagents/s04_subagent.py` | Deep Agents `SubAgentMiddleware` maps original `run_subagent(prompt)` to `task(description, subagent_type)` with fresh child message context and summary-only return | Subagents as context isolation |
| `agents/s05_skill_loading.py` | `agents_deepagents/s05_skill_loading.py` | Deep Agents `SkillsMiddleware` advertises skill metadata; `read_file` loads `SKILL.md` only on demand | Discover light, load deep |
| `agents/s06_context_compact.py` | `agents_deepagents/s06_context_compact.py` | Explicit six-stage context compaction pipeline (`apply_tool_result_budget -> snip_projection -> microcompact_messages -> context_collapse -> auto_compact_if_needed -> reactive_compact_on_overflow`) with deterministic summarizer injection | Context compression, persistence, and overflow recovery disclosure |
## Disclosure Status

`s01-s05` currently record no intentional nonessential drops. `s06` is
different: it teaches the public cc-haha context-compaction shape with explicit
source-backed vs inferred stage labels instead of implying hidden internal
parity by default.

### s06 parity map

The `s06_context_compact.py` chapter and its README disclosure intentionally use
the same stage names that the module exposes through
`SOURCE_BACKED_STAGES`, `INFERRED_STAGES`, and
`INTENTIONAL_SIMPLIFICATIONS`.

| s06 stage | Classification | Why |
|---|---|---|
| `apply_tool_result_budget` | Source-backed | Public `toolResultStorage.ts` shows persisted-output previews, per-tool replacement, and aggregate fresh-result budgeting. |
| `snip_projection` | Inferred equivalent | Public cc-haha references a `snipCompact` / history-snip projection, but the hidden implementation details are not fully available in the fetched source tree. |
| `microcompact_messages` | Source-backed | Public `microCompact.ts` exposes compactable tool classes, age/retention behavior, and boundary messaging. |
| `context_collapse` | Inferred equivalent | Public `query.ts` shows when staged context collapse is consulted, but not the full collapse internals, so the teaching track uses a disclosed LangChain-style summary equivalent. |
| `auto_compact_if_needed` | Source-backed with teaching simplifications | Public `autoCompact.ts` exposes thresholding and summary-budget concepts; the tutorial keeps those ideas but omits production-only session-memory and telemetry machinery. |
| `reactive_compact_on_overflow` | Source-backed recovery order | Public `query.ts` shows prompt-too-long recovery draining staged collapse before falling back to reactive compact. |

### s06 intentional simplifications

The tutorial chapter keeps the stage order but deliberately does **not**
implement several production-only concerns. These omissions should stay visible
in both code metadata and docs:

- no real Anthropic cache-edit persistence or prompt-cache-sharing fork
- no GrowthBook/feature flags or telemetry hooks
- no full session-memory extraction pipeline
- no exact hidden `snipCompact` / `contextCollapse` internals where public
  source is missing
- deterministic summarizer injection and approximate token/size accounting
  instead of provider-specific runtime behavior

## Run

```sh
python agents_deepagents/s01_agent_loop.py
python agents_deepagents/s02_tool_use.py
python agents_deepagents/s03_todo_write.py
python agents_deepagents/s04_subagent.py
python agents_deepagents/s05_skill_loading.py
python agents_deepagents/s06_context_compact.py
```

Automated tests compile the files and import pure helpers only; they do not use
`OPENAI_API_KEY` and do not make network calls.
