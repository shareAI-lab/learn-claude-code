import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "s08": REPO_ROOT / "s08_context_compact" / "code.py",
    "s09": REPO_ROOT / "s09_memory" / "code.py",
    "s20": REPO_ROOT / "s20_comprehensive" / "code.py",
}


def load_module(name: str, path: Path, temp_cwd: Path):
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)

    previous_anthropic = sys.modules.get("anthropic")
    previous_dotenv = sys.modules.get("dotenv")
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    previous_key = os.environ.get("ANTHROPIC_API_KEY")

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    os.environ["MODEL_ID"] = "test-model"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        os.chdir(temp_cwd)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_anthropic is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = previous_anthropic
        if previous_dotenv is None:
            sys.modules.pop("dotenv", None)
        else:
            sys.modules["dotenv"] = previous_dotenv
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        if previous_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = previous_key


def assistant_text():
    return {"role": "assistant", "content": [types.SimpleNamespace(type="text", text="ok")]}


def user_text():
    return {"role": "user", "content": "continue"}


def tool_use_message(tool_id="tool-1"):
    return {
        "role": "assistant",
        "content": [types.SimpleNamespace(type="tool_use", id=tool_id, name="bash")],
    }


def tool_result_message(tool_id="tool-1"):
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}],
    }


def message_has_tool_use(message):
    content = message.get("content")
    return (
        message.get("role") == "assistant"
        and isinstance(content, list)
        and any(getattr(block, "type", None) == "tool_use" for block in content)
    )


def assert_no_orphan_tool_results(testcase, messages):
    for idx, message in enumerate(messages):
        content = message.get("content")
        if message.get("role") != "user" or not isinstance(content, list):
            continue
        if not any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content):
            continue
        testcase.assertGreater(idx, 0)
        testcase.assertTrue(message_has_tool_use(messages[idx - 1]), messages)


class CompactionToolPairTests(unittest.TestCase):
    def test_snip_compact_keeps_head_tool_pair(self):
        messages = [
            user_text(),
            assistant_text(),
            tool_use_message("head-tool"),
            tool_result_message("head-tool"),
            assistant_text(),
            user_text(),
            assistant_text(),
            user_text(),
            assistant_text(),
            user_text(),
        ]

        for name, path in MODULES.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(f"{name}_head_under_test", path, Path(tmp))
                if name == "s09":
                    compacted = module.snip_compact(list(messages), mx=6)
                else:
                    compacted = module.snip_compact(list(messages), max_messages=6)
                self.assertEqual(compacted[2], messages[2])
                self.assertEqual(compacted[3], messages[3])
                assert_no_orphan_tool_results(self, compacted)

    def test_snip_compact_keeps_tail_tool_pair(self):
        messages = [
            user_text(),
            assistant_text(),
            user_text(),
            assistant_text(),
            user_text(),
            assistant_text(),
            tool_use_message("tail-tool"),
            tool_result_message("tail-tool"),
            assistant_text(),
            user_text(),
        ]

        for name, path in MODULES.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(f"{name}_under_test", path, Path(tmp))
                if name == "s09":
                    compacted = module.snip_compact(list(messages), mx=6)
                else:
                    compacted = module.snip_compact(list(messages), max_messages=6)
                assert_no_orphan_tool_results(self, compacted)

    def test_reactive_compact_keeps_tail_tool_pair(self):
        messages = [
            user_text(),
            assistant_text(),
            user_text(),
            tool_use_message("reactive-tool"),
            tool_result_message("reactive-tool"),
            assistant_text(),
            user_text(),
            assistant_text(),
            user_text(),
        ]

        for name, path in MODULES.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(f"{name}_reactive_under_test", path, Path(tmp))
                module.write_transcript = lambda _messages: Path("transcript.jsonl")
                module.summarize_history = lambda _messages: "summary"
                compacted = module.reactive_compact(list(messages))
                self.assertEqual(compacted[1], messages[3])
                assert_no_orphan_tool_results(self, compacted)

    def test_s20_has_tool_use_still_accepts_content_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_module("s20_has_tool_use_under_test", MODULES["s20"], Path(tmp))
            self.assertTrue(module.has_tool_use([types.SimpleNamespace(type="tool_use")]))
            self.assertFalse(module.has_tool_use([types.SimpleNamespace(type="text")]))


if __name__ == "__main__":
    unittest.main()
