import importlib.util
import os
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "agents" / "s05_skill_loading.py"


def load_s05_module(temp_cwd: Path):
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
    spec = importlib.util.spec_from_file_location("s05_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    try:
        os.chdir(temp_cwd)
        os.environ.setdefault("MODEL_ID", "test-model")
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


class SkillLoaderTests(unittest.TestCase):
    def test_get_descriptions_keeps_folded_frontmatter_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_cwd = Path(tmp)
            module = load_s05_module(temp_cwd)
            skills_dir = temp_cwd / "skills" / "demo-skill"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: demo
                    description: >
                      Loads the skill metadata correctly
                      even when the description spans lines.
                    tags: parsing, regression
                    ---
                    # Demo Skill

                    Body content.
                    """
                )
            )

            loader = module.SkillLoader(temp_cwd / "skills")

            self.assertEqual(
                loader.skills["demo"]["meta"]["description"],
                "Loads the skill metadata correctly even when the description spans lines.",
            )
            self.assertEqual(
                loader.get_descriptions(),
                "  - demo: Loads the skill metadata correctly even when the description spans lines. [parsing, regression]",
            )


if __name__ == "__main__":
    unittest.main()
