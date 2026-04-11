from __future__ import annotations

from pathlib import Path

import pytest

from coding_deepgent.tools.filesystem import bash, edit_file, read_file, safe_path, write_file


def test_safe_path_rejects_workspace_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        safe_path("../escape.txt", workdir=tmp_path)


def test_read_write_edit_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODING_DEEPGENT_WORKDIR", str(tmp_path))

    assert write_file("notes.txt", "alpha\nbeta\n") == "Wrote 11 bytes to notes.txt"
    assert read_file("notes.txt") == "alpha\nbeta"
    assert read_file("notes.txt", limit=1) == "alpha\n... (1 more lines)"
    assert edit_file("notes.txt", "beta", "gamma") == "Edited notes.txt"
    assert read_file("notes.txt") == "alpha\ngamma"


def test_bash_blocks_dangerous_commands() -> None:
    assert bash("rm -rf /") == "Error: Dangerous command blocked"
