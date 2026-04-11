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
- `s06` is the current **context compression parity** example: a
  LangChain/LangGraph-shaped teaching pipeline that keeps Claude Code /
  `cc-haha` compression stages visible as pure, testable transforms.
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
| `agents/s06_context_compact.py` | `agents_deepagents/s06_context_compact.py` | Single-file context-compression state pipeline with explicit stage boundaries, summaries, and overflow recovery | Visible `cc-haha`-informed compression order without hiding it behind one middleware call |

## Disclosure Status

### s06 source evidence vs inference

The `s06_context_compact.py` chapter is intentionally honest about which parts
of Claude Code / `cc-haha` are visible in the public source tree and which
parts must be taught as LangChain-native equivalents.

| s06 stage | Status | Public cc-haha evidence | Tutorial disclosure |
|---|---|---|---|
| `apply_tool_result_budget` | Source-backed | [`src/query.ts#L365-L398`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L365-L398), [`src/utils/toolResultStorage.ts#L137-L225`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/utils/toolResultStorage.ts#L137-L225), [`src/utils/toolResultStorage.ts#L739-L909`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/utils/toolResultStorage.ts#L739-L909) | The tutorial keeps persisted-output previews and stable replacement decisions visible in state. |
| `snip_projection` | Inferred equivalent | [`src/query.ts#L398-L407`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L398-L407) plus feature-gated `snipCompact` references noted in the spec | The public tree shows where snip runs, but not the full implementation, so the tutorial models a projection without claiming exact reproduction. |
| `microcompact_messages` | Source-backed | [`src/query.ts#L408-L417`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L408-L417), [`src/services/compact/microCompact.ts#L40-L50`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/services/compact/microCompact.ts#L40-L50), [`src/services/compact/microCompact.ts#L253-L530`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/services/compact/microCompact.ts#L253-L530) | The tutorial keeps compactable-tool clearing and boundary metadata, but uses deterministic local state instead of production cache-edit plumbing. |
| `context_collapse` | Inferred equivalent | [`src/query.ts#L428-L447`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L428-L447), [`src/query.ts#L1084-L1118`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L1084-L1118) | The tutorial preserves tool-use/result group integrity and staged summaries, but does not claim access to hidden `contextCollapse` internals. |
| `auto_compact_if_needed` | Source-backed | [`src/query.ts#L448-L467`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L448-L467), [`src/services/compact/autoCompact.ts#L28-L90`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/services/compact/autoCompact.ts#L28-L90), [`src/services/compact/autoCompact.ts#L147-L350`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/services/compact/autoCompact.ts#L147-L350) | The tutorial teaches threshold-driven compaction to summary + recent context without reproducing every production branch. |
| `reactive_compact_on_overflow` | Source-backed | [`src/query.ts#L1084-L1165`](https://github.com/NanmiCoder/cc-haha/blob/5fa3247f9fa3ddde462185218f7e73b2dccfc956/src/query.ts#L1084-L1165) | The tutorial keeps the collapse-drain-first recovery order explicit and testable. |

### Intentional s06 simplifications

To keep the tutorial deterministic and no-live-API, `s06` intentionally does
not model:

- real Anthropic cache edits,
- GrowthBook / feature flags / telemetry,
- prompt-cache-sharing fork behavior,
- full session-memory extraction, or
- the exact hidden `snipCompact` / `contextCollapse` internals that were not
  visible in the fetched public tree.

Those omissions are deliberate teaching boundaries, not accidental parity gaps.

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
