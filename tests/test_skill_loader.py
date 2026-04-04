"""Unit tests for SkillLoader (s05_skill_loading.py)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from conftest import load_agent_module


@pytest.fixture()
def SkillLoader():
    with tempfile.TemporaryDirectory() as tmp:
        module = load_agent_module("s05_skill_loading.py", Path(tmp))
        yield module.SkillLoader


def _make_skill(base_dir: Path, name: str, frontmatter: str, body: str):
    """Helper: create a skills/<name>/SKILL.md file."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}")


# -- _parse_frontmatter --

class TestParseFrontmatter:
    def test_valid_frontmatter(self, SkillLoader):
        loader = SkillLoader(Path("/nonexistent"))
        meta, body = loader._parse_frontmatter("---\nname: test\ndescription: A test\n---\nBody text here")
        assert meta["name"] == "test"
        assert meta["description"] == "A test"
        assert body == "Body text here"

    def test_no_frontmatter(self, SkillLoader):
        loader = SkillLoader(Path("/nonexistent"))
        meta, body = loader._parse_frontmatter("Just plain text without frontmatter")
        assert meta == {}
        assert body == "Just plain text without frontmatter"

    def test_invalid_yaml(self, SkillLoader):
        loader = SkillLoader(Path("/nonexistent"))
        meta, body = loader._parse_frontmatter("---\n: [invalid yaml\n---\nBody")
        assert meta == {}
        assert body == "Body"


# -- _load_all --

class TestLoadAll:
    def test_nonexistent_dir(self, SkillLoader):
        loader = SkillLoader(Path("/does/not/exist"))
        assert loader.skills == {}

    def test_empty_dir(self, SkillLoader, tmp_path):
        loader = SkillLoader(tmp_path)
        assert loader.skills == {}

    def test_loads_skill(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: PDF tools", "Process PDFs here")
        loader = SkillLoader(tmp_path)
        assert "pdf" in loader.skills
        assert loader.skills["pdf"]["body"] == "Process PDFs here"

    def test_name_from_directory(self, SkillLoader, tmp_path):
        """When frontmatter has no 'name', directory name is used."""
        _make_skill(tmp_path, "my-tool", "description: A tool", "Body")
        loader = SkillLoader(tmp_path)
        assert "my-tool" in loader.skills

    def test_multiple_skills(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "a", "name: a\ndescription: Skill A", "Body A")
        _make_skill(tmp_path, "b", "name: b\ndescription: Skill B", "Body B")
        loader = SkillLoader(tmp_path)
        assert len(loader.skills) == 2


# -- get_descriptions --

class TestGetDescriptions:
    def test_no_skills(self, SkillLoader):
        loader = SkillLoader(Path("/nonexistent"))
        assert loader.get_descriptions() == "(no skills available)"

    def test_with_description(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: Process PDFs", "Body")
        loader = SkillLoader(tmp_path)
        desc = loader.get_descriptions()
        assert "pdf: Process PDFs" in desc

    def test_with_tags(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: Process PDFs\ntags: utils", "Body")
        loader = SkillLoader(tmp_path)
        desc = loader.get_descriptions()
        assert "[utils]" in desc

    def test_without_tags(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: Process PDFs", "Body")
        loader = SkillLoader(tmp_path)
        desc = loader.get_descriptions()
        assert "[" not in desc


# -- get_content --

class TestGetContent:
    def test_existing_skill(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: PDF", "PDF instructions")
        loader = SkillLoader(tmp_path)
        content = loader.get_content("pdf")
        assert '<skill name="pdf">' in content
        assert "PDF instructions" in content
        assert "</skill>" in content

    def test_unknown_skill(self, SkillLoader, tmp_path):
        _make_skill(tmp_path, "pdf", "name: pdf\ndescription: PDF", "Body")
        loader = SkillLoader(tmp_path)
        result = loader.get_content("unknown")
        assert "Error: Unknown skill 'unknown'" in result
        assert "pdf" in result  # lists available skills
