"""记忆文件加载器。

语义对齐 Claude Code:
- 顺序读取 config.memory_files 列表(项目级 + 用户级)
- 单文件上限 16 KiB,防止个别超长 CLAUDE.md 挤占 context
- 支持 @path/to/file 的单层引用展开(一行一条,相对当前 memory 文件目录)
- 读取失败静默跳过,不让错误 memory 阻塞启动
"""
from __future__ import annotations

import re
from pathlib import Path


MEMORY_FILE_MAX_BYTES = 16 * 1024

_REF_LINE_RE = re.compile(r"^@([^\s#].*\S)\s*$")


def _resolve(p: str, cwd: Path) -> Path:
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path


def _expand_refs(text: str, base_dir: Path, seen: set[Path]) -> str:
    """将 `@some/file.md` 单层展开为文件内容。避免循环引用。"""
    out_lines: list[str] = []
    for line in text.splitlines():
        m = _REF_LINE_RE.match(line.strip())
        if not m:
            out_lines.append(line)
            continue
        ref_path = _resolve(m.group(1), base_dir).resolve()
        if ref_path in seen or not ref_path.exists() or not ref_path.is_file():
            out_lines.append(f"[memory ref not found: {m.group(1)}]")
            continue
        seen.add(ref_path)
        try:
            raw = ref_path.read_bytes()
        except Exception:
            out_lines.append(f"[memory ref read error: {m.group(1)}]")
            continue
        if len(raw) > MEMORY_FILE_MAX_BYTES:
            out_lines.append(f"[memory ref too large: {m.group(1)}]")
            continue
        try:
            sub_text = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            out_lines.append(f"[memory ref binary: {m.group(1)}]")
            continue
        out_lines.append(f"<ref path=\"{ref_path}\">")
        out_lines.append(sub_text)
        out_lines.append("</ref>")
    return "\n".join(out_lines)


def load_memory_file(p: str, cwd: Path | None = None) -> str | None:
    """读取单个 memory 文件,返回包好的 XML 片段或 None。"""
    cwd = cwd or Path.cwd()
    path = _resolve(p, cwd)
    if not path.exists() or not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except Exception:
        return None
    if len(raw) > MEMORY_FILE_MAX_BYTES:
        return f'<memory path="{path}" truncated="true">\n[file too large: {len(raw)} bytes]\n</memory>'
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None
    if not text:
        return None
    expanded = _expand_refs(text, path.parent, seen={path.resolve()})
    return f'<memory path="{path}">\n{expanded}\n</memory>'


def load_all(memory_files: list[str], cwd: Path | None = None) -> list[str]:
    """按 memory_files 列表顺序读取,返回已包装的片段列表。缺失的静默跳过。"""
    cwd = cwd or Path.cwd()
    out: list[str] = []
    for p in memory_files:
        if snippet := load_memory_file(p, cwd):
            out.append(snippet)
    return out
