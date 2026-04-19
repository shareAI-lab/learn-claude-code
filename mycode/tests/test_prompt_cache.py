"""M6-4: Prompt cache 单元测试。

只测纯函数 + Config + 局部消息 transform,不起真实 HTTP 调用。
"""
from __future__ import annotations

import pytest

from mycode.config import load_config
from mycode.llm.prompt_cache import (
    apply_cache_control,
    extract_cached_tokens,
    resolve_cache_mode,
)
from mycode.llm.providers import get_profile


# ---------- resolve_cache_mode ----------


def test_resolve_user_off_overrides_profile():
    assert resolve_cache_mode("off", "explicit") == "off"


def test_resolve_user_explicit_overrides_profile():
    assert resolve_cache_mode("explicit", "auto") == "explicit"


def test_resolve_user_auto_follows_profile_explicit():
    assert resolve_cache_mode("auto", "explicit") == "explicit"


def test_resolve_user_auto_follows_profile_off():
    assert resolve_cache_mode("auto", "off") == "off"


def test_resolve_user_auto_keeps_auto_when_profile_auto():
    assert resolve_cache_mode("auto", "auto") == "auto"


def test_resolve_missing_profile_mode():
    # profile 没声明 cache_mode,保留用户值
    assert resolve_cache_mode("auto", None) == "auto"
    assert resolve_cache_mode("off", None) == "off"


# ---------- apply_cache_control ----------


def test_apply_off_returns_original_untouched():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    out = apply_cache_control(msgs, "off")
    assert out is msgs
    assert msgs[0]["content"] == "s"  # 未改


def test_apply_auto_returns_original_untouched():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    out = apply_cache_control(msgs, "auto")
    assert out is msgs


def test_apply_explicit_wraps_system_and_last_user():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    out = apply_cache_control(msgs, "explicit")
    # system 消息被 wrap 成 list[dict] 且末块有 cache_control
    sys_content = out[0]["content"]
    assert isinstance(sys_content, list)
    assert sys_content[-1]["cache_control"] == {"type": "ephemeral"}
    assert sys_content[-1]["text"] == "sys"
    # u1 不动(只有最后一条 user 被标)
    assert out[1]["content"] == "u1"
    # u2 被标
    u2 = out[3]["content"]
    assert isinstance(u2, list)
    assert u2[-1]["cache_control"] == {"type": "ephemeral"}


def test_apply_explicit_preserves_original_messages():
    """transform 不应就地改原消息。"""
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    _ = apply_cache_control(msgs, "explicit")
    assert msgs[0]["content"] == "sys"
    assert msgs[1]["content"] == "u"


def test_apply_explicit_empty_messages():
    assert apply_cache_control([], "explicit") == []


def test_apply_explicit_no_system():
    msgs = [{"role": "user", "content": "hi"}]
    out = apply_cache_control(msgs, "explicit")
    u = out[0]["content"]
    assert isinstance(u, list)
    assert u[-1]["cache_control"] == {"type": "ephemeral"}


def test_apply_explicit_only_tool_messages():
    """最后一条 user 前插了 tool_result,仍应标 user 消息。"""
    msgs = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
        {"role": "tool", "tool_call_id": "t1", "content": "result"},
    ]
    out = apply_cache_control(msgs, "explicit")
    assert out[0]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    # user 被标
    assert out[1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    # tool_result 未动
    assert out[3]["content"] == "result"


def test_apply_explicit_list_content_preserved():
    msgs = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "part1"},
                {"type": "text", "text": "part2"},
            ],
        },
        {"role": "user", "content": "u"},
    ]
    out = apply_cache_control(msgs, "explicit")
    sys_blocks = out[0]["content"]
    assert len(sys_blocks) == 2
    assert "cache_control" not in sys_blocks[0]
    assert sys_blocks[-1]["cache_control"] == {"type": "ephemeral"}


# ---------- extract_cached_tokens ----------


def test_extract_openai_style():
    usage = {"prompt_tokens": 1000, "prompt_tokens_details": {"cached_tokens": 800}}
    assert extract_cached_tokens(usage) == 800


