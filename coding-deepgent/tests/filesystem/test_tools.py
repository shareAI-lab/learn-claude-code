from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from coding_deepgent.filesystem import (
    bash,
    edit_file,
    glob_search,
    grep_search,
    read_file,
    safe_path,
    write_file,
)


def runtime_for(*, workdir: Path, trusted_workdirs: tuple[Path, ...] = ()):
    return SimpleNamespace(
        context=SimpleNamespace(
            workdir=workdir,
            trusted_workdirs=trusted_workdirs,
        )
    )


def test_safe_path_rejects_workspace_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        safe_path("../escape.txt", workdir=tmp_path)


def test_safe_path_requires_explicit_workdir() -> None:
    with pytest.raises(TypeError):
        safe_path("notes.txt")  # type: ignore[call-arg]


def test_read_write_edit_roundtrip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CODING_DEEPGENT_WORKDIR", str(tmp_path))
    runtime = runtime_for(workdir=tmp_path)
    write = cast(Any, write_file).func
    read = cast(Any, read_file).func
    edit = cast(Any, edit_file).func

    assert (
        write("notes.txt", "alpha\nbeta\n", runtime)
        == "Wrote 11 bytes to notes.txt"
    )
    assert read("notes.txt", runtime) == "alpha\nbeta"
    assert (
        read("notes.txt", runtime, 1)
        == "alpha\n... (1 more lines)"
    )
    assert (
        edit("notes.txt", "beta", "gamma", runtime)
        == "Edited notes.txt"
    )
    assert read("notes.txt", runtime) == "alpha\ngamma"


def test_bash_blocks_dangerous_commands() -> None:
    run = cast(Any, bash).func
    assert (
        run("rm -rf /", runtime_for(workdir=Path.cwd()))
        == "Error: Dangerous command blocked"
    )


def test_tools_allow_explicit_trusted_extra_directories(
    tmp_path: Path,
) -> None:
    trusted_dir = tmp_path.parent / "trusted-shared"
    trusted_dir.mkdir()
    trusted_file = trusted_dir / "shared.txt"

    runtime = runtime_for(workdir=tmp_path, trusted_workdirs=(trusted_dir,))
    write = cast(Any, write_file).func
    read = cast(Any, read_file).func

    assert (
        write(str(trusted_file), "alpha", runtime)
        == f"Wrote 5 bytes to {trusted_file}"
    )
    assert read(str(trusted_file), runtime) == "alpha"


def test_discovery_tools_use_runtime_owned_roots(tmp_path: Path) -> None:
    runtime = runtime_for(workdir=tmp_path)
    (tmp_path / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    glob = cast(Any, glob_search).func
    grep = cast(Any, grep_search).func

    assert glob("*.txt", runtime) == "notes.txt"
    assert grep("beta", runtime, "**/*.txt") == "notes.txt:2:beta"
