from __future__ import annotations

import subprocess
from pathlib import Path

from langchain.tools import tool

from coding_deepgent.config import load_settings

OUTPUT_LIMIT = 50_000
DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def safe_path(path_str: str, *, workdir: Path | None = None) -> Path:
    """Resolve a path within the current coding-deepgent workspace."""

    root = (workdir or load_settings().workdir).resolve()
    path = (root / path_str).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path


def _run_bash(command: str) -> str:
    """Implementation helper for the bash tool."""

    if any(item in command for item in DANGEROUS_COMMANDS):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=load_settings().workdir,
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
    """Implementation helper for the read_file tool."""

    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"


def _write_file(path: str, content: str) -> str:
    """Implementation helper for the write_file tool."""

    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"


def _edit_file(path: str, old_text: str, new_text: str) -> str:
    """Implementation helper for the edit_file tool."""

    try:
        file_path = safe_path(path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"


@tool("bash")
def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    return _run_bash(command)


@tool("read_file")
def read_file(path: str, limit: int | None = None) -> str:
    """Read a workspace file, optionally limiting returned lines."""

    return _read_file(path, limit)


@tool("write_file")
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""

    return _write_file(path, content)


@tool("edit_file")
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text fragment in a workspace file."""

    return _edit_file(path, old_text, new_text)
