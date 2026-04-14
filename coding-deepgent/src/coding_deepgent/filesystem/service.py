from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import re

from coding_deepgent.filesystem.policy import (
    OUTPUT_LIMIT,
    command_policy,
    pattern_policy,
    safe_path,
)


@dataclass(frozen=True, slots=True)
class FilesystemRuntime:
    workdir: Path
    trusted_workdirs: tuple[Path, ...] = ()


def resolve_runtime(
    *,
    workdir: Path,
    trusted_workdirs: Iterable[Path] = (),
) -> FilesystemRuntime:
    return FilesystemRuntime(
        workdir=workdir.expanduser().resolve(),
        trusted_workdirs=tuple(path.expanduser().resolve() for path in trusted_workdirs),
    )


def runtime_from_context(context: object) -> FilesystemRuntime:
    workdir = getattr(context, "workdir", None)
    if workdir is None:
        raise RuntimeError("Filesystem tools require runtime workdir")
    trusted_workdirs = tuple(getattr(context, "trusted_workdirs", ()))
    return resolve_runtime(
        workdir=workdir,
        trusted_workdirs=trusted_workdirs,
    )


def _safe_path(runtime: FilesystemRuntime, path: str) -> Path:
    return safe_path(
        path,
        workdir=runtime.workdir,
        additional_workdirs=runtime.trusted_workdirs,
    )


def run_bash(runtime: FilesystemRuntime, command: str) -> str:
    decision = command_policy(command)
    if not decision.allowed:
        return decision.message

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=_safe_path(runtime, "."),
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


def read_workspace_file(runtime: FilesystemRuntime, path: str, limit: int | None = None) -> str:
    try:
        lines = _safe_path(runtime, path).read_text(encoding="utf-8").splitlines()
        if limit is not None and limit < len(lines):
            remaining = len(lines) - limit
            lines = lines[:limit] + [f"... ({remaining} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except Exception as exc:  # pragma: no cover
        return f"Error: {exc}"


def write_workspace_file(runtime: FilesystemRuntime, path: str, content: str) -> str:
    try:
        file_path = _safe_path(runtime, path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:  # pragma: no cover
        return f"Error: {exc}"


def edit_workspace_file(runtime: FilesystemRuntime, path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = _safe_path(runtime, path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as exc:  # pragma: no cover
        return f"Error: {exc}"


def glob_workspace_paths(
    runtime: FilesystemRuntime,
    pattern: str,
    *,
    limit: int = 200,
) -> str:
    decision = pattern_policy(pattern)
    if not decision.allowed:
        return decision.message

    root = _safe_path(runtime, ".")
    matches = sorted(
        path for path in root.glob(pattern) if path.is_file() or path.is_dir()
    )
    rendered = [str(path.relative_to(root)) for path in matches[:limit]]
    if len(matches) > limit:
        rendered.append(f"... ({len(matches) - limit} more matches)")
    return "\n".join(rendered)[:OUTPUT_LIMIT] if rendered else "(no matches)"


def grep_workspace_files(
    runtime: FilesystemRuntime,
    pattern: str,
    *,
    include: str = "**/*",
    limit: int = 200,
) -> str:
    include_decision = pattern_policy(include)
    if not include_decision.allowed:
        return include_decision.message

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Error: Invalid regex: {exc}"

    root = _safe_path(runtime, ".")
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
