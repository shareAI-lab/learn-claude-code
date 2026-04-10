# Deep Agents s01-s06 Teaching Track

This directory is the parallel Deep Agents track for the first milestone of the
course. The original `agents/*.py` files remain the hand-written Anthropic SDK
baseline; these files retell the same `s01-s06` lessons through a staged Deep
Agents harness.

The web UI does not surface this directory yet. Read and run these files from
the terminal.

## Environment

Configure the Deep Agents track with OpenAI-style variables:

```sh
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini        # optional; defaults to gpt-4.1-mini
OPENAI_BASE_URL=https://...      # optional OpenAI-compatible endpoint
```

`OPENAI_MODEL` is preferred for this track. `MODEL_ID` is accepted only as a
compatibility fallback if you already use the original `.env` file.

## Chapter Map

| Original baseline | Deep Agents track | Lesson |
|---|---|---|
| `agents/s01_agent_loop.py` | `agents_deepagents/s01_agent_loop.py` | Keep the minimal loop while shifting the track identity to Deep Agents. |
| `agents/s02_tool_use.py` | `agents_deepagents/s02_tool_use.py` | Add read/write/edit callables without rewriting the loop. |
| `agents/s03_todo_write.py` | `agents_deepagents/s03_todo_write.py` | Keep visible session planning state in Python and expose it as a tool. |
| `agents/s04_subagent.py` | `agents_deepagents/s04_subagent.py` | Spawn a child agent with fresh messages and return only a summary. |
| `agents/s05_skill_loading.py` | `agents_deepagents/s05_skill_loading.py` | Put a cheap skill catalog in the prompt and load full skill bodies on demand. |
| `agents/s06_context_compact.py` | `agents_deepagents/s06_context_compact.py` | Keep compaction as harness logic around Deep Agents invocation. |

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
