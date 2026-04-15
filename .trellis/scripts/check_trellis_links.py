#!/usr/bin/env python3
"""Smoke-check local Markdown links inside .trellis docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[2]
TRELLIS_ROOT = REPO_ROOT / ".trellis"
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _target_path(source: Path, raw: str) -> Path | None:
    target = raw.strip()
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    target = target.split("#", 1)[0].strip()
    if not target:
        return None
    target = unquote(target)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    path = Path(target)
    if path.is_absolute():
        return path
    return (source.parent / path).resolve()


def main() -> int:
    failures: list[str] = []
    for source in sorted(TRELLIS_ROOT.rglob("*.md")):
        text = source.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = _target_path(source, match.group(1))
            if target is None:
                continue
            if not target.exists():
                rel_source = source.relative_to(REPO_ROOT)
                failures.append(f"{rel_source}: missing link target {match.group(1)}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Trellis markdown links OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
