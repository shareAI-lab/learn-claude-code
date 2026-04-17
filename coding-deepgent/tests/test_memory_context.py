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
                type="feedback",
                rule="Run lint before commit",
                why="The repo requires clean validation before code submission",
                how_to_apply="Before any commit-like completion step, run lint first",
            )
        ],
    )

    assert context.memory_context == (
        "Relevant long-term memory:\n"
        "Feedback memory:\n"
        "- Rule: Run lint before commit\n"
        "  Why: The repo requires clean validation before code submission\n"
        "  How to apply: Before any commit-like completion step, run lint first"
    )
    assert context.memory_context in context.system_prompt
    assert context.default_system_prompt[0].startswith("You are coding-deepgent")
