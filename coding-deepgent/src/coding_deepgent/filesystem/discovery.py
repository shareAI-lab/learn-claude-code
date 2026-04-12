from __future__ import annotations

import re

from langchain.tools import tool

from .policy import OUTPUT_LIMIT, pattern_policy, safe_path
from .schemas import GlobInput, GrepInput


def _glob(pattern: str, *, limit: int = 200) -> str:
    decision = pattern_policy(pattern)
    if not decision.allowed:
        return decision.message

    root = safe_path(".")
    matches = sorted(
        path for path in root.glob(pattern) if path.is_file() or path.is_dir()
    )
    rendered = [str(path.relative_to(root)) for path in matches[:limit]]
    if len(matches) > limit:
        rendered.append(f"... ({len(matches) - limit} more matches)")
    return "\n".join(rendered)[:OUTPUT_LIMIT] if rendered else "(no matches)"


def _grep(pattern: str, *, include: str = "**/*", limit: int = 200) -> str:
    include_decision = pattern_policy(include)
    if not include_decision.allowed:
        return include_decision.message

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Error: Invalid regex: {exc}"

    root = safe_path(".")
    matches: list[str] = []

    for path in sorted(root.glob(include)):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if regex.search(line):
                matches.append(f"{path.relative_to(root)}:{line_number}:{line}")
                if len(matches) >= limit:
                    return "\n".join(matches)[:OUTPUT_LIMIT]

    return "\n".join(matches)[:OUTPUT_LIMIT] if matches else "(no matches)"


@tool("glob", args_schema=GlobInput)
def glob_search(pattern: str, limit: int = 200) -> str:
    """List workspace paths that match a glob pattern."""

    return _glob(pattern, limit=limit)


@tool("grep", args_schema=GrepInput)
def grep_search(pattern: str, include: str = "**/*", limit: int = 200) -> str:
    """Search workspace text files using a regular expression."""

    return _grep(pattern, include=include, limit=limit)
