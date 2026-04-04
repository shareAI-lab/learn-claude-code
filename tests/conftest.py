"""Shared fixtures for loading agent modules with mocked dependencies."""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"


def load_agent_module(module_file: str, temp_cwd: Path):
    """Load an agent module with mocked anthropic/dotenv so it doesn't need real API keys.

    Args:
        module_file: filename inside agents/, e.g. "s03_todo_write.py"
        temp_cwd: temporary working directory (avoids polluting real filesystem)

    Returns:
        The loaded module object.
    """
    module_path = AGENTS_DIR / module_file

    # Fake anthropic module
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    setattr(fake_anthropic, "Anthropic", FakeAnthropic)

    # Fake dotenv module
    fake_dotenv = types.ModuleType("dotenv")
    setattr(fake_dotenv, "load_dotenv", lambda **kw: None)

    # Save originals
    prev_anthropic = sys.modules.get("anthropic")
    prev_dotenv = sys.modules.get("dotenv")
    prev_cwd = Path.cwd()

    spec = importlib.util.spec_from_file_location(
        f"agent_{module_file.replace('.py', '')}", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    try:
        os.chdir(temp_cwd)
        os.environ.setdefault("MODEL_ID", "test-model")
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(prev_cwd)
        if prev_anthropic is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = prev_anthropic
        if prev_dotenv is None:
            sys.modules.pop("dotenv", None)
        else:
            sys.modules["dotenv"] = prev_dotenv
