#!/usr/bin/env python3
"""Render the task-dependency DAG of an integrated-harness trace as HTML.

Reads a JSONL trace written by trace_runtime.py, reconstructs the file-backed
task board from task_create / task_update / task_claim / task_complete events,
and emits a single self-contained HTML file with:

  * the blockedBy dependency graph as a layered SVG DAG (columns = longest-path
    layer, nodes colored by final status, critical path highlighted)
  * a table-view twin of the same data
  * stat tiles (tasks, edges, done/claimed/pending, depth)

Usage:
    python3 scripts/trace_task_dag.py traces/<run>.jsonl [-o trace_task_dag.html]

Reuses the palette validator and stylesheet from trace_workflow_viz.py so both
views of a run look and read the same.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from trace_workflow_viz import CSS, fmt_clock, validate_palette


# --------------------------------------------------------------------------
# Trace parsing
# --------------------------------------------------------------------------

def parse_tasks(path: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    break
    if not events:
        raise SystemExit(f"no parseable events in {path}")

    last_elapsed = max(e["elapsed_ms"] for e in events)
    run = next((e for e in events if e["event"] == "run_start"), events[0])

    tasks: dict[str, dict[str, Any]] = {}
    for e in events:
        d = e.get("data") or {}
        ev = e["event"]
        if ev == "task_create":
            tid = d.get("id") or d.get("task_id") or "?"
            tasks[tid] = {
                "id": tid, "subject": d.get("subject") or "",
                "desc": d.get("description") or "",
                "blocked": list(d.get("blockedBy") or []),
                "created_s": e["elapsed_ms"], "owner": None,
                "claim_s": None, "done_s": None, "status": d.get("status") or "pending",
            }
        elif ev == "task_update" and d.get("blocked_by_task_ids") is not None:
            t = tasks.get(d.get("task_id"))
            if t:
                t["blocked"] = list(d["blocked_by_task_ids"])
        elif ev == "task_update" and d.get("status"):
            t = tasks.get(d.get("task_id"))
            if t:
                t["status"] = d["status"]
        elif ev == "task_claim":
            t = tasks.get(d.get("task_id"))
            if t:
                t["owner"] = d.get("owner")
                t["claim_s"] = e["elapsed_ms"]
                if t["status"] != "done":
                    t["status"] = "claimed"
        elif ev == "task_complete":
            t = tasks.get(d.get("task_id"))
            if t:
                t["status"] = "done"
                t["done_s"] = e["elapsed_ms"]

    ids = {t["id"] for t in tasks.values()}
    deps: dict[str, list[str]] = {}
    for tid, t in tasks.items():
        t["deps"] = [b for b in t["blocked"] if b in ids]
        deps[tid] = t["deps"]

    # longest-path layering (iterative)
    layer: dict[str, int] = {}
    def depth(u: str) -> int:
        stack = [u]
        while stack:
            n = stack[-1]
            if n in layer:
                stack.pop(); continue
            pending = [v for v in deps[n] if v not in layer]
            if pending:
                stack.extend(pending); continue
            layer[n] = max((layer[v] + 1 for v in deps[n]), default=0)
            stack.pop()
    for tid in tasks:
        depth(tid)

    # critical path: longest chain ending at each node
    best: dict[str, tuple[int, list[str]]] = {}
    def crit(u: str) -> tuple[int, list[str]]:
        stack = [u]
        while stack:
            n = stack[-1]
            if n in best:
                stack.pop(); continue
            pending = [v for v in deps[n] if v not in best]
            if pending:
                stack.extend(pending); continue
            top = max((best[v] for v in deps[n]), key=lambda b: b[0], default=(0, []))
            best[n] = (top[0] + 1, top[1] + [n])
            stack.pop()
    for tid in tasks:
        crit(tid)

    cp_path: list[str] = []
    cp_edges: set[tuple[str, str]] = set()
    if best:
        cp_path = max(best.values(), key=lambda b: b[0])[1]
        for a, b in zip(cp_path, cp_path[1:]):
            cp_edges.add((a, b))

    by_layer: dict[int, list[str]] = defaultdict(list)
    for tid in sorted(tasks, key=lambda k: tasks[k]["created_s"]):
        by_layer[layer[tid]].append(tid)

    return {
        "run_id": run.get("run_id"),
        "file": path.name,
        "last_elapsed": last_elapsed,
        "tasks": tasks,
        "layers": {str(k): v for k, v in sorted(by_layer.items())},
        "n_layers": max(layer.values(), default=0) + 1,
        "n_edges": sum(len(v) for v in deps.values()),
        "on_cp": cp_path,
        "cp_edges": sorted(cp_edges),
        "status_census": _census(tasks),
    }


def _census(tasks: dict[str, dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for t in tasks.values():
        out[t["status"]] += 1
    return dict(out)


# --------------------------------------------------------------------------
# HTML generation
# --------------------------------------------------------------------------

DAG_CSS = """
.dag-scroll { overflow-x:auto; }
.dag-legend { display:flex; flex-wrap:wrap; gap:12px; font-size:11.5px; color:var(--ink-2);
  align-items:center; margin-bottom:8px; }
