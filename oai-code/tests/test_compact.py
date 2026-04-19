"""M1-6: 上下文压缩测试 (microcompact + auto-compact + roles)。"""
from __future__ import annotations

import json
from pathlib import Path

from oai_code.config import load_config
from oai_code.context import (
    auto_compact,
    estimate_tokens,
    microcompact,
    should_auto_compact,
)


def _cfg(tmp_path, monkeypatch, **over):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    return load_config(
        cli_overrides={"model": "test", "provider": "custom", **over}
    )


def test_microcompact_skips_when_few_tools(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok"},
        {"role": "tool", "tool_call_id": "a", "content": "x" * 10000},
    ]
    evicted = microcompact(messages, cfg)
    assert evicted == 0
    assert "x" * 1000 in messages[-1]["content"]


def test_microcompact_evicts_old_large(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    big = "y" * 10_000
    small = "short"
    messages = [{"role": "system", "content": "sys"}]
    # 造 5 条 tool_result,最早 2 条应被外置(keep_recent_tool_results=3)
    for i in range(5):
        messages.append({"role": "assistant", "content": "thinking"})
        messages.append(
            {
                "role": "tool",
                "tool_call_id": f"t{i}",
                "content": big if i < 2 else small,
            }
        )
    evicted = microcompact(messages, cfg)
    assert evicted == 2
    # blob 文件应存在
    blobs = list((tmp_path / ".oaic" / "blobs").glob("*.txt"))
    assert len(blobs) >= 1
    # 被外置的 tool_result 内容被改写
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert tool_msgs[0]["content"].startswith("[evicted")
    assert tool_msgs[1]["content"].startswith("[evicted")
    # 最近 3 条保留原样(最后一条是 small)
    assert tool_msgs[-1]["content"] == small


def test_microcompact_below_threshold_not_evicted(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    messages = [{"role": "system", "content": "sys"}]
    for i in range(5):
        messages.append({"role": "tool", "tool_call_id": f"t{i}", "content": "tiny"})
    evicted = microcompact(messages, cfg)
    assert evicted == 0


def test_estimate_tokens():
    msgs = [{"role": "user", "content": "x" * 400}]
    t = estimate_tokens(msgs)
    assert t > 80  # 粗略 4 字符/token,应该 ~100


def test_should_auto_compact_threshold(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch, context_window=1000)
    # 1000 * 75% = 750 tokens ≈ 3000 chars
    small = [{"role": "user", "content": "hi"}]
    assert not should_auto_compact(small, cfg)
    big = [{"role": "user", "content": "x" * 5000}]
    assert should_auto_compact(big, cfg)


class _StubLLM:
    def call(self, messages, tools=None):
        class R:
            content = "summary of prior conversation"
            tool_calls: list = []
            finish_reason = "stop"
            raw = None
        return R()


def test_auto_compact_produces_summary(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    messages = [
        {"role": "system", "content": "sys"},
        *[
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(20)
        ],
    ]
    new = auto_compact(messages, cfg, _StubLLM())
    # system 保留
    assert new[0]["role"] == "system"
    # 紧随一条 compacted
    assert "<compacted" in new[1]["content"]
    assert "summary" in new[1]["content"]
    # tail 保留 6 条
    assert len(new) == 1 + 1 + 6
    # transcript 落盘
    dumps = list((tmp_path / ".oaic" / "transcripts").glob("*.jsonl"))
    assert len(dumps) == 1


def test_roles_derive_for_summarize(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(
        cli_overrides={
            "provider": "fenbi",
            "roles": {"summarize": {"provider": "fenbi-mini"}},
        }
    )
    main = cfg.derive_for_role("main")
    summ = cfg.derive_for_role("summarize")
    assert main.model == "pa/gpt-5.4"
    assert summ.model == "pa/gpt-5.4-mini"
    assert summ.base_url == main.base_url


def test_roles_role_inherits_when_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"provider": "fenbi"})
    sub = cfg.derive_for_role("subagent")
    # 无 roles.subagent 覆盖时,应完全继承顶层
    assert sub.model == cfg.model
    assert sub.base_url == cfg.base_url
    assert sub.provider == cfg.provider


def test_roles_partial_override_model_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(
        cli_overrides={
            "provider": "fenbi",
            "roles": {"subagent": {"model": "pa/claude-sonnet-4-6"}},
        }
    )
    sub = cfg.derive_for_role("subagent")
    assert sub.model == "pa/claude-sonnet-4-6"
    # base_url / provider 继承顶层 fenbi
    assert sub.base_url == cfg.base_url
