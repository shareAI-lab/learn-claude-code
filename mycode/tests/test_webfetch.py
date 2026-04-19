"""M4-6: WebFetch 测试(用 respx mock httpx)。"""
from __future__ import annotations

import httpx
import pytest
import respx

from mycode.config import load_config
from mycode.tools.registry import ToolRegistry
from mycode.tools.web import _html_to_text, _run_webfetch, register_webfetch


# ---------- HTML → text ----------

def test_html_strips_tags():
    out = _html_to_text("<h1>Hello</h1><p>World</p>")
    assert "Hello" in out and "World" in out
    assert "<h1>" not in out


def test_html_strips_scripts_and_styles():
    out = _html_to_text(
        "<script>alert(1)</script><style>body{}</style><p>visible</p>"
    )
    assert "alert" not in out
    assert "body{}" not in out
    assert "visible" in out


def test_html_unescapes_entities():
    out = _html_to_text("<p>5 &lt; 10 &amp; 20 &gt; 15</p>")
    assert "5 < 10 & 20 > 15" in out


# ---------- URL 校验 ----------

def test_rejects_file_scheme():
    out = _run_webfetch("file:///etc/passwd")
    assert out.startswith("Error: unsupported url scheme")


def test_rejects_empty_netloc():
    out = _run_webfetch("http:///")
    assert out.startswith("Error")


# ---------- HTTP 行为(用 respx mock) ----------

@respx.mock
def test_fetch_html_page():
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(
            200,
            html="<html><body><h1>Title</h1><p>Body text.</p></body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )
    out = _run_webfetch("https://example.com/")
    assert "Status: 200" in out
    assert "Title" in out
    assert "Body text" in out
    assert "<h1>" not in out


@respx.mock
def test_fetch_plain_text_untouched():
    respx.get("https://example.com/data.txt").mock(
        return_value=httpx.Response(
            200,
            text="line1\nline2\nline3",
            headers={"content-type": "text/plain"},
        )
    )
    out = _run_webfetch("https://example.com/data.txt")
    assert "line1\nline2\nline3" in out


@respx.mock
def test_404_returns_error():
    respx.get("https://example.com/missing").mock(
        return_value=httpx.Response(404)
    )
    out = _run_webfetch("https://example.com/missing")
    assert out.startswith("Error: HTTP 404")


@respx.mock
def test_timeout_returns_error():
    respx.get("https://example.com/slow").mock(
        side_effect=httpx.TimeoutException("too slow")
    )
    out = _run_webfetch("https://example.com/slow", timeout=1)
    assert out.startswith("Error: timeout")


@respx.mock
def test_large_body_truncated():
    big = b"x" * (3 * 1024 * 1024)
    respx.get("https://example.com/big").mock(
        return_value=httpx.Response(
            200,
            content=big,
            headers={"content-type": "application/octet-stream"},
        )
    )
    out = _run_webfetch("https://example.com/big")
    assert "body truncated" in out
    # 实际返回不应包含全部 3 MB
    assert len(out) < 2.5 * 1024 * 1024


@respx.mock
def test_follows_redirects():
    respx.get("https://example.com/old").mock(
        return_value=httpx.Response(
            301, headers={"location": "https://example.com/new"}
        )
    )
    respx.get("https://example.com/new").mock(
        return_value=httpx.Response(200, text="final", headers={"content-type": "text/plain"})
    )
    out = _run_webfetch("https://example.com/old")
    assert "Status: 200" in out
    assert "final" in out


# ---------- 注册 ----------

def test_registers_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_webfetch(reg, cfg)
    t = reg.get("WebFetch")
    assert t is not None
    assert "network" in t.requires
    assert "url" in t.input_schema["properties"]
