"""M6-1: WebSearch 工具测试(respx mock bing.cn)。"""
from __future__ import annotations

import httpx
import pytest
import respx

from mycode.config import load_config
from mycode.tools.registry import ToolRegistry
from mycode.tools.web_search import (
    _parse_bing_results,
    _run_web_search,
    register_web_search,
)


# 模拟的 bing.cn 结果页 HTML 片段(简化但结构真实)
_BING_HTML = """<!DOCTYPE html><html><body>
<ol id="b_results">
<li class="b_algo">
  <h2><a href="https://example.com/one" h="ID=SERP">Example One — Title</a></h2>
  <div class="b_caption">
    <p class="b_lineclamp2 b_algoSlug">First snippet body text here.</p>
  </div>
</li>
<li class="b_algo">
  <h2><a href="https://example.com/two" h="ID=SERP,2">Example Two 第二个</a></h2>
  <div class="b_caption">
    <p>Second snippet in old shape.</p>
  </div>
</li>
<li class="b_algo">
  <h2><a href="javascript:void(0)">Bad Link</a></h2>
  <p>This should be skipped(not http url).</p>
</li>
<li class="b_algo">
  <h2><a href="https://example.com/three">Example Three</a></h2>
  <!-- 没有 snippet -->
</li>
</ol>
</body></html>"""


# ---------- 解析器 ----------


def test_parse_extracts_title_url_snippet():
    results = _parse_bing_results(_BING_HTML, limit=10)
    assert len(results) == 3  # 非 http 那条被过滤
    assert results[0]["title"] == "Example One — Title"
    assert results[0]["url"] == "https://example.com/one"
    assert "First snippet" in results[0]["snippet"]


def test_parse_respects_limit():
    results = _parse_bing_results(_BING_HTML, limit=2)
    assert len(results) == 2


def test_parse_handles_missing_snippet():
    results = _parse_bing_results(_BING_HTML, limit=10)
    third = results[2]
    assert third["title"] == "Example Three"
    # 没 snippet 时返回空串或空白,不崩
    assert isinstance(third["snippet"], str)


def test_parse_skips_non_http_urls():
    results = _parse_bing_results(_BING_HTML, limit=10)
    urls = [r["url"] for r in results]
    assert all(u.startswith(("http://", "https://")) for u in urls)
    assert "javascript:void(0)" not in urls


def test_parse_strips_html_tags_from_title():
    html = '<li class="b_algo"><h2><a href="https://x.com">Title <strong>bold</strong> here</a></h2><p>s</p></li>'
    results = _parse_bing_results(html, limit=10)
    assert results[0]["title"] == "Title bold here"


def test_parse_handles_empty_body():
    assert _parse_bing_results("<html></html>", limit=10) == []


# ---------- 端到端(respx) ----------


@respx.mock
def test_search_happy_path():
    respx.get("https://cn.bing.com/search").mock(
        return_value=httpx.Response(200, text=_BING_HTML)
    )
    out = _run_web_search("python requests")
    assert "Search results for: python requests" in out
    assert "1. Example One" in out
    assert "https://example.com/one" in out
    assert "First snippet" in out


@respx.mock
def test_empty_query_rejected():
    out = _run_web_search("   ")
    assert out.startswith("Error: query is empty")


@respx.mock
def test_timeout_returns_error():
    respx.get("https://cn.bing.com/search").mock(
        side_effect=httpx.TimeoutException("too slow")
    )
    out = _run_web_search("something", timeout=1)
    assert out.startswith("Error: timeout")


@respx.mock
def test_http_error_returns_error():
    respx.get("https://cn.bing.com/search").mock(
        return_value=httpx.Response(503)
    )
    out = _run_web_search("x")
    assert out.startswith("Error: HTTP 503")


@respx.mock
def test_no_results_graceful():
    respx.get("https://cn.bing.com/search").mock(
        return_value=httpx.Response(200, text="<html><body>Empty page</body></html>")
    )
    out = _run_web_search("rare-query-xyz")
    assert "(no results for:" in out


@respx.mock
def test_num_limit_respected():
    respx.get("https://cn.bing.com/search").mock(
        return_value=httpx.Response(200, text=_BING_HTML)
    )
    out = _run_web_search("q", num=2)
    # 只应有 1. 和 2.,没有 3.
    assert "1." in out and "2." in out
    assert "3." not in out


@respx.mock
def test_num_clamped_to_bounds():
    """num=0 或 num=999 都应被 clamp 到 1..20 而不是崩。"""
    respx.get("https://cn.bing.com/search").mock(
        return_value=httpx.Response(200, text=_BING_HTML)
    )
    # num=0 → 1
    out = _run_web_search("q", num=0)
    assert not out.startswith("Error")
    # num=999 → 20
    out = _run_web_search("q", num=999)
    assert not out.startswith("Error")


# ---------- registry 注册 ----------


def test_registers_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_web_search(reg, cfg)
    t = reg.get("WebSearch")
    assert t is not None
    assert "network" in t.requires
    assert "query" in t.input_schema["properties"]
