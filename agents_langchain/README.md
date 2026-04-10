# LangChain s01-s06 Teaching Track

This directory is a parallel comparison track for the first milestone.  It does
not replace the original `agents/*.py` Anthropic SDK teaching baseline, and it is
not surfaced by the current web UI.

## What changed vs. `agents/`

| Original baseline | LangChain comparison | Teaching focus |
|---|---|---|
| `agents/s01_agent_loop.py` | `agents_langchain/s01_agent_loop.py` | visible model -> tool -> result loop with `ChatOpenAI.bind_tools` |
| `agents/s02_tool_use.py` | `agents_langchain/s02_tool_use.py` | expanding tool dispatch with LangChain tools |
| `agents/s03_todo_write.py` | `agents_langchain/s03_todo_write.py` | keeping session planning state outside the model |
| `agents/s04_subagent.py` | `agents_langchain/s04_subagent.py` | fresh child-agent context with summary-only return |
| `agents/s05_skill_loading.py` | `agents_langchain/s05_skill_loading.py` | discover skill summaries, load full skill bodies on demand |
| `agents/s06_context_compact.py` | `agents_langchain/s06_context_compact.py` | compaction policy remains harness-owned around LangChain |

## OpenAI-compatible configuration

The LangChain track uses OpenAI-interface chat models through
`langchain-openai`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5
# Optional for OpenAI-compatible endpoints:
# OPENAI_BASE_URL=https://api.openai.com/v1
```

Model precedence is `OPENAI_MODEL` first, then `MODEL_ID` only when it does not
look like the Anthropic default (`claude-*`), and finally `gpt-5`.  This keeps an
existing `.env` for the original Anthropic demos from silently becoming the
LangChain track's default.

## Run a demo

Install dependencies and configure the OpenAI-compatible variables first:

```sh
pip install -r requirements.txt
cp .env.example .env
python agents_langchain/s01_agent_loop.py
python agents_langchain/s06_context_compact.py
```

Automated tests compile and inspect pure helpers only; they do not call a live
LLM and do not require `OPENAI_API_KEY`.
