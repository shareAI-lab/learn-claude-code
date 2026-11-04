import importlib.util
import os
import sys
import tempfile
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s07_skill_loading" / "code.py"
INTEGRATED_LESSON = ROOT / "s15_integrated_harness" / "code.py"
SKILL_LESSONS = (LESSON, INTEGRATED_LESSON)


def load_lesson(workdir: Path, lesson_path: Path = LESSON):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")

    module_name = f"skill_loading_test_{lesson_path.parent.name}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, lesson_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules[module_name] = module
    try:
        os.chdir(workdir)
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        sys.modules.pop(module_name, None)


def parse_frontmatter(lesson, text: str) -> tuple[dict, str]:
    if hasattr(lesson, "SkillLoader"):
        return lesson.SkillLoader.parse_frontmatter(text)
    return lesson._parse_frontmatter(text)


def test_catalog_stays_small_and_load_skill_returns_the_full_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / "skills" / "code-review"
        skill_dir.mkdir(parents=True)
        manifest = """---
name: code-review
description: |
  Review code for bugs,
  regressions, and missing tests.
---

# Code Review

UNIQUE_FULL_INSTRUCTION
"""
        (skill_dir / "SKILL.md").write_text(manifest)

        lesson = load_lesson(root)

        assert lesson.SKILL_LOADER.catalog() == (
            "- code-review: Review code for bugs, regressions, and missing tests."
        )
        assert "code-review" in lesson.SYSTEM
        assert "UNIQUE_FULL_INSTRUCTION" not in lesson.SYSTEM
        assert lesson.SKILL_LOADER.load("code-review") == manifest
        assert lesson.TOOL_HANDLERS["load_skill"]("code-review") == manifest


def test_skill_loaders_read_utf8_manifests() -> None:
    manifest = """---
name: chinese-skill
description: 处理中文内容
---

# 中文技能
"""
    for lesson_path in SKILL_LESSONS:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "chinese-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_bytes(manifest.encode("utf-8"))

            lesson = load_lesson(root, lesson_path)
            registry = (lesson.SKILL_LOADER.skills
                        if hasattr(lesson, "SKILL_LOADER")
                        else lesson.SKILL_REGISTRY)
            loaded = (lesson.SKILL_LOADER.load("chinese-skill")
                      if hasattr(lesson, "SKILL_LOADER")
                      else lesson.load_skill("chinese-skill"))

            assert registry["chinese-skill"]["description"] == "处理中文内容"
            assert loaded == manifest


def test_s07_exposes_only_base_tools_and_load_skill() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        assert [tool["name"] for tool in lesson.TOOLS] == [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "load_skill",
        ]


def test_skill_frontmatter_requires_standalone_delimiters() -> None:
    invalid_opening = "---not frontmatter\n---\n# Body"
    block_scalar = """---
name: demo
description: |
  before
  ---
  after
---
# Body
"""
    for lesson_path in SKILL_LESSONS:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp), lesson_path)
            assert parse_frontmatter(lesson, invalid_opening) == ({}, invalid_opening)
            for text in (block_scalar, block_scalar.replace("\n", "\r\n")):
                metadata, body = parse_frontmatter(lesson, text)
                assert metadata["description"] == "before\n---\nafter\n"
                assert body == "# Body"


def test_skill_frontmatter_falls_back_for_invalid_or_empty_metadata() -> None:
    manifest = "---\nname:\ndescription:\n---\n# Body description\n"
    for lesson_path in SKILL_LESSONS:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "fallback-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(manifest)
            empty_dir = root / "skills" / "empty-skill"
            empty_dir.mkdir()
            (empty_dir / "SKILL.md").write_text("---\nname: empty-skill\n---\n")
            typed_dir = root / "skills" / "typed-fallback"
            typed_dir.mkdir()
            (typed_dir / "SKILL.md").write_text(
                "---\nname: [bad]\ndescription: [bad]\n---\n# Typed fallback\n"
            )
            outside = root / "outside-skill.md"
            outside.write_text("# External skill\n\nDO_NOT_LOAD")
            linked_dir = root / "skills" / "linked-skill"
            linked_dir.mkdir()
            (linked_dir / "SKILL.md").symlink_to(outside)
            lesson = load_lesson(root, lesson_path)
            registry = (lesson.SKILL_LOADER.skills if hasattr(lesson, "SKILL_LOADER")
                        else lesson.SKILL_REGISTRY)
            assert registry["fallback-skill"]["description"] == "Body description"
            assert registry["empty-skill"]["description"] == ""
            assert registry["typed-fallback"]["description"] == "Typed fallback"
            assert "linked-skill" not in registry

            metadata, body = parse_frontmatter(
                lesson, "---\n- not\n- a mapping\n---\nBody"
            )
            assert metadata == {}
            assert body == "Body"
