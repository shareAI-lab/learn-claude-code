"""WebSearch 工具: 基于 bing.cn 的无 key 搜索。

解析 HTML 返回 [{title, url, snippet}, ...] 列表给模型。
- 不需要 API key
- 默认抓 10 条,最多 20 条
- 超时 15s,失败返回 Error 字符串
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import httpx

from ..config.models import Config
from .registry import Tool, ToolRegistry


DEFAULT_TIMEOUT = 15.0
DEFAULT_NUM = 10
MAX_NUM = 20

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_bing_results(body: str, limit: int) -> list[dict]:
    """解析 bing.cn 返回的 HTML。按 'class="b_algo"' 切块。"""
    results: list[dict] = []
    idx = 0
    while len(results) < limit:
        j = body.find('class="b_algo"', idx)
        if j < 0:
            break
        window = body[j: j + 3000]
        idx = j + 1

        h = re.search(
            r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            window,
            re.DOTALL,
        )
        if not h:
            continue
        url = h.group(1)
        title = _strip_tags(h.group(2))
        if not title or not url.startswith(("http://", "https://")):
            continue

        # snippet: 优先找 b_lineclamp (新版 bing) → b_caption 下的 p → 任意 p
        snippet = ""
        for pattern in (
            r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>',
            r'<div class="b_caption[^"]*"[^>]*>.*?<p[^>]*>(.*?)</p>',
            r'<p[^>]*>(.*?)</p>',
        ):
            s = re.search(pattern, window, re.DOTALL)
            if s:
                snippet = _strip_tags(s.group(1))
                if snippet:
                    break

        results.append({"title": title[:200], "url": url, "snippet": snippet[:300]})
    return results


def _run_web_search(
    query: str,
    num: int | None = None,
    timeout: float | None = None,
    client_factory=None,
) -> str:
    query = (query or "").strip()
    if not query:
        return "Error: query is empty"
    n = max(1, min(int(num or DEFAULT_NUM), MAX_NUM))
    t = timeout or DEFAULT_TIMEOUT

    factory = client_factory or (
        lambda: httpx.Client(
            follow_redirects=True,
            timeout=t,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "zh-CN,en;q=0.8"},
        )
    )

    try:
        with factory() as client:
            resp = client.get(
                "https://cn.bing.com/search",
                params={"q": query, "form": "QBLH"},
            )
    except httpx.TimeoutException:
        return f"Error: timeout after {t}s"
    except httpx.HTTPError as e:
        return f"Error: {type(e).__name__}: {e}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

    if resp.status_code >= 400:
        return f"Error: HTTP {resp.status_code} {resp.reason_phrase}"

    results = _parse_bing_results(resp.text, n)
    if not results:
        return f"(no results for: {query})"

    lines = [f"Search results for: {query}"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet']}")
    return "\n".join(lines)


def register_web_search(registry: ToolRegistry, cfg: Config) -> None:
    registry.register(
        Tool(
            name="WebSearch",
            description=(
                "Search the web and return a list of results (title + URL + snippet). "
                "Powered by bing.cn (no API key required). "
                "Use for finding recent documentation, discussion threads, or when "
                "internal knowledge is stale. Up to 20 results per query."
            ),
            requires=["network"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_NUM,
                        "default": DEFAULT_NUM,
                    },
                    "timeout": {"type": "number", "minimum": 1, "maximum": 60},
                },
                "required": ["query"],
            },
            handler=lambda **kw: _run_web_search(
                kw["query"], kw.get("num"), kw.get("timeout")
            ),
        )
    )
