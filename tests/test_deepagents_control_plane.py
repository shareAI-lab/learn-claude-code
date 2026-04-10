from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents_deepagents import s07_permission_system as s07
from agents_deepagents import s08_hook_system as s08
from agents_deepagents import s09_memory_system as s09
from agents_deepagents import s10_system_prompt as s10
from agents_deepagents import s11_error_recovery as s11


def test_permission_manager_plan_mode_blocks_writes() -> None:
    manager = s07.PermissionManager(mode="plan")
    assert manager.check("read_file", {"path": "README.md"})["behavior"] == "allow"
    assert manager.check("write_file", {"path": "demo.txt", "content": "x"})["behavior"] == "deny"


def test_bash_validator_flags_dangerous_patterns() -> None:
    failures = s07.bash_validator.validate("sudo rm -rf /tmp/demo")
    assert {name for name, _ in failures} >= {"sudo", "rm_rf"}


def test_hook_manager_supports_injected_messages(tmp_path: Path) -> None:
    config = tmp_path / ".hooks.json"
    payload = {
        "hooks": {
            "SessionStart": [
                {"command": "python -c \"import sys; sys.stderr.write('session-start'); sys.exit(2)\""}
            ]
        }
    }
    config.write_text(json.dumps(payload), encoding="utf-8")
    manager = s08.HookManager(config_path=config, sdk_mode=True)
    result = manager.run_hooks("SessionStart")
    assert result["messages"] == ["session-start"]
    assert result["blocked"] is False


def test_memory_manager_saves_and_loads_prompt(tmp_path: Path) -> None:
    manager = s09.MemoryManager(tmp_path)
    msg = manager.save_memory("db_schema", "Database schema", "project", "tables: users")
    assert "Saved memory" in msg
    prompt = manager.load_memory_prompt()
    assert "db_schema" in prompt
    assert "tables: users" in prompt


def test_system_prompt_builder_assembles_static_and_dynamic_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = s10.SystemPromptBuilder(workdir=tmp_path, tools=[s10.bash])
    built = builder.build()
    assert s10.DYNAMIC_BOUNDARY in built
    assert "# Available tools" in built
    assert "# Dynamic context" in built


def test_backoff_delay_grows_with_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s11.random, "uniform", lambda a, b: 0.0)
    assert s11.backoff_delay(0) == pytest.approx(1.0)
    assert s11.backoff_delay(1) == pytest.approx(2.0)
    assert s11.backoff_delay(2) == pytest.approx(4.0)
