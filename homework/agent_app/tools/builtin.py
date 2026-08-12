"""Path-safe builtin tool implementations.

Every operation receives its allowed workspace root explicitly so importing this
module has no dependency on application configuration or process state.
"""

from __future__ import annotations

import glob
import subprocess
from pathlib import Path


def resolve_tool_cwd(workdir: Path, cwd: str | Path | None = None) -> Path:
    workspace_root = workdir.resolve()
    base = Path(cwd).resolve() if cwd else workspace_root

    if not base.is_relative_to(workspace_root):
        raise ValueError(f"Tool cwd escapes workspace: {cwd}")
    if not base.is_dir():
        raise ValueError(f"Tool cwd does not exist: {base}")
    return base


def safe_path(
    workdir: Path, path: str, cwd: str | Path | None = None
) -> Path:
    base = resolve_tool_cwd(workdir, cwd)
    resolved = (base / path).resolve()

    if not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes working directory: {path}")
    return resolved


def run_bash(
    workdir: Path,
    command: str,
    run_in_background: bool = False,
    cwd: str | Path | None = None,
) -> str:
    try:
        base = resolve_tool_cwd(workdir, cwd)
        result = subprocess.run(
            command,
            shell=True,
            cwd=base,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as exc:
        return f"Error: {exc}"


def run_read(
    workdir: Path,
    path: str,
    offset: int = 0,
    limit: int | None = None,
    cwd: str | Path | None = None,
) -> str:
    try:
        lines = safe_path(workdir, path, cwd=cwd).read_text().splitlines()
        offset = max(0, offset)
        limit = 1000 if limit is None else max(1, min(limit, 1000))
        end = min(offset + limit, len(lines))
        result = lines[offset:end]
        if end < len(lines):
            result.append(
                f"... ({len(lines) - end} more lines);continue with offset={end}"
            )
        return "\n".join(result)
    except Exception as exc:
        return f"Error: {exc}"


def run_write(
    workdir: Path, path: str, content: str, cwd: str | Path | None = None
) -> str:
    try:
        file_path = safe_path(workdir, path, cwd=cwd)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"


def run_edit(
    workdir: Path,
    path: str,
    old_text: str,
    new_text: str,
    cwd: str | Path | None = None,
) -> str:
    try:
        file_path = safe_path(workdir, path, cwd=cwd)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as exc:
        return f"Error: {exc}"


def run_glob(workdir: Path, pattern: str, cwd: str | Path | None = None) -> str:
    try:
        base = resolve_tool_cwd(workdir, cwd)
        results = []
        for match in glob.glob(pattern, root_dir=base):
            path = (base / match).resolve()
            if path.is_relative_to(base):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as exc:
        return f"Error: {exc}"