.dag-legend .k { display:inline-flex; align-items:center; gap:5px; }
.dag-node { cursor:default; }
.dag-node:focus { outline:none; }
.dag-node:focus-visible .dag-box { stroke:var(--accent); stroke-width:2; }
"""

STATUS_FILL = {"done": "var(--c-tool)", "claimed": "var(--c-model)", "pending": "var(--muted)"}
STATUS_LABEL = {"done": "done", "claimed": "claimed", "pending": "pending"}


def short(tid: str) -> str:
    return tid.replace("task_", "")[:4]


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def build_svg(d: dict[str, Any]) -> str:
    tasks = d["tasks"]
    node_w, node_h, gap_y, col_gap, pad_l, pad_t = 224, 40, 8, 96, 16, 34
    pos: dict[str, tuple[float, float]] = {}
    for ln, tids in d["layers"].items():
        for i, tid in enumerate(tids):
            pos[tid] = (pad_l + int(ln) * (node_w + col_gap), pad_t + i * (node_h + gap_y))
    max_rows = max(len(v) for v in d["layers"].values())
    W = pad_l * 2 + d["n_layers"] * (node_w + col_gap) - col_gap
    H = pad_t * 2 + max_rows * (node_h + gap_y) - gap_y

    cp_edges = {tuple(x) for x in d["cp_edges"]}
    parts = [
        f'<svg viewBox="0 0 {W} {H}" width="{W}" style="max-width:none" '
        f'role="img" aria-label="Task dependency DAG, {d["n_layers"]} layers">'
    ]
    # edges first (under nodes)
    for tid, t in tasks.items():
        x2, y2 = pos[tid]
        for dep in t["deps"]:
            x1, y1 = pos[dep]
            dx = (x2 - (x1 + node_w)) * 0.5
            is_cp = (dep, tid) in cp_edges
            stroke = "var(--accent)" if is_cp else "var(--axis)"
            opacity = "0.9" if is_cp else "0.45"
            width = "1.6" if is_cp else "1"
            parts.append(
                f'<path d="M {x1 + node_w} {y1 + node_h / 2} '
                f'C {x1 + node_w + dx} {y1 + node_h / 2}, {x2 - dx} {y2 + node_h / 2}, {x2} {y2 + node_h / 2}" '
                f'fill="none" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"/>')
    # layer headers
    for ln in sorted(d["layers"], key=int):
        x = pad_l + int(ln) * (node_w + col_gap)
        parts.append(f'<text x="{x}" y="{pad_t - 12}" font-size="11" fill="var(--muted)">'
                     f'L{ln} · {len(d["layers"][ln])} task{"s" if len(d["layers"][ln]) != 1 else ""}</text>')
    # nodes
    cp = set(d["on_cp"])
    for tid, t in tasks.items():
        x, y = pos[tid]
        fill = STATUS_FILL.get(t["status"], "var(--muted)")
        box_stroke = "var(--accent)" if tid in cp and t["status"] != "done" else "var(--border)"
        title = esc(t["subject"])
        dims = 'font-style:italic;fill:var(--muted)' if t["status"] == "pending" else ""
        tip = (
            f' data-tip-title="{short(tid)} · {STATUS_LABEL.get(t["status"], t["status"])}'
            f'{" · critical path" if tid in cp else ""}"'
            f' data-tip-subject="{title}"'
            f' data-tip-owner="{esc(t["owner"] or "unclaimed")}"'
            f' data-tip-deps="{esc(", ".join(short(b) for b in t["deps"]) or "none — root task")}"'
            f' data-tip-times="created {fmt_clock(t["created_s"])}'
            + (f' · claimed {fmt_clock(t["claim_s"])}' if t["claim_s"] else "")
            + (f' · done {fmt_clock(t["done_s"])}' if t["done_s"] else "") + '"'
        )
        parts.append(
            f'<g class="dag-node" tabindex="0"{tip}>'
            f'<rect class="dag-box" x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="7" '
            f'fill="var(--surface-1)" stroke="{box_stroke}" stroke-width="1"/>'
            f'<rect x="{x}" y="{y}" width="4" height="{node_h}" rx="2" fill="{fill}"/>'
            f'<text x="{x + 12}" y="{y + 16}" font-size="10.5" font-weight="650" fill="var(--ink)">'
            f'{short(tid)}{" ★" if tid in cp else ""}</text>'
            f'<text x="{x + node_w - 8}" y="{y + 16}" font-size="9.5" text-anchor="end" '
            f'fill="var(--muted)">{STATUS_LABEL.get(t["status"], t["status"])}</text>'
            f'<text x="{x + 12}" y="{y + 30}" font-size="10" {dims} fill="var(--ink-2)">{title[:34]}</text>'
            f'</g>')
    parts.append("</svg>")
    return "\n".join(parts)


JS = r"""
const DATA = JSON.parse(document.getElementById('viz-data').textContent);
const tip = document.getElementById('tooltip');
function showTip(rows, x, y) {
  tip.textContent = '';
  for (const r of rows) {
    const d = document.createElement('div');
    d.className = r.c ? 'tr' : 'tm';
    if (r.c) { const i = document.createElement('i'); i.style.background = r.c; d.appendChild(i); }
    const s = document.createElement('span'); s.className = r.c ? 'tv' : '';
    s.textContent = (r.c ? r.v : r.t) + (r.c && r.l ? ' ' + r.l : '');
    d.appendChild(s); tip.appendChild(d);
  }
  tip.style.display = 'block';
  tip.style.left = Math.min(x + 14, innerWidth - tip.offsetWidth - 8) + 'px';
  tip.style.top = Math.min(y + 14, innerHeight - tip.offsetHeight - 8) + 'px';
}
function hideTip() { tip.style.display = 'none'; }
document.querySelectorAll('.dag-node').forEach(g => {
  const rows = [
    { v: g.dataset.tipTitle, c: '' },
    { t: g.dataset.tipSubject },
    { t: 'owner: ' + g.dataset.tipOwner },
    { t: 'blockedBy: ' + g.dataset.tipDeps },
    { t: g.dataset.tipTimes },
  ];
  g.addEventListener('pointermove', ev => showTip(rows, ev.clientX, ev.clientY));
  g.addEventListener('pointerleave', hideTip);
  g.addEventListener('focus', () => { const b = g.getBoundingClientRect(); showTip(rows, b.left, b.bottom); });
  g.addEventListener('blur', hideTip);
});

