"""脱敏测试 (DESIGN.md §10: 日志 / session 不泄漏 key / .env)。"""
from __future__ import annotations

from oai_code.tools.safety import redact


def test_redact_bearer_token():
    s = 'Authorization: Bearer fb-bF8oKzdmN2JlZWIyMzc1Y2E5ZTliOGE1YzIyM2U4NTcwMDg0'
    out = redact(s)
    assert "fb-bF8oKzdmN2JlZWIyMzc1Y2E5ZTliOGE1YzIyM2U4NTcwMDg0" not in out
    assert "[REDACTED]" in out


def test_redact_sk_prefix():
    s = "OPENAI_API_KEY=sk-abcdef0123456789"
    out = redact(s)
    assert "sk-abcdef0123456789" not in out


def test_redact_quoted_api_key_json():
    s = '{"api_key": "supersecretvalue123"}'
    out = redact(s)
    assert "supersecretvalue123" not in out
    assert "[REDACTED]" in out


def test_redact_leaves_ordinary_text():
    s = "just an error: file not found"
    assert redact(s) == s
