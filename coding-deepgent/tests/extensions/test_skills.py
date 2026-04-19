from __future__ import annotations

from typing import Any, cast
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from coding_deepgent.skills import LoadSkillInput, load_local_skill, load_skill
from coding_deepgent.skills.loader import discover_local_skills, parse_skill_markdown


def write_skill(root: Path, name: str = "demo") -> None:
    path = root / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n\nUse this skill carefully.",
        encoding="utf-8",
    )


def test_local_skill_loader_reads_frontmatter_and_body(tmp_path: Path) -> None:
    write_skill(tmp_path)

    loaded = load_local_skill(workdir=tmp_path.parent, skill_dir=tmp_path, name="demo")

    assert loaded.metadata.name == "demo"
    assert loaded.metadata.description == "Demo skill"
    assert "Use this skill" in loaded.body


def test_load_skill_tool_is_strict_and_uses_runtime_context(tmp_path: Path) -> None:
    write_skill(tmp_path)
    runtime = SimpleNamespace(
        context=SimpleNamespace(workdir=tmp_path.parent, skill_dir=tmp_path)
    )

    assert "# Skill: demo" in cast(Any, load_skill).func("demo", runtime)
    assert load_skill.name == "load_skill"
    assert (
        "name"
        in cast(Any, load_skill.tool_call_schema).model_json_schema()["properties"]
    )

    with pytest.raises(ValidationError):
        LoadSkillInput.model_validate({"skill": "demo", "runtime": runtime})


def test_skill_loader_rejects_malformed_or_mismatched_skills(tmp_path: Path) -> None:
    malformed = tmp_path / "bad" / "SKILL.md"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("no frontmatter", encoding="utf-8")
    mismatch_root = tmp_path / "skills"
    write_skill(mismatch_root, name="actual")
    (mismatch_root / "actual" / "SKILL.md").write_text(
        "---\nname: other\ndescription: Demo skill\n---\n\nBody.",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing frontmatter"):
        parse_skill_markdown(malformed)
    with pytest.raises(ValueError, match="Skill name mismatch"):
        load_local_skill(workdir=tmp_path, skill_dir=mismatch_root, name="actual")
    with pytest.raises(ValueError, match="directory and metadata name"):
        discover_local_skills(workdir=tmp_path, skill_dir=mismatch_root)


def test_loaded_skill_render_truncates_large_skill_body(tmp_path: Path) -> None:
    write_skill(tmp_path)
    loaded = load_local_skill(workdir=tmp_path.parent, skill_dir=tmp_path, name="demo")
    long_skill = type(loaded)(
        metadata=loaded.metadata,
        body="x" * 20,
        path=loaded.path,
    )

    rendered = long_skill.render(max_chars=5)

    assert rendered.endswith("xxxxx\n...[skill truncated]")
