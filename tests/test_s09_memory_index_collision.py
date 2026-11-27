"""s09: a record name must never collide with the MEMORY.md index name."""
import runpy
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s09_memory" / "code.py"


def load_lesson(monkeypatch, workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(workdir)
    return runpy.run_path(str(LESSON))


@pytest.mark.parametrize("name", ["Memory", "MEMORY", "memory!", "!!!", "???"])
def test_memory_slug_never_matches_index_name(tmp_path, monkeypatch, name):
    lesson = load_lesson(monkeypatch, tmp_path)

    slug = lesson["memory_slug"](name)

    assert slug
    assert f"{slug}.md".lower() != lesson["MEMORY_INDEX"].name.lower()
    assert lesson["memory_path"](f"{slug}.md").name == f"{slug}.md"


@pytest.mark.parametrize("filename", ["memory.md", "MEMORY.md", "Memory.md"])
def test_memory_path_rejects_index_name_case_insensitively(
        tmp_path, monkeypatch, filename):
    lesson = load_lesson(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        lesson["memory_path"](filename)

    assert lesson["memory_path"](
        filename, allow_index=True
    ).name.lower() == "memory.md"


def test_write_named_memory_keeps_a_distinct_record_and_index(
        tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)

    path = lesson["write_memory_file"](
        "Memory", "user", "A durable note", "body text"
    )

    # On a case-insensitive filesystem both names resolve to one file, so the
    # record name must differ from the index name ignoring case.
    assert path.name.lower() != lesson["MEMORY_INDEX"].name.lower()
    assert path.is_file()
    assert "body text" in lesson["read_memory_file"](path.name)
    assert [record["filename"] for record in lesson["list_memory_files"]()] == [
        path.name
    ]
    assert "Memory" in lesson["read_memory_index"]()
    assert path.name in lesson["read_memory_index"]()


def test_case_variant_of_index_is_not_loaded_as_a_record(tmp_path, monkeypatch):
    """Simulates an index file whose on-disk spelling uses different case."""
    lesson = load_lesson(monkeypatch, tmp_path)
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "memory.md").write_text(
        "---\nname: Memory\ndescription: must be skipped\ntype: user\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )

    assert lesson["list_memory_files"]() == []

    lesson["rebuild_memory_index"]()

    assert lesson["read_memory_index"]() == ""


def test_normal_memory_record_is_unchanged(tmp_path, monkeypatch):
    lesson = load_lesson(monkeypatch, tmp_path)

    assert lesson["memory_slug"]("User Preference Tabs") == "user-preference-tabs"

    path = lesson["write_memory_file"](
        "User Preference Tabs", "user", "Prefers tabs", "Use tabs"
    )

    assert path.name == "user-preference-tabs.md"
    assert lesson["read_memory_file"](path.name) is not None
    assert [record["filename"] for record in lesson["list_memory_files"]()] == [
        "user-preference-tabs.md"
    ]
    assert "user-preference-tabs.md" in lesson["read_memory_index"]()
