import importlib.util
import sys
import types
from pathlib import Path

import pytest


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


class BaseAgentModule:
    def __init__(self, module):
        self.module = module

    def __getitem__(self, name):
        return getattr(self.module, name)


def load_baseagent_module():
    spec = importlib.util.spec_from_file_location("_baseagent_compact", BASE_AGENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return BaseAgentModule(module)


@pytest.fixture
def baseagent(monkeypatch):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(
                create=None,
                stream=None,
            )

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "test-model")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)

    return load_baseagent_module()


def response(content, stop_reason="tool_use"):
    return types.SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
    )


def test_compact_schema_is_registered_without_normal_handler(baseagent):
    compact_tools = [
        tool
        for tool in baseagent["BUILTIN_TOOLS"]
        if tool["name"] == "compact"
    ]

    assert len(compact_tools) == 1
    schema = compact_tools[0]["input_schema"]
    assert schema["properties"]["focus"]["type"] == "string"
    assert schema["required"] == []
    assert "compact" not in baseagent["BUILTIN_HANDLERS"]
