"""路径安全与脱敏工具。"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from ..config.models import Config


class PathDeniedError(Exception):
    """路径命中 denied_paths 或越界。"""


def safe_path(p: str, cfg: Config) -> Path:
    """解析相对路径为绝对路径,并校验是否命中黑名单/是否越界。

    规则对应 TOOLS.md §0.6。
    """
    workspace = cfg.workspace_root()
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = (workspace / path).resolve()
    else:
        path = path.resolve()

    # denied_paths 检查
    str_path = str(path)
    home = str(Path.home())
    for pattern in cfg.denied_paths:
        expanded = pattern.replace("~", home)
        if fnmatch.fnmatch(str_path, expanded) or str_path.startswith(expanded.rstrip("/*")):
            raise PathDeniedError(f"path '{p}' is denied by policy")

    # workspace 越界
    if not cfg.allow_outside_workspace:
        try:
            path.relative_to(workspace.resolve())
        except ValueError:
            raise PathDeniedError(f"path '{p}' escapes workspace")

    return path


# --- 日志脱敏 ---

_REDACT_PATTERNS = [
    # Bearer token
    (re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]{8,})", re.IGNORECASE), r"\1[REDACTED]"),
    # Authorization: xxx
    (re.compile(r'("?[Aa]uthorization"?\s*[:=]\s*"?)([^"\s,}]+)'), r"\1[REDACTED]"),
    # api_key / api-key / openai_api_key = "xxx"
    (
        re.compile(
            r'("?(?:openai_)?api[_-]?key"?\s*[:=]\s*"?)([A-Za-z0-9_\-]{8,})',
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    # sk-xxxxxxx 常见 key 前缀
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{8,})\b"), "[REDACTED]"),
    (re.compile(r"\b(fb-[A-Za-z0-9_\-]{8,})\b"), "[REDACTED]"),
]


def redact(text: str) -> str:
    """对字符串做脱敏,用于 session / 日志写入前。"""
    out = text
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out
