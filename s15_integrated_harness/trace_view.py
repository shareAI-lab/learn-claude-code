#!/usr/bin/env python3
"""Render an integrated-harness JSONL trace as metrics, a tree, and a timeline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


START_TO_END = {
    "agent_start": {"agent_end"},
    "agent_active_start": {"agent_active_end"},
    "model_request": {"model_response", "model_error"},
    "tool_start": {"tool_end"},
    "tool_execution_start": {"tool_execution_end"},
    "background_start": {"background_end"},
    "workflow_node_start": {"workflow_node_end"},
    "context_prepare": {"context_prepared"},
    "permission_wait_start": {"permission_wait_end"},
    "input_wait_start": {"input_wait_end"},
}
WRAPPER_TOOLS = {"task", "spawn_teammate", "Workflow"}


@dataclass(frozen=True)
class Interval:
    start_ns: int
    end_ns: int
    start_event: dict[str, Any]
    end_event: dict[str, Any]

    @property
    def duration_ms(self) -> float:
        return max(0, self.end_ns - self.start_ns) / 1_000_000

    @property
    def agent_id(self) -> str | None:
        return self.start_event.get("agent_id") or self.end_event.get("agent_id")

    @property
    def kind(self) -> str:
        return str(self.start_event.get("event", "unknown"))

    @property
    def start_data(self) -> dict[str, Any]:
        data = self.start_event.get("data", {})
        return data if isinstance(data, dict) else {}

    @property
    def end_data(self) -> dict[str, Any]:
        data = self.end_event.get("data", {})
        return data if isinstance(data, dict) else {}


def load_trace(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(record, dict) or not isinstance(record.get("event"), str):
                raise ValueError(f"invalid trace record at {path}:{line_number}")
            records.append(record)
    records.sort(key=lambda event: int(event.get("monotonic_ns", 0)))
    if not records:
        raise ValueError(f"trace is empty: {path}")
    return records


def pair_spans(events: Iterable[dict[str, Any]]) -> list[Interval]:
    starts: dict[str, dict[str, Any]] = {}
    intervals = []
    for event in events:
        span_id = event.get("span_id")
        name = event.get("event")
        if not span_id:
            continue
        if name in START_TO_END:
            starts[str(span_id)] = event
            continue
        start = starts.get(str(span_id))
        if start is None or name not in START_TO_END.get(start.get("event"), set()):
            continue
        start_ns = int(start.get("monotonic_ns", 0))
        end_ns = max(start_ns, int(event.get("monotonic_ns", start_ns)))
        intervals.append(Interval(start_ns, end_ns, start, event))
        starts.pop(str(span_id), None)
    return intervals


def _ranges(intervals: Iterable[Interval]) -> list[tuple[int, int]]:
    return sorted(
        (interval.start_ns, interval.end_ns)
        for interval in intervals
        if interval.end_ns >= interval.start_ns
    )


def _union_ns(intervals: Iterable[Interval]) -> int:
    total = 0
    current_start = current_end = None
    for start, end in _ranges(intervals):
        if current_start is None:
            current_start, current_end = start, end
        elif start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    if current_start is not None:
        total += current_end - current_start
    return total


def _merge_ranges(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _agent_maps(events: Iterable[dict[str, Any]]):
    info: dict[str, dict[str, Any]] = {
        "agent-root": {"role": "lead", "name": "Root Agent", "task": "interactive session"}
    }
    parents: dict[str, str | None] = {"agent-root": None}
    created_at: dict[str, float] = {"agent-root": 0.0}
    for event in events:
        agent_id = event.get("agent_id")
        if not agent_id:
            continue
        agent_id = str(agent_id)
        data = event.get("data", {})
        if not isinstance(data, dict):
            data = {}
        if event.get("event") in {"agent_create", "agent_start"}:
            current = info.setdefault(agent_id, {})
            for key in ("role", "name", "task", "label", "execution", "workflow_name"):
                if key in data and key not in current:
                    current[key] = data[key]
            if event.get("agent_kind") and "kind" not in current:
                current["kind"] = event["agent_kind"]
            parent = event.get("parent_agent_id")
            if agent_id not in parents or parents[agent_id] is None:
                parents[agent_id] = str(parent) if parent else None
            created_at.setdefault(agent_id, float(event.get("elapsed_ms", 0)))
    return info, parents, created_at


def _depths(parents: dict[str, str | None]) -> dict[str, int]:
    memo: dict[str, int] = {}

    def depth(agent_id: str, visiting: set[str]) -> int:
        if agent_id in memo:
            return memo[agent_id]
        if agent_id in visiting:
            return 0
        parent = parents.get(agent_id)
        value = 0 if parent is None else depth(parent, visiting | {agent_id}) + 1
        memo[agent_id] = value
        return value

    for agent_id in parents:
        depth(agent_id, set())
    return memo


def _tool_work_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    work = []
    for interval in intervals:
        if interval.kind == "background_start":
            work.append(interval)
        elif interval.kind == "tool_execution_start":
            tool = interval.start_data.get("tool") or interval.end_data.get("tool")
            if tool not in WRAPPER_TOOLS:
                work.append(interval)
    return work


def _active_work_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    return [
        interval for interval in intervals
        if interval.kind == "model_request"
        or (
            interval.kind == "workflow_node_start"
            and interval.start_data.get("executed") is not False
        )
    ] + _tool_work_intervals(intervals)


def _maximum_parallel_agents(intervals: Iterable[Interval]) -> int:
    per_agent: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for interval in intervals:
        if interval.agent_id:
            per_agent[interval.agent_id].append((interval.start_ns, interval.end_ns))
    points = []
    for ranges in per_agent.values():
        for start, end in _merge_ranges(ranges):
            points.append((start, 1))
            points.append((end, -1))
    # End before start at the same timestamp avoids counting adjacent spans twice.
    active = peak = 0
    for _when, delta in sorted(points, key=lambda point: (point[0], point[1])):
        active += delta
        peak = max(peak, active)
    return peak


def calculate_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    intervals = pair_spans(events)
    info, parents, _created_at = _agent_maps(events)
    depths = _depths(parents)
    start_ns = int(events[0].get("monotonic_ns", 0))
    end_ns = int(events[-1].get("monotonic_ns", start_ns))
    total_ms = max(0, end_ns - start_ns) / 1_000_000

    model_intervals = [span for span in intervals if span.kind == "model_request"]
    tool_intervals = [span for span in intervals if span.kind == "tool_start"]
    leaf_tool_intervals = _tool_work_intervals(intervals)
    human_intervals = [
        span for span in intervals
        if span.kind in {"input_wait_start", "permission_wait_start"}
    ]
    busy_intervals = model_intervals + leaf_tool_intervals
    busy_ns = _union_ns(busy_intervals)
    human_ns = _union_ns(human_intervals)
    human_and_busy_ns = _union_ns(human_intervals + busy_intervals)
    human_only_ns = max(0, human_ns - (human_ns + busy_ns - human_and_busy_ns))
    orchestration_ms = max(0.0, total_ms - busy_ns / 1_000_000 - human_only_ns / 1_000_000)

    tool_counts = Counter()
    for event in events:
        if event.get("event") != "tool_start":
            continue
        data = event.get("data", {})
        tool = data.get("tool", "unknown") if isinstance(data, dict) else "unknown"
        tool_counts[str(tool)] += 1

    input_tokens = output_tokens = cache_tokens = 0
    calls_with_usage = 0
    for event in events:
        if event.get("event") != "model_response":
            continue
        data = event.get("data", {})
        usage = data.get("usage") if isinstance(data, dict) else None
        if not isinstance(usage, dict):
            continue
        calls_with_usage += 1
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        cache_tokens += int(usage.get("cache_creation_input_tokens") or 0)
        cache_tokens += int(usage.get("cache_read_input_tokens") or 0)

    queue_waits = []
    for event in events:
        if event.get("event") != "workflow_node_start":
            continue
        data = event.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("queue_wait_ms"), (int, float)):
            queue_waits.append(float(data["queue_wait_ms"]))

    created_ns: dict[str, int] = {}
    started_agents: set[str] = set()
    launch_waits = []
    for event in events:
        agent_id = event.get("agent_id")
        if not agent_id:
            continue
        agent_id = str(agent_id)
        if event.get("event") == "agent_create":
            created_ns.setdefault(agent_id, int(event.get("monotonic_ns", 0)))
        elif (
            event.get("event") == "agent_start"
            and agent_id in created_ns
            and agent_id not in started_agents
        ):
            started_agents.add(agent_id)
            launch_waits.append(max(
                0,
                int(event.get("monotonic_ns", 0)) - created_ns[agent_id],
            ) / 1_000_000)

    subagent_ids = {
        str(event["agent_id"])
        for event in events
        if event.get("event") == "agent_create" and event.get("agent_id")
        and event.get("agent_id") != "agent-root"
    }
    return {
        "run_id": events[0].get("run_id"),
        "total_runtime_ms": round(total_ms, 3),
        "total_model_calls": sum(
            event.get("event") == "model_request" for event in events
        ),
        "model_errors": sum(event.get("event") == "model_error" for event in events),
        "total_tool_calls": sum(event.get("event") == "tool_start" for event in events),
        "tool_calls_by_type": dict(sorted(tool_counts.items())),
        "total_subagents": len(subagent_ids),
        "total_agents": len(info),
        "cached_workflow_nodes": sum(
            event.get("event") == "workflow_node_end"
            and isinstance(event.get("data"), dict)
            and event["data"].get("status") == "cached"
            for event in events
        ),
        "maximum_agent_depth": max(depths.values(), default=0),
        "maximum_parallel_agents": _maximum_parallel_agents(
            _active_work_intervals(intervals)
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_tokens": cache_tokens,
        "model_calls_with_usage": calls_with_usage,
        "model_time_ms": round(sum(span.duration_ms for span in model_intervals), 3),
        "model_wall_time_ms": round(_union_ns(model_intervals) / 1_000_000, 3),
        "tool_time_ms": round(sum(span.duration_ms for span in leaf_tool_intervals), 3),
        "tool_wall_time_ms": round(_union_ns(leaf_tool_intervals) / 1_000_000, 3),
        "human_wait_ms": round(human_only_ns / 1_000_000, 3),
        "observed_scheduling_wait_ms": round(sum(queue_waits), 3),
        "maximum_scheduling_wait_ms": round(max(queue_waits, default=0.0), 3),
        "agent_launch_wait_ms": round(sum(launch_waits), 3),
        "maximum_agent_launch_wait_ms": round(max(launch_waits, default=0.0), 3),
        "orchestration_overhead_ms": round(orchestration_ms, 3),
    }


def build_summary(path: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    trace_files = sorted(path.parent.glob("run_*.jsonl"), key=lambda item: item.name)
    summary: dict[str, Any] = {
        "trace_file": str(path),
        "trace_files": [str(item) for item in trace_files],
        "trace_count": len(trace_files),
        "event_count": len(events),
        "events_by_type": dict(sorted(Counter(event.get("event") for event in events).items())),
    }
    stamped = [event for event in events if event.get("monotonic_ns") is not None]
    if stamped:
        first_ns = min(int(event["monotonic_ns"]) for event in stamped)
        last_ns = max(int(event["monotonic_ns"]) for event in stamped)
        summary["duration_ms"] = round((last_ns - first_ns) / 1_000_000, 3)
    input_tokens = output_tokens = cache_tokens = 0
    has_usage = False
    for event in events:
        if event.get("event") != "model_response":
            continue
        data = event.get("data", {})
        usage = data.get("usage") if isinstance(data, dict) else None
        if not isinstance(usage, dict):
            continue
        has_usage = True
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        cache_tokens += int(usage.get("cache_creation_input_tokens") or 0)
        cache_tokens += int(usage.get("cache_read_input_tokens") or 0)
    if has_usage:
        summary["total_tokens"] = input_tokens + output_tokens + cache_tokens
        summary["tokens"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_tokens": cache_tokens,
        }
    return summary


def _short(value: Any, limit: int = 100) -> str:
    if isinstance(value, dict) and "preview" in value:
        value = value.get("preview", "")
    elif not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[: max(0, limit - 3)] + "..."


def _agent_label(agent_id: str, info: dict[str, dict[str, Any]]) -> str:
    data = info.get(agent_id, {})
    if agent_id == "agent-root":
        return "Root Agent"
    role = data.get("name") or data.get("label") or data.get("role") or data.get("kind")
    return f"{role or 'Agent'} ({agent_id})"


def _event_label(event: dict[str, Any], starts: dict[str, dict[str, Any]]) -> str | None:
    name = event.get("event")
    data = event.get("data", {})
    data = data if isinstance(data, dict) else {}
    duration = data.get("duration_ms")
    duration_text = f" {float(duration):.1f}ms" if isinstance(duration, (int, float)) else ""
    if name in {"model_response", "model_error"}:
        start = starts.get(str(event.get("span_id")), {})
        start_data = start.get("data", {}) if isinstance(start.get("data", {}), dict) else {}
        purpose = data.get("purpose") or start_data.get("purpose") or "unspecified"
        if name == "model_error":
            return f"LLM [{purpose}] error{duration_text}: {_short(data.get('error', ''))}"
        actions = data.get("requested_actions", [])
        tools = [action.get("tool") for action in actions
                 if isinstance(action, dict) and action.get("type") == "tool_use"]
        outcome = " -> " + ", ".join(f"tool:{tool}" for tool in tools) if tools else " -> response"
        return f"LLM [{purpose}]{duration_text}{outcome}"
    if name == "tool_end":
        start = starts.get(str(event.get("span_id")), {})
        start_data = start.get("data", {}) if isinstance(start.get("data", {}), dict) else {}
        tool = data.get("tool") or start_data.get("tool") or "unknown"
        arguments = start_data.get("arguments", {})
        status = data.get("status", "unknown")
        return f"Tool: {tool} {_short(arguments, 80)} -> {status}{duration_text}"
    if name == "background_end":
        tool = data.get("tool") or "bash"
        return f"Background tool: {tool} -> {data.get('status', 'unknown')}{duration_text}"
    if name == "workflow_node_end":
        start = starts.get(str(event.get("span_id")), {})
        start_data = start.get("data", {}) if isinstance(start.get("data", {}), dict) else {}
        label = data.get("label") or start_data.get("label") or "workflow step"
        status = data.get("status", "unknown")
        executed = data.get("executed", start_data.get("executed", True))
        suffix = " (journal cache)" if executed is False else ""
        return f"Workflow node: {label} -> {status}{duration_text}{suffix}"
    if name == "message_send":
        return f"Message: {data.get('from')} -> {data.get('to')} ({data.get('message_type')})"
    if name == "workflow_dependency":
        return f"Depends: {data.get('from_node_id')} -> {data.get('to_node_id')}"
    if name == "harness_decision":
        action = data.get("action")
        suffix = f" / {action}" if action else ""
        return (
            f"Harness: {data.get('decision', 'unknown')} "
            f"({data.get('reason', 'unspecified')}{suffix})"
        )
    if name == "context_compact":
        return f"Context compact: {data.get('strategy', 'unknown')}"
    return None


def render_tree(events: list[dict[str, Any]]) -> str:
    info, parents, created_at = _agent_maps(events)
    children: dict[str | None, list[str]] = defaultdict(list)
    for agent_id, parent in parents.items():
        if agent_id != "agent-root":
            children[parent].append(agent_id)
    for values in children.values():
        values.sort(key=lambda agent_id: created_at.get(agent_id, 0))

    starts = {
        str(event["span_id"]): event
        for event in events
        if event.get("span_id") and event.get("event") in START_TO_END
    }
    actions: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for event in events:
        agent_id = event.get("agent_id")
        if not agent_id:
            continue
        label = _event_label(event, starts)
        if label:
            actions[str(agent_id)].append((float(event.get("elapsed_ms", 0)), "event", label))
    for parent, child_ids in children.items():
        if parent is None:
            continue
        for child_id in child_ids:
            actions[parent].append((created_at.get(child_id, 0), "child", child_id))
    for values in actions.values():
        values.sort(key=lambda item: item[0])

    roots = ["agent-root"] if "agent-root" in info else []
    roots.extend(
        agent_id for agent_id, parent in parents.items()
        if parent is None and agent_id not in roots
    )
    lines = ["Agent / execution tree"]

    def visit(agent_id: str, prefix: str, connector: str) -> None:
        lines.append(f"{prefix}{connector}{_agent_label(agent_id, info)}")
        data = info.get(agent_id, {})
        task = data.get("task")
        items = list(actions.get(agent_id, []))
        details = []
        if task and agent_id != "agent-root":
            details.append((created_at.get(agent_id, 0) - 0.001, "event", f"Task: {_short(task, 120)}"))
        items = sorted(details + items, key=lambda item: item[0])
        child_prefix = prefix + ("   " if connector == "└─ " else "│  ")
        for index, (_when, kind, value) in enumerate(items):
            last = index == len(items) - 1
            branch = "└─ " if last else "├─ "
            if kind == "child":
                visit(value, child_prefix, branch)
            else:
                lines.append(f"{child_prefix}{branch}{value}")

    for index, root in enumerate(roots):
        visit(root, "", "" if index == 0 else "└─ ")
    return "\n".join(lines)


def render_timeline(events: list[dict[str, Any]], width: int = 90) -> str:
    intervals = pair_spans(events)
    info, _parents, _created = _agent_maps(events)
    first_ns = int(events[0].get("monotonic_ns", 0))
    last_ns = int(events[-1].get("monotonic_ns", first_ns))
    total_ns = max(1, last_ns - first_ns)
    chart_width = max(30, width)
    priority = {"L": 1, "A": 2, "W": 3, "B": 4, "T": 5, "M": 6, "P": 7}
    symbols = {
        "agent_active_start": "A",
        "agent_start": "L",
        "workflow_node_start": "W",
        "background_start": "B",
        "tool_start": "T",
        "model_request": "M",
        "permission_wait_start": "P",
        "input_wait_start": "P",
    }
    per_agent: dict[str, list[Interval]] = defaultdict(list)
    for interval in intervals:
        if interval.kind not in symbols:
            continue
        agent_id = interval.agent_id or "harness-wait"
        per_agent[agent_id].append(interval)

    labels = {agent_id: _agent_label(agent_id, info) for agent_id in per_agent}
    if "harness-wait" in labels:
        labels["harness-wait"] = "Harness / user wait"
    label_width = min(30, max([len(label) for label in labels.values()] + [5]))
    total_ms = total_ns / 1_000_000
    midpoint = f"{total_ms / 2:.0f}ms"
    end_label = f"{total_ms:.0f}ms"
    axis = [" "] * chart_width
    for position, label in ((0, "0ms"), (chart_width // 2, midpoint),
                            (max(0, chart_width - len(end_label)), end_label)):
        for offset, character in enumerate(label):
            if position + offset < chart_width:
                axis[position + offset] = character
    lines = ["Timeline", " " * (label_width + 2) + "".join(axis),
             " " * (label_width + 2) + "|" + "-" * (chart_width - 2) + "|"]

    order = sorted(
        per_agent,
        key=lambda agent_id: min(span.start_ns for span in per_agent[agent_id]),
    )
    for agent_id in order:
        cells = [" "] * chart_width
        cell_priority = [0] * chart_width
        for interval in sorted(per_agent[agent_id], key=lambda span: priority[symbols[span.kind]]):
            symbol = symbols[interval.kind]
            start = int((interval.start_ns - first_ns) / total_ns * (chart_width - 1))
            end = int((interval.end_ns - first_ns) / total_ns * (chart_width - 1))
            end = max(start, end)
            for position in range(start, min(chart_width - 1, end) + 1):
                if priority[symbol] >= cell_priority[position]:
                    cells[position] = symbol
                    cell_priority[position] = priority[symbol]
            if start < chart_width and priority[symbol] >= cell_priority[start]:
                cells[start] = "["
            if end < chart_width and priority[symbol] >= cell_priority[end]:
                cells[end] = "]"
        lines.append(f"{labels[agent_id][:label_width]:<{label_width}}  {''.join(cells)}")

    dependencies = []
    for event in events:
        if event.get("event") != "workflow_dependency":
            continue
        data = event.get("data", {})
        if isinstance(data, dict):
            dependencies.append(f"{data.get('from_node_id')} -> {data.get('to_node_id')}")
    lines.append(
        "Legend: M=model  T=tool  B=background tool  W=workflow node  "
        "A=active cycle  L=lifecycle  P=user/permission wait"
    )
    if dependencies:
        lines.append("Dependencies:")
        lines.extend(f"  {dependency}" for dependency in dependencies)
    return "\n".join(lines)


def render_metrics(metrics: dict[str, Any]) -> str:
    ordered = [
        "run_id", "total_runtime_ms", "total_model_calls", "model_errors",
        "total_tool_calls", "tool_calls_by_type", "total_subagents", "total_agents",
        "cached_workflow_nodes", "maximum_agent_depth", "maximum_parallel_agents", "input_tokens",
        "output_tokens", "cache_tokens", "model_calls_with_usage", "model_time_ms",
        "model_wall_time_ms", "tool_time_ms", "tool_wall_time_ms", "human_wait_ms",
        "observed_scheduling_wait_ms", "maximum_scheduling_wait_ms",
        "agent_launch_wait_ms", "maximum_agent_launch_wait_ms",
        "orchestration_overhead_ms",
    ]
    lines = ["Metrics"]
    width = max(len(key) for key in ordered)
    for key in ordered:
        value = metrics.get(key)
        if isinstance(value, dict):
            value = json.dumps(value, sort_keys=True)
        lines.append(f"  {key:<{width}} : {value}")
    return "\n".join(lines)


def _latest_trace(directory: Path) -> Path:
    candidates = sorted(directory.glob("run_*.jsonl"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise ValueError(f"no run_*.jsonl files found in {directory}")
    return candidates[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", nargs="?", type=Path,
                        help="trace JSONL (default: latest file in traces/)")
    parser.add_argument("--view", choices=("both", "tree", "timeline", "metrics"),
                        default="both")
    parser.add_argument("--width", type=int, default=90,
                        help="timeline chart width (default: 90)")
    parser.add_argument("--summary", action="store_true",
                        help="print a machine-readable JSON summary to stdout")
    args = parser.parse_args(argv)
    try:
        path = args.trace or _latest_trace(Path("traces"))
        events = load_trace(path)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.summary:
        print(json.dumps(build_summary(path, events), indent=2))
        return 0

    sections = []
    if args.view in {"both", "metrics"}:
        sections.append(render_metrics(calculate_metrics(events)))
    if args.view in {"both", "tree"}:
        sections.append(render_tree(events))
    if args.view in {"both", "timeline"}:
        sections.append(render_timeline(events, args.width))
    print(f"Trace: {path}\n")
    print("\n\n".join(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
