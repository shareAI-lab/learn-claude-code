# coding-deepgent

Independent cumulative LangChain cc product surface.

## Current product stage

- `current_product_stage`: `stage-1-todowrite-foundation`
- `compatibility_anchor`: `s03` planning/filesystem foundation
- Upgrade policy: advance by explicit product-stage plan approval, not tutorial chapter completion.

## Current architecture

- LangChain remains the runtime boundary: `PlanningState`, planning middleware, tools, and `Command(update=...)` own agent behavior.
- The public planning contract is now cc-aligned `TodoWrite(todos=[...])` with required `activeForm` on every todo item.
- Planning display is renderer-first: `coding_deepgent.renderers.planning` owns the terminal-compatible plan/reminder rendering seam, while tool and middleware code call that seam.
- Stage 1 intentionally does **not** add subagents, skills, context compaction, FastAPI, browser UI, plugin loading, or a generic event bus.
