from __future__ import annotations

import subprocess
from pathlib import Path

from coding_deepgent.config import load_settings

OUTPUT_LIMIT = 50_000
DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def safe_path(path_str: str, *, workdir: Path | None = None) -> Path:
    root = (workdir or load_settings().workdir).resolve()
    path = (root / path_str).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path


def bash(command: str) -> str:
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


def read_file(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"


def write_file(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as exc:  # pragma: no cover - teaching tool reports errors as output
        return f"Error: {exc}"
