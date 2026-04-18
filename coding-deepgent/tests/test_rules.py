from __future__ import annotations

from pathlib import Path

from coding_deepgent.sessions import (
    JsonlSessionStore,
    build_recovery_brief,
    build_resume_context_message,
    render_recovery_brief,
)


def test_recovery_brief_shows_project_rules_signal(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    rules_dir = workdir / ".coding-deepgent"
    rules_dir.mkdir()
    (rules_dir / "RULES.md").write_text("Always explain major tradeoffs first.", encoding="utf-8")

    store = JsonlSessionStore(tmp_path / "sessions")
    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="resume")
    store.append_state_snapshot(context, state={"todos": [], "rounds_since_update": 0})

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert "Project rules:" in rendered
    assert ".coding-deepgent/RULES.md" in rendered


def test_resume_context_message_does_not_repeat_project_rules_section(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    rules_dir = workdir / ".coding-deepgent"
    rules_dir.mkdir()
    (rules_dir / "RULES.md").write_text("Always explain major tradeoffs first.", encoding="utf-8")

    store = JsonlSessionStore(tmp_path / "sessions")
    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="resume")
    store.append_state_snapshot(context, state={"todos": [], "rounds_since_update": 0})

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    message = build_resume_context_message(loaded)

    assert "Project rules:" not in str(message["content"])
