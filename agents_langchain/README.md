# LangChain teaching track (`s01-s06`)

This directory is the parallel LangChain/OpenAI-interface track for the first
six chapters of the repository. It is a comparison track, not a replacement for
the original hand-written baseline in `agents/`.

The milestone boundary is intentionally small:

- included now: `s01` through `s06`
- not included yet: `s07` through `s19`
- not changed here: the web learning app under `web/`

## Why this lives outside `agents/`

The original `agents/*.py` files teach the harness mechanics directly: model
turns, tool dispatch, todo state, subagent context isolation, skill discovery,
and context compaction. The LangChain track keeps those files untouched so you
can compare:

- what the hand-written harness owns
- what LangChain now owns
- what state still has to remain visible in the surrounding teaching code

Keeping the track in `agents_langchain/` also prevents the current web extractor
from treating the comparison scripts as mainline chapters before the web UI has
an explicit LangChain milestone.

## Environment

Install the normal Python requirements:

```sh
pip install -r requirements.txt
```

For manual LangChain demo runs, configure the OpenAI-compatible variables in
`.env`:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.2
# OPENAI_BASE_URL=https://api.openai.com/v1
```

Rules for this track:

- `OPENAI_API_KEY` is required only when you actually run a live LangChain demo.
- `OPENAI_BASE_URL` is optional and is for OpenAI-compatible endpoints.
- `OPENAI_MODEL` is the preferred model variable for this track.
- If a script also accepts the repo-wide `MODEL_ID` for compatibility,
  `OPENAI_MODEL` should take precedence.
- Automated tests must not require `OPENAI_API_KEY` and must not make network
  calls.

The package choice follows the current LangChain Python installation guidance:
the core `langchain` package plus the OpenAI provider integration
`langchain-openai`.

## Chapter map

| Original baseline | LangChain comparison | What to compare |
|---|---|---|
| `agents/s01_agent_loop.py` | `agents_langchain/s01_agent_loop.py` | Which parts of `messages -> model -> tool_result -> next turn` remain visible when LangChain owns model/tool plumbing |
| `agents/s02_tool_use.py` | `agents_langchain/s02_tool_use.py` | How adding tools expands the dispatch surface without rewriting the loop |
| `agents/s03_todo_write.py` | `agents_langchain/s03_todo_write.py` | Which planning state stays in explicit harness code instead of disappearing into model text |
| `agents/s04_subagent.py` | `agents_langchain/s04_subagent.py` | How a child agent keeps fresh messages and returns a bounded summary |
| `agents/s05_skill_loading.py` | `agents_langchain/s05_skill_loading.py` | How cheap skill discovery and on-demand full loading map into LangChain tools |
| `agents/s06_context_compact.py` | `agents_langchain/s06_context_compact.py` | How compaction remains a harness-owned context operation around LangChain calls |

## Reading order

Read each LangChain file side-by-side with its original baseline:

1. Open the original `agents/sXX_*.py`.
2. Identify the state structure and the path that advances one turn.
3. Open the matching `agents_langchain/sXX_*.py`.
4. Look for comments or code blocks that explain:
   - what LangChain owns now
   - what the surrounding harness still owns
   - what is intentionally left as explicit teaching state
5. Run the script manually only after setting the OpenAI-compatible environment.

## Review checklist for this track

Use this checklist when reviewing new or changed LangChain examples:

- `agents/s01_agent_loop.py` through `agents/s06_context_compact.py` remain
  unchanged as the baseline.
- The LangChain examples do not instantiate a live model at import time.
- Pure helpers remain importable without `OPENAI_API_KEY`.
- Tests compile or exercise pure helpers only; they do not call the live model.
- The scripts document when LangChain owns a loop/tool behavior that the
  original baseline implements by hand.
- `web/` remains untouched for this milestone.
- s01-s06 remain teaching examples, not a production agent framework.
