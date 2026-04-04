from __future__ import annotations

from pathlib import Path
import py_compile

import pytest


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
AGENT_FILES = sorted(
    path for path in AGENTS_DIR.glob("*.py") if path.name != "__init__.py"
)
AGENT_IDS = [path.name for path in AGENT_FILES]


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=AGENT_IDS)
def test_agent_scripts_compile(agent_path: Path) -> None:
    _ = py_compile.compile(str(agent_path), doraise=True)


def test_agent_scripts_exist() -> None:
    assert AGENT_FILES, "expected at least one agent script"
