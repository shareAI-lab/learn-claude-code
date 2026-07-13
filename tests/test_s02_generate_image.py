import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "s02_tool_use" / "code.py"


def load_course_module():
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_model_id = os.environ.get("MODEL_ID")
    spec = importlib.util.spec_from_file_location("s02_generate_image_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    try:
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_model_id is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model_id
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps({
            "data": {"image_urls": ["https://example.com/generated.png"]},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }).encode("utf-8")


class GenerateImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_course_module()

    def test_tool_schema_matches_the_image_api_contract(self):
        tool = next(tool for tool in self.module.TOOLS if tool["name"] == "generate_image")
        schema = tool["input_schema"]

        self.assertEqual(schema["required"], ["prompt"])
        self.assertEqual(schema["properties"]["prompt"]["maxLength"], 1500)
        self.assertEqual(schema["properties"]["aspect_ratio"]["default"], "1:1")
        self.assertEqual(
            schema["properties"]["aspect_ratio"]["enum"],
            ["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"],
        )

    def test_uses_the_selected_regional_api_host(self):
        previous_key = os.environ.get("MINIMAX_API_KEY")
        previous_host = os.environ.get("MINIMAX_API_HOST")
        try:
            os.environ["MINIMAX_API_KEY"] = "test-key"
            cases = [
                (None, "https://api.minimax.io/v1/image_generation"),
                ("https://api.minimaxi.com/", "https://api.minimaxi.com/v1/image_generation"),
            ]
            for host, expected_url in cases:
                with self.subTest(host=host):
                    if host is None:
                        os.environ.pop("MINIMAX_API_HOST", None)
                    else:
                        os.environ["MINIMAX_API_HOST"] = host
                    captured = {}

                    def fake_urlopen(request, timeout):
                        captured["request"] = request
                        captured["timeout"] = timeout
                        return FakeResponse()

                    with patch.object(
                        self.module.urllib.request,
                        "urlopen",
                        side_effect=fake_urlopen,
                    ):
                        result = self.module.run_generate_image("sunrise", "16:9")

                    request = captured["request"]
                    self.assertEqual(result, "https://example.com/generated.png")
                    self.assertEqual(request.full_url, expected_url)
                    self.assertEqual(captured["timeout"], 120)
                    self.assertEqual(
                        json.loads(request.data.decode("utf-8")),
                        {
                            "model": "image-01",
                            "prompt": "sunrise",
                            "aspect_ratio": "16:9",
                            "n": 1,
                            "response_format": "url",
                        },
                    )
                    self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        finally:
            if previous_key is None:
                os.environ.pop("MINIMAX_API_KEY", None)
            else:
                os.environ["MINIMAX_API_KEY"] = previous_key
            if previous_host is None:
                os.environ.pop("MINIMAX_API_HOST", None)
            else:
                os.environ["MINIMAX_API_HOST"] = previous_host


if __name__ == "__main__":
    unittest.main()
