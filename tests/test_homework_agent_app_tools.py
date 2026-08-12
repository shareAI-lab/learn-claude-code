from pathlib import Path
import threading
import types

import pytest

from homework.agent_app.tools.builtin import (
    run_edit,
    run_glob,
    run_read,
    run_write,
    safe_path,
)
from homework.agent_app.tools.hooks import HookRegistry, make_permission_hook


def test_safe_path_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        safe_path(tmp_path, "../outside")


def test_hook_registries_do_not_share_callbacks():
    first = HookRegistry()
    second = HookRegistry()

    first.register("Stop", lambda _messages: "first")

    assert second.trigger("Stop", []) is None


def test_permission_hook_resolves_current_mcp_metadata_and_lock(tmp_path):
    current = types.SimpleNamespace(metadata={}, lock=threading.RLock())
    hook = make_permission_hook(
        tmp_path,
        lambda _prompt: "n",
        lambda: current.metadata,
        lambda: current.lock,
    )
    block = types.SimpleNamespace(
        name="mcp__deploy__trigger",
        input={"service": "api"},
    )

    current.metadata = {
        block.name: {
            "server": "deploy",
            "original_name": "trigger",
            "destructive": True,
        }
    }
    assert hook(block) == "Permission denied by user"

    current.metadata = {}
    current.lock = threading.RLock()
    assert hook(block) == "Permission denied: unknown MCP tool metadata"


def test_permission_hook_resolves_one_mcp_state_per_check(tmp_path):
    current = types.SimpleNamespace(
        value=types.SimpleNamespace(
            metadata={
                "mcp__docs__search": {
                    "server": "docs",
                    "original_name": "search",
                    "destructive": False,
                }
            },
            lock=threading.RLock(),
        )
    )
    resolutions = []

    def resolve_state():
        resolutions.append(current.value)
        return current.value

    hook = make_permission_hook(
        tmp_path,
        lambda _prompt: "n",
        mcp_state=resolve_state,
    )
    block = types.SimpleNamespace(
        name="mcp__docs__search",
        input={"query": "runtime"},
    )

    assert hook(block) is None
    assert resolutions == [current.value]

    current.value = types.SimpleNamespace(
        metadata={},
        lock=threading.RLock(),
    )
    assert hook(block) == "Permission denied: unknown MCP tool metadata"
    assert resolutions == [resolutions[0], current.value]


def test_permission_hook_accepts_direct_mcp_metadata_and_lock(tmp_path):
    metadata = {
        "mcp__docs__search": {
            "server": "docs",
            "original_name": "search",
            "destructive": False,
        }
    }
    hook = make_permission_hook(
        tmp_path,
        lambda _prompt: "n",
        metadata,
        threading.RLock(),
    )
    block = types.SimpleNamespace(
        name="mcp__docs__search",
        input={"query": "runtime"},
    )

    assert hook(block) is None


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