def test_extract_deepseek_style():
    usage = {"prompt_tokens": 1000, "prompt_cache_hit_tokens": 600}
    assert extract_cached_tokens(usage) == 600


def test_extract_anthropic_style():
    usage = {"cache_read_input_tokens": 500}
    assert extract_cached_tokens(usage) == 500


def test_extract_flat_cached_tokens():
    usage = {"cached_tokens": 333}
    assert extract_cached_tokens(usage) == 333


def test_extract_none_usage_returns_zero():
    assert extract_cached_tokens(None) == 0


def test_extract_empty_usage_returns_zero():
    assert extract_cached_tokens({}) == 0


def test_extract_zero_cached_returns_zero():
    # 0 不应被当作命中
    usage = {"prompt_tokens_details": {"cached_tokens": 0}}
    assert extract_cached_tokens(usage) == 0


def test_extract_prefers_openai_over_others():
    usage = {
        "prompt_tokens_details": {"cached_tokens": 100},
        "prompt_cache_hit_tokens": 200,  # deepseek 字段同时出现
    }
    assert extract_cached_tokens(usage) == 100  # openai 优先


# ---------- Providers cache_mode ----------


def test_profile_openai_auto():
    assert get_profile("openai").get("cache_mode") == "auto"


def test_profile_openrouter_explicit():
    assert get_profile("openrouter").get("cache_mode") == "explicit"


def test_profile_ollama_off():
    assert get_profile("ollama").get("cache_mode") == "off"


def test_profile_fenbi_sonnet_explicit():
    assert get_profile("fenbi-sonnet").get("cache_mode") == "explicit"


# ---------- Config 集成 ----------


def test_config_prompt_cache_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "x", "provider": "custom"})
    assert cfg.prompt_cache.mode == "auto"
    assert cfg.prompt_cache.report is True


def test_config_prompt_cache_off_via_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".mycode").mkdir()
    import json

    (tmp_path / ".mycode" / "settings.json").write_text(
        json.dumps(
            {
                "model": "x",
                "provider": "custom",
                "prompt_cache": {"mode": "off", "report": False},
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg.prompt_cache.mode == "off"
    assert cfg.prompt_cache.report is False


def test_config_prompt_cache_invalid_mode_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(SystemExit):
        load_config(
            cli_overrides={
                "model": "x",
                "provider": "custom",
                "prompt_cache": {"mode": "turbo"},  # 不在 Literal 里
            }
        )


# ---------- LLMClient cache_mode 解析 ----------


def test_llmclient_resolves_openrouter_to_explicit(tmp_path, monkeypatch):
    """openrouter profile 的 cache_mode=explicit + 用户 auto → explicit。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-x")
    cfg = load_config(
        cli_overrides={
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
        }
    )
    from mycode.llm.client import LLMClient

    client = LLMClient(cfg)
    assert client._cache_mode == "explicit"


def test_llmclient_resolves_openai_to_auto(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    cfg = load_config(cli_overrides={"provider": "openai", "model": "gpt-4o"})
    from mycode.llm.client import LLMClient

    assert LLMClient(cfg)._cache_mode == "auto"


def test_llmclient_user_off_overrides_profile_explicit(tmp_path, monkeypatch):
    """用户显式关,profile 再激进也不应走 explicit。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-x")
    cfg = load_config(
        cli_overrides={
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "prompt_cache": {"mode": "off"},
        }
    )
    from mycode.llm.client import LLMClient

    assert LLMClient(cfg)._cache_mode == "off"


# ---------- LLMResponse.cached_tokens ----------


def test_llm_response_cached_tokens_field():
    """LLMResponse dataclass 带 cached_tokens 默认 0。"""
    from mycode.llm.client import LLMResponse

    r = LLMResponse(content="x", tool_calls=[], finish_reason="stop", raw=None)  # type: ignore[arg-type]
    assert r.cached_tokens == 0
    r2 = LLMResponse(
        content="x", tool_calls=[], finish_reason="stop", raw=None, cached_tokens=42  # type: ignore[arg-type]
    )
    assert r2.cached_tokens == 42
