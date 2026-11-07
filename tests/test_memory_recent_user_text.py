import runpy
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s09_memory" / "code.py"


def load_lesson(monkeypatch):
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
    return runpy.run_path(str(LESSON))


def test_recent_user_text_keeps_the_latest_context_when_truncated(monkeypatch):
    lesson = load_lesson(monkeypatch)
    messages = [
        {"role": "user", "content": "older-" + "o" * 3000},
        {"role": "assistant", "content": "ack"},
        {"role": "user", "content": "middle-" + "m" * 1000},
        {"role": "user", "content": "latest"},
    ]

    result = lesson["recent_user_text"](messages)

    assert len(result) == 4000
    assert "older-" not in result
    assert "middle-" in result
    assert result.endswith("latest")
    assert result.index("middle-") < result.index("latest")
