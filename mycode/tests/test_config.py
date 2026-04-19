"""配置加载顺序测试。"""
from __future__ import annotations

import json

from mycode.config import load_config


def test_profile_fills_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "deepseek"})
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.model == "deepseek-chat"
    assert cfg.api_key_env == "DEEPSEEK_API_KEY"


def test_fenbi_profile_has_default_query(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "fenbi"})
    assert cfg.default_query == {"service_provider": "ppio"}
    assert cfg.base_url.endswith("/agi/api/openai/v1")


def test_project_overrides_user(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    user = tmp_path / ".mycode"
    user.mkdir()
    (user / "settings.json").write_text(
        json.dumps({"provider": "deepseek", "model": "user-m"})
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".mycode").mkdir()
    (proj / ".mycode" / "settings.json").write_text(json.dumps({"model": "proj-m"}))
    monkeypatch.chdir(proj)
    cfg = load_config()
    assert cfg.provider == "deepseek"
    assert cfg.model == "proj-m"


def test_cli_override_wins(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "openai", "model": "cli-m"})
    assert cfg.model == "cli-m"


def test_memory_files_default_includes_user_level(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "deepseek"})
    assert "~/.mycode/CLAUDE.md" in cfg.memory_files


def test_deep_merge_mcp_servers(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    user = tmp_path / ".mycode"
    user.mkdir()
    (user / "settings.json").write_text(
        json.dumps({"mcp_servers": {"linear": {"command": "npx"}}})
    )
    proj = tmp_path / "proj"
    (proj / ".mycode").mkdir(parents=True)
    (proj / ".mycode" / "settings.json").write_text(
        json.dumps({"mcp_servers": {"github": {"command": "gh-mcp"}}})
    )
    monkeypatch.chdir(proj)
    cfg = load_config()
    assert set(cfg.mcp_servers.keys()) == {"linear", "github"}
