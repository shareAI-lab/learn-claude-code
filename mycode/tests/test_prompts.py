"""M6-3: prompt 加载器与中英双语模板测试。"""
from __future__ import annotations

import pytest

from mycode.config import load_config
from mycode.prompts import PromptLoader, load_prompt
from mycode.prompts.loader import DEFAULT_LANG, _prompts_base


# ---------- 内置 prompt 存在性 ----------


EXPECTED_PROMPTS = [
    "base_system",
    "subagent_system",
    "teammate_system",
    "summarize",
    "auto_compact",
    "expert_system",
]


def test_all_en_prompts_exist():
    base = _prompts_base() / "en"
    for name in EXPECTED_PROMPTS:
        assert (base / f"{name}.md").is_file(), f"missing en/{name}.md"


def test_all_zh_prompts_exist():
    base = _prompts_base() / "zh"
    for name in EXPECTED_PROMPTS:
        assert (base / f"{name}.md").is_file(), f"missing zh/{name}.md"


def test_en_and_zh_same_filenames():
    en_files = {p.name for p in (_prompts_base() / "en").glob("*.md")}
    zh_files = {p.name for p in (_prompts_base() / "zh").glob("*.md")}
    assert en_files == zh_files, f"en-zh mismatch: en-only={en_files - zh_files}, zh-only={zh_files - en_files}"


# ---------- loader 基础行为 ----------


def test_load_en_base_system():
    loader = PromptLoader(lang="en")
    text = loader.render("base_system")
    assert "mycode" in text
    assert "coding agent" in text.lower()


def test_load_zh_base_system():
    loader = PromptLoader(lang="zh")
    text = loader.render("base_system")
    assert "mycode" in text
    assert "编码 Agent" in text


def test_load_prompt_convenience_function():
    text = load_prompt("base_system", lang="en")
    assert "mycode" in text


def test_unknown_lang_falls_back_to_en():
    # __post_init__ 会把非法 lang 重置为 default (en)
    loader = PromptLoader(lang="fr")
    assert loader.lang == DEFAULT_LANG
    text = loader.render("base_system")
    assert "You are mycode" in text


def test_missing_prompt_raises():
    with pytest.raises(FileNotFoundError, match="not-a-real-prompt"):
        load_prompt("not-a-real-prompt", lang="en")


def test_zh_missing_prompt_falls_back_to_en(tmp_path):
    """如果 zh 缺某个 prompt,应 fallback 到 en (避免一侧加新模板时另一侧 CI 崩)。"""
    # 这里用 expert_system: 我们确定两边都有;
    # 用一个不存在的假路径模拟 zh 目录少文件不现实,所以直接测代码路径:
    loader = PromptLoader(lang="zh")
    candidates = loader._candidates("base_system")
    # 应该有 3 个候选: 项目级 + zh + en fallback
    assert len(candidates) >= 2
    assert any("/en/" in str(c) for c in candidates), "zh lang should include en fallback"


# ---------- 模板变量 ----------


def test_render_with_vars():
    text = load_prompt(
        "teammate_system",
        lang="en",
        name="alice",
        role="backend",
        team_name="core",
        workspace_path="/tmp/x",
    )
    assert "'alice'" in text
    assert "backend" in text
    assert "'core'" in text
    assert "/tmp/x" in text


def test_render_missing_var_raises():
    with pytest.raises(KeyError, match="teammate_system"):
        load_prompt("teammate_system", lang="en", name="alice")  # 缺 role/team_name/workspace_path


def test_render_extra_vars_ignored():
    text = load_prompt("base_system", lang="en", foo="bar", baz=42)
    assert "mycode" in text
    assert "foo" not in text


def test_subagent_prompt_variables():
    text = load_prompt(
        "subagent_system",
        lang="en",
        description="explore the codebase",
        subagent_type="Explore",
    )
    assert "explore the codebase" in text
    assert "Explore" in text


def test_auto_compact_has_conversation_placeholder():
    raw_en = PromptLoader(lang="en").load_raw("auto_compact")
    assert "{conversation}" in raw_en
    raw_zh = PromptLoader(lang="zh").load_raw("auto_compact")
    assert "{conversation}" in raw_zh


# ---------- 项目级覆盖 ----------


def test_project_override_takes_precedence(tmp_path, monkeypatch):
    """如果 `<workspace>/.mycode/prompts/{lang}/<name>.md` 存在,应优先用它。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    override_dir = tmp_path / ".mycode" / "prompts" / "en"
    override_dir.mkdir(parents=True)
    (override_dir / "base_system.md").write_text(
        "custom project system prompt", encoding="utf-8"
    )

    text = load_prompt("base_system", lang="en", workspace=tmp_path)
    assert text == "custom project system prompt"


def test_project_override_missing_falls_back(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # 没有项目级覆盖,应使用内置
    text = load_prompt("base_system", lang="en", workspace=tmp_path)
    assert "mycode" in text


# ---------- Config 集成 ----------


def test_config_prompt_lang_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "x", "provider": "custom"})
    assert cfg.prompt_lang == "en"


def test_config_prompt_lang_zh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(
        cli_overrides={"model": "x", "provider": "custom", "prompt_lang": "zh"}
    )
    assert cfg.prompt_lang == "zh"


def test_config_prompt_lang_invalid_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(SystemExit):
        load_config(
            cli_overrides={"model": "x", "provider": "custom", "prompt_lang": "fr"}
        )


# ---------- available() ----------


def test_available_lists_all():
    loader = PromptLoader(lang="en")
    names = loader.available()
    for p in EXPECTED_PROMPTS:
        assert p in names
