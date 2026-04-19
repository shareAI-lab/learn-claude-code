"""WebFetch 工具: 拉取 URL,HTML → 纯文本,返回给模型。

简化版:
- 仅支持 http / https
- 超时 30s,体积上限 2 MiB,下载后截到 tool_result_max_bytes
- HTML 用简单正则去 script/style 再抽文本,不引入 BeautifulSoup
- 失败 / 非 2xx → Error: 字符串
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import httpx

from ..config.models import Config
from .registry import Tool, ToolRegistry


MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
DEFAULT_TIMEOUT = 30.0
ALLOWED_SCHEMES = {"http", "https"}

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def _html_to_text(body: str) -> str:
    body = _SCRIPT_STYLE_RE.sub("", body)
    body = _TAG_RE.sub("", body)
    body = html.unescape(body)
    body = _WS_RE.sub(" ", body)
    body = _MULTI_NL_RE.sub("\n\n", body)
    return body.strip()


def _run_webfetch(url: str, timeout: float | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return f"Error: unsupported url scheme '{parsed.scheme}' (allowed: http/https)"
    if not parsed.netloc:
        return f"Error: invalid url '{url}'"
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout or DEFAULT_TIMEOUT,
            headers={"User-Agent": "oai-code/0.1 (+https://github.com/zhouyunfei/oai-code)"},
        ) as client:
            resp = client.get(url)
    except httpx.TimeoutException:
        return f"Error: timeout after {timeout or DEFAULT_TIMEOUT}s"
    except httpx.HTTPError as e:
        return f"Error: {type(e).__name__}: {e}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

    if resp.status_code >= 400:
        return f"Error: HTTP {resp.status_code} {resp.reason_phrase}"

    content = resp.content[:MAX_BYTES]
    truncated = len(resp.content) > MAX_BYTES
    ctype = resp.headers.get("content-type", "").lower()
    try:
        text = content.decode(resp.encoding or "utf-8", errors="replace")
    except LookupError:
        text = content.decode("utf-8", errors="replace")

    if "text/html" in ctype or text.lstrip().startswith(("<!DOCTYPE", "<html", "<!doctype")):
        text = _html_to_text(text)

    header = f"URL: {resp.url}\nStatus: {resp.status_code}\nContent-Type: {ctype}\n"
    if truncated:
        header += f"[body truncated to {MAX_BYTES} bytes]\n"
    return header + "\n" + text


def register_webfetch(registry: ToolRegistry, cfg: Config) -> None:
    registry.register(
        Tool(
            name="WebFetch",
            description=(
                "Fetch a URL (http/https) and return the page as plain text. "
                "HTML pages are stripped of script/style/tags. Max 2 MiB, 30s timeout. "
                "Use for reading docs, GitHub READMEs, API reference pages."
            ),
            requires=["network"],
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout": {"type": "number", "minimum": 1, "maximum": 120},
                },
                "required": ["url"],
            },
            handler=lambda **kw: _run_webfetch(kw["url"], kw.get("timeout")),
        )
    )
