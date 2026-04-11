# coding-deepgent

Independent cumulative LangChain/Deep Agents project state through the confirmed `s03` milestone.


## Current architecture

- LangChain remains the runtime boundary: `PlanningState`, `PlanningMiddleware`, tools, and `Command(update=...)` own agent behavior.
- Planning display is renderer-first: `coding_deepgent.renderers.planning` owns the terminal-compatible plan/reminder rendering seam, while tool and middleware code call that seam.
- This pass intentionally does **not** add FastAPI, browser UI, plugin loading, or a generic event bus; future UI work should start from `PlanningState.items` and a new display/API plan.
