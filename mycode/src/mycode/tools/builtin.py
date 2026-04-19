"""M0 内置工具: Bash / Read / Write / Edit / Glob / Grep。

严格按 TOOLS.md §1-§2 的 schema 与错误串约定实现。
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path

from ..config.models import Config
from .registry import Tool, ToolRegistry
from .safety import PathDeniedError, safe_path


# ---------- 全局状态: 被 Read 过的文件,用于 Write 防误覆盖 ----------
_read_in_session: set[str] = set()


def reset_session_state() -> None:
    _read_in_session.clear()


# ---------- Bash ----------

_BASH_DENY = [
    r"\brm\s+-rf\s+/(?!\S)",
    r"\brm\s+-rf\s+~(?!\S|/\w)",
    r"\brm\s+-rf\s+\$HOME\b",
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bmkfs\b",
    r">\s*/dev/sd",
    r"\bdd\s+of=/dev/",
]


def _bash_blocked(cmd: str, cfg: Config) -> str | None:
    patterns = _BASH_DENY + cfg.bash_deny_patterns
    for pat in patterns:
        if re.search(pat, cmd):
            return f"Error: command blocked by deny-list pattern: {pat}"
    return None


def _run_bash(cfg: Config, command: str, timeout: int = 120, description: str = "") -> str:
    if blocked := _bash_blocked(command, cfg):
        return blocked
    timeout = min(max(int(timeout), 1), 600)
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=cfg.workspace_root(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        out += f"\n[exit code: {r.returncode}]"
    return out.rstrip("\n") or "(no output)"


# ---------- Read ----------

_TEXT_MAX_BYTES = 256 * 1024
_TEXT_MAX_LINES = 5000


def _is_binary(data: bytes) -> bool:
    # 简单 heuristic: 前 4096 字节里有 NUL 或大量非可打印字符则视为二进制
    sample = data[:4096]
    if b"\x00" in sample:
        return True
    printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126 or b >= 128)
    return len(sample) > 0 and printable / len(sample) < 0.7


def _run_read(cfg: Config, file_path: str, offset: int = 0, limit: int | None = None) -> str:
    try:
        path = safe_path(file_path, cfg)
    except PathDeniedError as e:
        return f"Error: {e}"
    if not path.exists():
        return f"Error: file not found: {file_path}"
    if not path.is_file():
        return f"Error: not a regular file: {file_path}"
    try:
        raw = path.read_bytes()
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    if len(raw) > _TEXT_MAX_BYTES or _is_binary(raw):
        return f"[binary or too large, {len(raw)} bytes]"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return f"[binary or too large, {len(raw)} bytes]"
    lines = text.splitlines()
    total = len(lines)
    start = max(0, int(offset))
    end = total if limit is None else min(total, start + int(limit))
    end = min(end, start + _TEXT_MAX_LINES)
    out: list[str] = []
    for i in range(start, end):
        out.append(f"{i + 1:>6}\t{lines[i]}")
    if end < total:
        out.append(f"... ({total - end} more lines)")
    _read_in_session.add(str(path))
    return "\n".join(out) if out else "(empty)"


# ---------- Write ----------

def _run_write(cfg: Config, file_path: str, content: str) -> str:
    try:
        path = safe_path(file_path, cfg)
    except PathDeniedError as e:
        return f"Error: {e}"
    if path.exists() and str(path) not in _read_in_session:
        return f"Error: must Read file before overwriting: {file_path}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    _read_in_session.add(str(path))
    return f"Wrote {len(content)} bytes to {file_path}"


# ---------- Edit ----------

def _run_multi_edit(
    cfg: Config,
    file_path: str,
    edits: list[dict],
) -> str:
    """M4-4: 对单文件做多处 edit,原子性:全部成功才写盘。

    edits 列表按顺序应用,前一次修改的结果作为后一次的输入。
    任何一个 old_string 找不到 / 多次匹配且未开 replace_all → 整体回滚。
    """
    try:
        path = safe_path(file_path, cfg)
    except PathDeniedError as e:
        return f"Error: {e}"
    if not path.exists():
        return f"Error: file not found: {file_path}"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

    if not isinstance(edits, list) or not edits:
        return "Error: edits must be a non-empty list"

    working = text
    replaced_counts: list[int] = []
    for i, ed in enumerate(edits):
        if not isinstance(ed, dict):
            return f"Error: edits[{i}] must be object"
        old = ed.get("old_string")
        new = ed.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str):
            return f"Error: edits[{i}] missing old_string/new_string"
        replace_all = bool(ed.get("replace_all", False))
        cnt = working.count(old)
        if cnt == 0:
            return f"Error: edits[{i}] old_string not found"
        if cnt > 1 and not replace_all:
            return (
                f"Error: edits[{i}] old_string matched {cnt} times; "
                f"pass more context or set replace_all"
            )
        if replace_all:
            working = working.replace(old, new)
            replaced_counts.append(cnt)
        else:
            working = working.replace(old, new, 1)
            replaced_counts.append(1)

    try:
        path.write_text(working, encoding="utf-8")
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    total = sum(replaced_counts)
    return f"MultiEdit applied {len(edits)} edits ({total} replacements) to {file_path}"


def _run_edit(
    cfg: Config,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    try:
        path = safe_path(file_path, cfg)
    except PathDeniedError as e:
        return f"Error: {e}"
    if not path.exists():
        return f"Error: file not found: {file_path}"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    count = text.count(old_string)
    if count == 0:
        return "Error: old_string not found"
    if count > 1 and not replace_all:
        return f"Error: old_string matched {count} times; pass more context or set replace_all"
    new_text = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
    try:
        path.write_text(new_text, encoding="utf-8")
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    return f"Edited {file_path} ({count if replace_all else 1} replacement)"


# ---------- Glob ----------

def _run_glob(cfg: Config, pattern: str, path: str | None = None) -> str:
    root = cfg.workspace_root()
    if path:
        try:
            root = safe_path(path, cfg)
        except PathDeniedError as e:
            return f"Error: {e}"
    try:
        matches = sorted(
            root.glob(pattern),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    rel = []
    for p in matches[:500]:
        try:
            rel.append(str(p.relative_to(root)))
        except ValueError:
            rel.append(str(p))
    if len(matches) > 500:
        rel.append(f"... ({len(matches) - 500} more)")
    return "\n".join(rel) if rel else "(no matches)"


# ---------- Grep ----------

def _run_grep(
    cfg: Config,
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    output_mode: str = "files_with_matches",
    case_insensitive: bool = False,
    line_numbers: bool = True,
    context: int = 0,
    head_limit: int = 250,
) -> str:
    # 优先尝试 rg,否则退化到 python re
    cmd_path = cfg.workspace_root()
    if path:
        try:
            cmd_path = safe_path(path, cfg)
        except PathDeniedError as e:
            return f"Error: {e}"

    args = ["rg", "--color=never"]
    if case_insensitive:
        args.append("-i")
    if output_mode == "files_with_matches":
        args.append("--files-with-matches")
    elif output_mode == "count":
        args.append("--count")
    else:  # content
        if line_numbers:
            args.append("-n")
        if context > 0:
            args.extend(["-C", str(context)])
    if glob:
        args.extend(["--glob", glob])
    args.append(pattern)
    args.append(str(cmd_path))

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return _grep_python_fallback(
            cmd_path, pattern, glob, output_mode, case_insensitive, line_numbers, head_limit
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (30s)"
    out_lines = (r.stdout or "").splitlines()
    if head_limit and head_limit > 0:
        out_lines = out_lines[:head_limit]
    return "\n".join(out_lines) if out_lines else "(no matches)"


def _grep_python_fallback(
    root: Path,
    pattern: str,
    glob: str | None,
    output_mode: str,
    ci: bool,
    line_numbers: bool,
    head_limit: int,
) -> str:
    flags = re.IGNORECASE if ci else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: invalid regex: {e}"
    collected: list[str] = []
    counts: dict[Path, int] = {}
    files = [p for p in root.rglob("*") if p.is_file()]
    for p in files:
        if glob and not fnmatch.fnmatch(p.name, glob):
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if rx.search(line):
                    counts[p] = counts.get(p, 0) + 1
                    if output_mode == "content":
                        prefix = f"{p}:{i}:" if line_numbers else f"{p}:"
                        collected.append(f"{prefix}{line}")
        except Exception:
            continue
    if output_mode == "files_with_matches":
        collected = [str(p) for p in counts]
    elif output_mode == "count":
        collected = [f"{p}:{c}" for p, c in counts.items()]
    if head_limit and head_limit > 0:
        collected = collected[:head_limit]
    return "\n".join(collected) if collected else "(no matches)"


# ---------- register all ----------

def register_builtins(registry: ToolRegistry) -> None:
    cfg = registry.cfg

    registry.register(
        Tool(
            name="Bash",
            description="Run a shell command in the workspace.",
            requires=["exec"],
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 120, "maximum": 600},
                    "description": {"type": "string"},
                },
                "required": ["command"],
            },
            handler=lambda **kw: _run_bash(
                cfg, kw["command"], kw.get("timeout", 120), kw.get("description", "")
            ),
        )
    )

    registry.register(
        Tool(
            name="Read",
            description="Read a text file with 1-based line-number prefix.",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "offset": {"type": "integer", "minimum": 0},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 5000},
                },
                "required": ["file_path"],
            },
            handler=lambda **kw: _run_read(
                cfg, kw["file_path"], kw.get("offset", 0), kw.get("limit")
            ),
            path_fields=("file_path",),
        )
    )

    registry.register(
        Tool(
            name="Write",
            description="Overwrite a file. Must have Read the file in this session first (new files exempt).",
            requires=["write"],
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
            handler=lambda **kw: _run_write(cfg, kw["file_path"], kw["content"]),
            path_fields=("file_path",),
        )
    )

    registry.register(
        Tool(
            name="Edit",
            description="Replace exact text in a file. old_string must match exactly once unless replace_all=true.",
            requires=["write"],
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean", "default": False},
                },
                "required": ["file_path", "old_string", "new_string"],
            },
            handler=lambda **kw: _run_edit(
                cfg,
                kw["file_path"],
                kw["old_string"],
                kw["new_string"],
                kw.get("replace_all", False),
            ),
            path_fields=("file_path",),
        )
    )

    registry.register(
        Tool(
            name="MultiEdit",
            description=(
                "Apply multiple Edit operations to a single file atomically. "
                "All edits succeed or none are written. Each edit has the same "
                "semantics as the Edit tool. Order matters: later edits see the "
                "output of earlier ones."
            ),
            requires=["write"],
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "edits": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_string": {"type": "string"},
                                "new_string": {"type": "string"},
                                "replace_all": {"type": "boolean", "default": False},
                            },
                            "required": ["old_string", "new_string"],
                        },
                    },
                },
                "required": ["file_path", "edits"],
            },
            handler=lambda **kw: _run_multi_edit(cfg, kw["file_path"], kw["edits"]),
            path_fields=("file_path",),
        )
    )

    registry.register(
        Tool(
            name="Glob",
            description="Find files by glob pattern, sorted by mtime desc.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
            handler=lambda **kw: _run_glob(cfg, kw["pattern"], kw.get("path")),
        )
    )

    registry.register(
        Tool(
            name="Grep",
            description="Search file contents via ripgrep (fallback to python re).",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "output_mode": {
                        "type": "string",
                        "enum": ["files_with_matches", "content", "count"],
                    },
                    "case_insensitive": {"type": "boolean"},
                    "line_numbers": {"type": "boolean"},
                    "context": {"type": "integer"},
                    "head_limit": {"type": "integer"},
                },
                "required": ["pattern"],
            },
            handler=lambda **kw: _run_grep(
                cfg,
                kw["pattern"],
                kw.get("path"),
                kw.get("glob"),
                kw.get("output_mode", "files_with_matches"),
                kw.get("case_insensitive", False),
                kw.get("line_numbers", True),
                kw.get("context", 0),
                kw.get("head_limit", 250),
            ),
        )
    )
