"""Shared Anthropic client factory for chapter scripts.

Keeps client creation behavior consistent while allowing optional
custom HTTP client injection (for proxies, custom transports, tests, etc.).
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from anthropic import Anthropic
import httpx


def _read_proxy_env() -> tuple[str, str, str] | None:
    """Read proxy credentials and endpoint from env.

    Supports both lowercase names requested by users and uppercase aliases.
    """
    username = (os.getenv("username") or os.getenv("PROXY_USERNAME") or "").strip()
    password = (os.getenv("password") or os.getenv("PROXY_PASSWORD") or "").strip()
    proxy_url = (os.getenv("proxy_url") or os.getenv("PROXY_URL") or "").strip()

    if not (username and password and proxy_url):
        return None
    return username, password, proxy_url


def _build_proxy_http_client_from_env() -> httpx.Client | None:
    """Build an HTTPX client with proxy auth if env is fully configured."""
    proxy_env = _read_proxy_env()
    if proxy_env is None:
        return None

    username, password, proxy_url = proxy_env
    normalized_proxy = proxy_url if "://" in proxy_url else f"http://{proxy_url}"
    parsed = urlsplit(normalized_proxy)
    if not parsed.netloc:
        return None

    # Replace any existing auth part with env-provided credentials.
    host_port = parsed.netloc.rsplit("@", 1)[-1]
    auth = f"{quote(username, safe='')}:{quote(password, safe='')}"
    netloc = f"{auth}@{host_port}"
    proxy_with_auth = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    return httpx.Client(proxy=proxy_with_auth)


def create_anthropic_client(http_client: Any | None = None) -> Anthropic:
    """Create an Anthropic client with optional custom HTTP transport.

    Args:
        http_client: Optional custom HTTPX-compatible client.

    Returns:
        Configured ``Anthropic`` client instance.
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        # Some compatible gateways don't use Anthropic auth headers.
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    kwargs: dict[str, Any] = {"base_url": base_url}

    # Priority: explicit injection > env-driven proxy injection > default transport.
    chosen_http_client = http_client if http_client is not None else _build_proxy_http_client_from_env()
    if chosen_http_client is not None:
        kwargs["http_client"] = chosen_http_client

    return Anthropic(**kwargs)
