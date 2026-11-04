import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = sorted(ROOT.glob("s[0-9][0-9]_*"))


def test_every_chapter_uses_english_as_the_default_readme() -> None:
    assert len(CHAPTERS) == 17

    for chapter in CHAPTERS:
        assert (chapter / "README.md").is_file()
        assert (chapter / "README.zh.md").is_file()
        assert (chapter / "README.ja.md").is_file()
        assert not (chapter / "README.en.md").exists()


def test_every_chapter_has_the_same_language_navigation() -> None:
    expected = (
        "[English](README.md) · [中文](README.zh.md) · "
        "[日本語](README.ja.md)"
    )

    for chapter in CHAPTERS:
        for filename in ("README.md", "README.zh.md", "README.ja.md"):
            lines = (chapter / filename).read_text(encoding="utf-8").splitlines()
            assert lines[2] == expected


def test_every_chapter_script_compiles_on_python_311() -> None:
    for chapter in CHAPTERS:
        _ = py_compile.compile(str(chapter / "code.py"), doraise=True)
