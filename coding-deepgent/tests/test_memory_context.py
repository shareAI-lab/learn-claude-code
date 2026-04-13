from __future__ import annotations

from pathlib import Path

from coding_deepgent.memory import MemoryRecord
from coding_deepgent.prompting import build_prompt_context


def test_prompt_context_injects_recalled_memory_as_distinct_section() -> None:
    context = build_prompt_context(
        workdir=Path("/tmp/project"),
        agent_name="coding-deepgent",
        session_id="s1",
        entrypoint="coding-deepgent",
        memories=[
            MemoryRecord(
                content="Prefer LangChain stores for memory", namespace="project"
            )
        ],
    )

    assert (
        context.memory_context
        == "Relevant long-term memory:\n- [project] Prefer LangChain stores for memory"
    )
    assert context.memory_context in context.system_prompt
    assert context.default_system_prompt[0].startswith("You are coding-deepgent")