// table twin
(function () {
  const ta = document.getElementById('tbl-tasks');
  const thead = document.createElement('thead'); const trh = document.createElement('tr');
  ['ID', 'Subject', 'Status', 'Owner', 'blockedBy', 'Created'].forEach(h => {
    const th = document.createElement('th'); if (h === 'Created') th.className = 'num';
    th.textContent = h; trh.appendChild(th);
  });
  thead.appendChild(trh); ta.appendChild(thead);
  const tb = document.createElement('tbody');
  DATA.tasks.forEach(t => {
    const tr = document.createElement('tr');
    const td = (v, cls) => { const d = document.createElement('td'); if (cls) d.className = cls;
      d.textContent = v; tr.appendChild(d); return d; };
    td(t.id).style.fontVariantNumeric = 'tabular-nums';
    const s = td(t.subject); s.style.maxWidth = '420px';
    if (t.subject) { s.title = t.subject; s.style.overflow = 'hidden';
      s.style.textOverflow = 'ellipsis'; s.style.whiteSpace = 'nowrap'; }
    const st = document.createElement('td'); const sp = document.createElement('span');
    sp.className = 'st ' + (t.status === 'done' ? 'done' : t.status === 'claimed' ? 'run2' : '');
    sp.textContent = t.status; st.appendChild(sp); tr.appendChild(st);
    td(t.owner || '—');
    td(t.deps.length ? t.deps.join(', ') : '—');
    td(t.created, 'num');
    tb.appendChild(tr);
  });
  ta.appendChild(tb);
})();
"""


def build_html(d: dict[str, Any], palette_report: list[str]) -> str:
    c = d["status_census"]
    n = len(d["tasks"])
    tiles = [
        ("Tasks", str(n), f"{d['n_edges']} blockedBy edges · {d['n_layers']} layers"),
        ("Done", str(c.get("done", 0)), f"{c.get('claimed', 0)} claimed · {c.get('pending', 0)} never started"),
        ("Critical path", f"{len(d['on_cp'])} tasks", " → ".join(short(x) for x in d["on_cp"])),
        ("Wall time", fmt_clock(d["last_elapsed"]), f"snapshot of {d['file']}"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="lb">{lb}</div><div class="v">{esc(v)}</div><div class="x">{esc(x)}</div></div>'
        for lb, v, x in tiles)
    legend_items = [
        ("done", "var(--c-tool)"), ("claimed", "var(--c-model)"),
        ("pending (never started)", "var(--muted)"), ("critical path ★", "var(--accent)"),
    ]
    legend_html = "".join(f'<span class="k"><span class="sw" style="background:{c2}"></span>{lb}</span>'
                          for lb, c2 in legend_items)
    report_html = "\n".join("<!-- " + line + " -->" for line in palette_report)
    tasks_json = json.dumps([
        {"id": short(t["id"]), "subject": t["subject"], "status": t["status"],
         "owner": t["owner"], "deps": [short(b) for b in t["deps"]],
         "created": fmt_clock(t["created_s"])}
        for t in d["tasks"].values()
    ], ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Task DAG — run {d['run_id']}</title>
<style>{CSS}</style>
<style>{DAG_CSS}</style>
</head>
<body>
<div class="viz-root" data-mode="light">
  {report_html}
  <h1>Task dependency DAG — run {d['run_id']}</h1>
  <p class="sub">Reconstructed from task_create / task_update / task_claim / task_complete events in
  <b>{esc(d['file'])}</b>. Columns are longest-path layers; every edge is a blockedBy written by the lead.</p>
  <div class="tiles">{tiles_html}</div>
  <div class="card"><h2>DAG <span class="n">· left to right = dependency order · hover a node for subject, owner and times</span></h2>
    <div class="dag-legend">{legend_html}</div>
    <div class="dag-scroll">{build_svg(d)}</div>
  </div>
  <div class="card"><h2>Tasks <span class="n">· table view of the DAG</span></h2>
    <table id="tbl-tasks"></table>
  </div>
  <p class="foot">Self-contained snapshot — regenerate:
  <code>python3 scripts/trace_task_dag.py traces/{esc(d['file'])} -o trace_task_dag.html</code></p>
</div>
<div id="tooltip"></div>
<script type="application/json" id="viz-data">{tasks_json}</script>
<script>{JS}</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trace", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("trace_task_dag.html"))
    args = ap.parse_args(argv)

    reports = []
    reports += validate_palette(["#2a78d6", "#eb6834", "#1baf7a"], "#fcfcfb", "light",
                                extra_status=["#d03b3b"])
    reports += validate_palette(["#3987e5", "#d95926", "#199e70"], "#1a1a19", "dark",
                                extra_status=["#d03b3b"])

    d = parse_tasks(args.trace)
    html = build_html(d, reports)
    args.output.write_text(html)
    c = d["status_census"]
    print(f"wrote {args.output} ({len(html)/1024:.0f} KB): {len(d['tasks'])} tasks, "
          f"{d['n_edges']} edges, {d['n_layers']} layers, "
          f"done={c.get('done',0)} claimed={c.get('claimed',0)} pending={c.get('pending',0)}, "
          f"critical path={' → '.join(short(x) for x in d['on_cp'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
