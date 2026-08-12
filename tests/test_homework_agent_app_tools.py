from pathlib import Path

import pytest

from homework.agent_app.tools.builtin import (
    run_edit,
    run_glob,
    run_read,
    run_write,
    safe_path,
)
from homework.agent_app.tools.hooks import HookRegistry


def test_safe_path_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        safe_path(tmp_path, "../outside")


def test_hook_registries_do_not_share_callbacks():
    first = HookRegistry()
    second = HookRegistry()

    first.register("Stop", lambda _messages: "first")

    assert second.trigger("Stop", []) is None


def test_file_tools_use_explicit_root_and_cwd(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()

    assert run_write(tmp_path, "note.txt", "before\nafter", cwd=nested) == (
        "Wrote 12 bytes to note.txt"
    )
    assert run_read(tmp_path, "note.txt", cwd=nested) == "before\nafter"
    assert run_edit(tmp_path, "note.txt", "before", "changed", cwd=nested) == (
        "Edited note.txt"
    )
    assert run_glob(tmp_path, "*.txt", cwd=nested) == "note.txt"
    assert (nested / "note.txt").read_text() == "changed\nafter"
