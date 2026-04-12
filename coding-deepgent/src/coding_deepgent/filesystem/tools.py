from __future__ import annotations

import subprocess

from langchain.tools import tool

from .policy import OUTPUT_LIMIT, command_policy, safe_path
from .schemas import BashInput, EditFileInput, ReadFileInput, WriteFileInput


def _run_bash(command: str) -> str:
    decision = command_policy(command)
    if not decision.allowed:
        return decision.message

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=safe_path("."),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"

    output = (result.stdout + result.stderr).strip()
    return output[:OUTPUT_LIMIT] if output else "(no output)"


def _read_file(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit is not None and limit < len(lines):
            remaining = len(lines) - limit
            lines = lines[:limit] + [f"... ({remaining} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except (
        Exception
    ) as exc:  # pragma: no cover - tool errors are returned as tool output
        return f"Error: {exc}"


def _write_file(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except (
        Exception
    ) as exc:  # pragma: no cover - tool errors are returned as tool output
        return f"Error: {exc}"


def _edit_file(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except (
        Exception
    ) as exc:  # pragma: no cover - tool errors are returned as tool output
        return f"Error: {exc}"


@tool("bash", args_schema=BashInput)
def bash(command: str) -> str:
    """Run a shell command inside the current workspace."""

    return _run_bash(command)


@tool("read_file", args_schema=ReadFileInput)
def read_file(path: str, limit: int | None = None) -> str:
    """Read a workspace file, optionally limiting returned lines."""

    return _read_file(path, limit)


@tool("write_file", args_schema=WriteFileInput)
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""

    return _write_file(path, content)


@tool("edit_file", args_schema=EditFileInput)
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text fragment in a workspace file."""

    return _edit_file(path, old_text, new_text)
