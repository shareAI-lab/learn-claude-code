from __future__ import annotations

from pathlib import Path

from coding_deepgent.agent_service import build_system_prompt
from coding_deepgent.prompting import build_prompt_context
from coding_deepgent.settings import Settings


def test_prompt_context_splits_system_user_and_system_context() -> None:
    context = build_prompt_context(
        workdir=Path("/tmp/project"),
        agent_name="coding-deepgent",
        session_id="session-1",
        entrypoint="coding-deepgent",
    )

    assert context.user_context == {"session_id": "session-1"}
    assert context.system_context == {
        "workdir": "/tmp/project",
        "entrypoint": "coding-deepgent",
        "agent_name": "coding-deepgent",
    }
    assert "coding-deepgent" in context.system_prompt
    assert "write_file" not in context.system_prompt


def test_prompt_context_supports_settings_backed_custom_and_append_prompt() -> None:
    context = build_prompt_context(
        workdir=Path("/tmp/project"),
        agent_name="coding-deepgent",
        session_id="session-1",
        entrypoint="coding-deepgent",
        custom_system_prompt="Custom base",
        append_system_prompt="Appendix",
    )

    assert context.default_system_prompt == ("Custom base",)
    assert context.system_prompt == "Custom base\n\nAppendix"


def test_prompt_context_includes_project_rules_before_memory(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".coding-deepgent"
    rules_dir.mkdir()
    (rules_dir / "RULES.md").write_text("Always explain major tradeoffs first.", encoding="utf-8")

    context = build_prompt_context(
        workdir=tmp_path,
        agent_name="coding-deepgent",
        session_id="session-1",
        entrypoint="coding-deepgent",
        memories=(),
    )

    assert "Project-level rules:" in context.system_prompt
    assert "Always explain major tradeoffs first." in context.system_prompt


def test_build_system_prompt_respects_settings_backed_layering() -> None:
    settings = Settings(
        workdir=Path("/tmp/project"),
        custom_system_prompt="Custom base",
        append_system_prompt="Appendix",
        agent_name="coding-deepgent",
        entrypoint="coding-deepgent",
    )

    assert build_system_prompt(settings) == "Custom base\n\nAppendix"


def test_build_system_prompt_places_rules_before_append_prompt(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".coding-deepgent"
    rules_dir.mkdir()
    (rules_dir / "RULES.md").write_text("Do not skip explicit validation.", encoding="utf-8")
    settings = Settings(
        workdir=tmp_path,
        custom_system_prompt="Custom base",
        append_system_prompt="Appendix",
        agent_name="coding-deepgent",
        entrypoint="coding-deepgent",
    )

    prompt = build_system_prompt(settings)

    assert "Custom base" in prompt
    assert "Project-level rules:" in prompt
    assert "Do not skip explicit validation." in prompt
    assert "Appendix" in prompt
    assert prompt.index("Project-level rules:") < prompt.index("Appendix")
