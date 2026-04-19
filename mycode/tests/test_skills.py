"""M1-5: Skills 加载机制测试。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.tools.skills import discover_skills, _parse_skill_md


def _write_skill(dir_path, name: str, description: str, body: str = "skill body"):
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}\n",
        encoding="utf-8",
    )


def test_parse_skill_with_frontmatter(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: foo\ndescription: do foo\n---\nbody here\n", encoding="utf-8")
    s = _parse_skill_md(p)
    assert s is not None
    assert s.name == "foo"
    assert s.description == "do foo"
    assert s.body == "body here"


def test_parse_without_frontmatter_fallback(tmp_path):
    p = tmp_path / "quirky-name"
    p.mkdir()
    md = p / "SKILL.md"
    md.write_text("just a body\n", encoding="utf-8")
    s = _parse_skill_md(md)
    assert s is not None
    assert s.name == "quirky-name"
    assert s.description == "(no description)"


def test_discover_multiple_dirs_first_wins(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_skill(tmp_path / "skills" / "greet", "greet", "proj version")
    _write_skill(tmp_path / ".mycode" / "skills" / "greet", "greet", "user version")
    cfg = load_config(
        cli_overrides={
            "model": "test",
            "provider": "custom",
            "skills_dirs": ["./skills", "~/.mycode/skills"],
        }
    )
    reg = discover_skills(cfg)
    assert "greet" in reg.skills
    # 项目级在前,应胜出
    assert reg.skills["greet"].description == "proj version"


def test_load_known_and_unknown(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_skill(tmp_path / "skills" / "greet", "greet", "hello")
    cfg = load_config(
        cli_overrides={
            "model": "test",
            "provider": "custom",
            "skills_dirs": ["./skills"],
        }
    )
    reg = discover_skills(cfg)
    out = reg.load("greet")
    assert "<skill" in out
    assert "skill body" in out
    assert reg.load("unknown").startswith("Error:")


def test_descriptions_lists_all(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_skill(tmp_path / "skills" / "a", "a", "do a")
    _write_skill(tmp_path / "skills" / "b", "b", "do b")
    cfg = load_config(
        cli_overrides={
            "model": "test",
            "provider": "custom",
            "skills_dirs": ["./skills"],
        }
    )
    reg = discover_skills(cfg)
    desc = reg.descriptions()
    assert "a: do a" in desc
    assert "b: do b" in desc


def test_empty_dirs_no_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(
        cli_overrides={"model": "test", "provider": "custom", "skills_dirs": ["./none"]}
    )
    reg = discover_skills(cfg)
    assert reg.skills == {}
    assert "no skills" in reg.descriptions()
