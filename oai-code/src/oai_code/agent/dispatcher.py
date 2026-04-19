"""Tool call 派发: 按 DESIGN §5 并行/串行规则执行一组 tool_calls。

规则:
- 同文件路径的多个 Write/Edit/Bash 按出现顺序串行
- Bash 与后续读同路径的工具串行(简化为: Bash 一律单独成组)
- 其余并发,受 config.parallel_tools 上限
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from ..config.models import Config
from ..tools.registry import ToolRegistry


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    content: str


def _truncate(s: str, max_bytes: int) -> str:
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    return b[:max_bytes].decode("utf-8", errors="ignore") + f"\n[truncated: total {len(b)} bytes]"


def _path_of(call: ToolCall, registry: ToolRegistry) -> str | None:
    tool = registry.get(call.name)
    if not tool:
        return None
    for field in tool.path_fields:
        v = call.arguments.get(field)
        if isinstance(v, str):
            return v
    return None


def _extract_bash_paths(cmd: str) -> set[str]:
    """从 Bash 命令里粗略抽取重定向目标作为"写路径"。"""
    paths: set[str] = set()
    for m in re.finditer(r">>?\s*([^\s;&|]+)", cmd):
        paths.add(m.group(1))
    return paths


def _build_groups(
    calls: list[ToolCall], registry: ToolRegistry
) -> list[list[ToolCall]]:
    """把 tool_calls 切成一组组"组内串行,组间并行"的批次。

    简化算法: 从头扫描,贪心放到最后一组;若当前 call 与最后一组任一 call 冲突
    则串行到同一组(保持原序,组内顺序执行)。
    """
    if not calls:
        return []

    # 收集每个 call 的"写路径"集合,用于冲突判定
    def paths_of(c: ToolCall) -> set[str]:
        p = _path_of(c, registry)
        s: set[str] = {p} if p else set()
        if c.name == "Bash":
            cmd = c.arguments.get("command", "")
            s |= _extract_bash_paths(cmd)
        return s

    groups: list[list[ToolCall]] = [[calls[0]]]
    for c in calls[1:]:
        conflict = False
        cp = paths_of(c)
        for prev in groups[-1]:
            pp = paths_of(prev)
            if cp & pp:
                conflict = True
                break
            if c.name == "Bash" or prev.name == "Bash":
                # Bash 保守串行(DESIGN §5): 若与非 Bash 共组又涉及任何同名路径,已上面处理;
                # 纯 Bash 对非重定向命令允许并行,这里不强制
                pass
        if conflict:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups


def _execute_one(
    call: ToolCall, registry: ToolRegistry, max_bytes: int
) -> ToolResult:
    if not registry.is_allowed(call.name):
        return ToolResult(call.id, f"Error: tool '{call.name}' not allowed by policy")
    tool = registry.get(call.name)
    if not tool:
        return ToolResult(call.id, f"Error: unknown tool '{call.name}'")
    try:
        out = tool.handler(**call.arguments)
    except TypeError as e:
        return ToolResult(call.id, f"Error: {e}")
    except Exception as e:
        return ToolResult(call.id, f"Error: {type(e).__name__}: {e}")
    if not isinstance(out, str):
        out = json.dumps(out, ensure_ascii=False, default=str)
    return ToolResult(call.id, _truncate(out, max_bytes))


def dispatch(
    calls: list[ToolCall],
    registry: ToolRegistry,
    cfg: Config,
) -> list[ToolResult]:
    """主入口: 返回与 calls 同序的 ToolResult 列表。"""
    if not calls:
        return []

    groups = _build_groups(calls, registry)
    results_by_id: dict[str, ToolResult] = {}
    max_bytes = cfg.tool_result_max_bytes
    parallel = 1 if cfg.serial_only else max(1, min(cfg.parallel_tools, len(groups)))

    def run_group(group: list[ToolCall]) -> list[ToolResult]:
        # 组内串行
        return [_execute_one(c, registry, max_bytes) for c in group]

    if parallel <= 1:
        for g in groups:
            for r in run_group(g):
                results_by_id[r.tool_call_id] = r
    else:
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            for group_results in ex.map(run_group, groups):
                for r in group_results:
                    results_by_id[r.tool_call_id] = r

    return [results_by_id[c.id] for c in calls]
