#!/usr/bin/env python3
"""Render an integrated-harness trace as an interactive HTML workflow visualization.

Reads a JSONL trace written by trace_runtime.py and emits a single self-contained
HTML file (no external assets) with:

  * run stat tiles (wall time, agents, tasks, model/tool calls, tokens)
  * the agent tree (lead -> spawned teammates) as an SVG diagram
  * a swimlane timeline (per-agent lanes with model calls, tool executions,
    permission waits, messages, compactions, turn boundaries)
  * a tool-usage bar chart and table-view twins for every chart

Usage:
    python3 scripts/trace_workflow_viz.py traces/<run>.jsonl [-o out.html]

The file is safe to regenerate while the traced run is still writing: open spans
are closed at the last observed event and marked "open at snapshot".
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Palette validation (port of dataviz validate_palette.js six checks) — the
# color part is computable, so compute it. Fails generation on a hard FAIL.
# --------------------------------------------------------------------------

def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex_to_rgb01(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    return tuple(int(hx[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _oklab(hx: str) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(v) for v in _hex_to_rgb01(hx))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


# Machado-Oliveira-Fernandes 2009, severity 1.0
_CVD_MATS = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
}


def _delta_e(h1: str, h2: str, cvd: str | None = None) -> float:
    def lab(hx: str) -> tuple[float, float, float]:
        if cvd is None:
            return _oklab(hx)
        rgb = _hex_to_rgb01(hx)
        lin = [_srgb_to_linear(v) for v in rgb]
        mat = _CVD_MATS[cvd]
        sim_lin = [sum(mat[i][j] * lin[j] for j in range(3)) for i in range(3)]
        # back to gamma-encoded sRGB (clamped — simulation can go slightly
        # out of gamut), then OKLab
        sim = tuple(max(0.0, min(1.0, max(0.0, v) ** (1 / 2.4) * 1.055 - 0.055)) for v in sim_lin)  # type: ignore[assignment]
        r, g, b = sim  # type: ignore[misc]
        l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
        m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
        s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
        l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
        return (
            0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
        )
    a, b = lab(h1), lab(h2)
    return math.dist(a, b) * 100


def _contrast(fg: str, bg: str) -> float:
    def rel(hx: str) -> float:
        r, g, b = (_srgb_to_linear(v) for v in _hex_to_rgb01(hx))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    l1, l2 = sorted((rel(fg), rel(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def validate_palette(colors: list[str], surface: str, mode: str,
                     extra_status: list[str] | None = None) -> list[str]:
    """Six-checks port; returns human-readable lines, raises on hard FAIL.

    `colors` are the categorical series (pair-gated); `extra_status` are status
    hues checked for band/chroma/contrast only — a status color never carries
    series identity, so it is exempt from series pair gating (icon + label
    pairing is the required mitigation instead).
    """
    out: list[str] = []
    band = (0.43, 0.77) if mode == "light" else (0.48, 0.67)
    hard_fail = False
    for hx in list(colors) + list(extra_status or []):
        L, a, b = _oklab(hx)
        chroma = math.hypot(a, b)
        ok_band = band[0] <= L <= band[1]
        ok_chroma = chroma >= 0.10
        out.append(f"  {hx}  L={L:.3f} C={chroma:.3f}  band {'ok' if ok_band else 'FAIL'}"
                   f"  chroma {'ok' if ok_chroma else 'FAIL'}  contrast {_contrast(hx, surface):.2f}:1")
        hard_fail |= not (ok_band and ok_chroma)
    worst: tuple[float, tuple[str, str]] | None = None
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            for cvd in (None, "protan", "deutan"):
                d = _delta_e(colors[i], colors[j], cvd)
                if worst is None or d < worst[0]:
                    worst = (d, (colors[i], colors[j]))
    assert worst is not None
    out.append(f"  worst series pair ΔE (normal/protan/deutan, all pairs): {worst[0]:.1f} "
               f"({worst[1][0]} vs {worst[1][1]}) -> {'ok (>=8)' if worst[0] >= 8 else 'warn band 6-8 (secondary encoding required)' if worst[0] >= 6 else 'FAIL'}")
    if worst[0] < 6:
        hard_fail = True
    out.insert(0, f"palette[{mode}]:")
    if hard_fail:
        raise SystemExit("palette validation FAILED:\n" + "\n".join(out))
    return out


# --------------------------------------------------------------------------
# Trace parsing
# --------------------------------------------------------------------------

START_TO_END = {
    "agent_active_start": "agent_active_end",
    "model_request": ("model_response", "model_error"),
    "tool_execution_start": "tool_execution_end",
    "permission_wait_start": "permission_wait_end",
    "input_wait_start": "input_wait_end",
}
END_TO_START = {
    "agent_active_end": "agent_active_start",
    "model_response": "model_request", "model_error": "model_request",
    "tool_execution_end": "tool_execution_start",
    "permission_wait_end": "permission_wait_start",
    "input_wait_end": "input_wait_start",
}


def fmt_compact(n: float) -> str:
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            v = n / div
            return f"{v:.1f}".rstrip("0").rstrip(".") + suf
    return f"{n:.0f}"


def fmt_clock(ms: float) -> str:
    s = int(ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def parse_trace(path: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                break  # torn final line from a live writer
    if not events:
        raise SystemExit(f"no parseable events in {path}")

    last_ts = max(e["monotonic_ns"] for e in events)
    last_elapsed = max(e["elapsed_ms"] for e in events)
    run = next((e for e in events if e["event"] == "run_start"), events[0])
    meta_src = run.get("data", {})

    # ---- agents ----------------------------------------------------------
    agents: dict[str, dict[str, Any]] = {}

    def agent(aid: str | None) -> dict[str, Any]:
        aid = aid or "?"
        return agents.setdefault(aid, {
            "id": aid, "name": aid, "role": "", "parent": None,
            "spawn_s": None, "state": "running", "end_s": None,
            "model_req": 0, "model_err": 0, "tin": 0, "tout": 0,
            "tools_ok": 0, "tools_err": 0, "msgs_sent": 0, "msgs_recv": 0,
            "active_ms": 0.0, "task": "", "exec": "",
        })

    # names/roles/parents
    for e in events:
        d = e.get("data") or {}
        if e["event"] == "agent_create":
            a = agent(e["agent_id"])
            a["name"] = d.get("name") or a["name"]
            a["parent"] = e.get("parent_agent_id")
            a["spawn_s"] = e["elapsed_ms"]
            a["role"] = d.get("role") or ""
            a["exec"] = d.get("execution") or ""
            a["task"] = (d.get("task") or "").strip()
        elif e["event"] == "agent_start" and e["agent_id"] == "agent-root":
            a = agent(e["agent_id"])
            a["role"] = d.get("role") or a["role"] or "lead"
            a["spawn_s"] = e["elapsed_ms"]
        elif e["event"] == "agent_end":
            a = agent(e["agent_id"])
            a["state"] = "ended"
            a["end_s"] = e["elapsed_ms"]

    name_of = {aid: a["name"] for aid, a in agents.items()}
    root_id = next((aid for aid, a in agents.items() if a["parent"] is None), "agent-root")

    # ---- spans (paired start/end) ---------------------------------------
    open_spans: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    intervals: list[dict[str, Any]] = []   # {kind, agent, s, e_ms, open, data}
    for e in events:
        ev = e["event"]
        aid = e.get("agent_id") or "?"
        if ev in START_TO_END:
            open_spans[(ev, e.get("span_id") or aid)].append(e)
            continue
        key_ev = END_TO_START.get(ev)
        if key_ev is None:
            continue
        stack = open_spans.get((key_ev, e.get("span_id") or aid))
        start = stack.pop() if stack else None  # LIFO matches nested spans
        s_ms = start["elapsed_ms"] if start else e["elapsed_ms"]
        intervals.append({
            "kind": key_ev, "agent": start.get("agent_id") if start else aid,
            "s": s_ms, "e": e["elapsed_ms"], "open": False,
            "data": (start or {}).get("data") or {}, "end_data": d,
        })
    for (start_ev, _key), stack in open_spans.items():
        for start in stack:
            intervals.append({
                "kind": start_ev, "agent": start.get("agent_id") or "?",
                "s": start["elapsed_ms"], "e": last_elapsed, "open": True,
                "data": start.get("data") or {}, "end_data": {},
            })

    # ---- per-agent counters ---------------------------------------------
    tasks: dict[str, dict[str, Any]] = {}
    tool_counts: Counter[str] = Counter()
    tool_err_counts: Counter[str] = Counter()
    turns: list[dict[str, Any]] = []
    compactions: list[dict[str, Any]] = []
    messages = 0
    for e in events:
        d = e.get("data") or {}
        aid = e.get("agent_id")
        ev = e["event"]
        if aid:
            a = agent(aid)
        if ev == "context_compact":
            compactions.append({"agent": aid, "s": e["elapsed_ms"]})
        if ev == "model_request":
            a["model_req"] += 1
        elif ev == "model_response":
            u = d.get("usage") or {}
            a["tin"] += u.get("input_tokens") or 0
            a["tout"] += u.get("output_tokens") or 0
        elif ev == "model_error":
            a["model_err"] += 1
        elif ev == "tool_execution_start":
            tool_counts[d.get("tool") or "?"] += 1
        elif ev == "tool_execution_end":
            if d.get("status") == "ok":
                a["tools_ok"] += 1
            else:
                a["tools_err"] += 1
                tool_err_counts[d.get("tool") or "?"] += 1
        elif ev == "message_send":
            a["msgs_sent"] += 1; messages += 1
        elif ev == "message_deliver":
            a["msgs_recv"] += 1
        elif ev == "turn_start":
            turns.append({"n": len(turns) + 1, "s": e["elapsed_ms"],
                          "trigger": d.get("trigger") or "?",
                          "preview": ((d.get("request") or {}).get("preview") or "").strip(),
                          "end": None})
        elif ev == "turn_end":
            if turns:
                turns[-1]["end"] = e["elapsed_ms"]
                turns[-1]["status"] = d.get("status") or "?"
        elif ev == "task_create":
            tasks[d.get("id") or d.get("task_id") or "?"] = {
                "id": d.get("id") or d.get("task_id"), "subject": d.get("subject") or "",
                "by": "lead" if aid == root_id else name_of.get(aid, aid), "at": e["elapsed_ms"],
                "blocked": list(d.get("blockedBy") or []),
                "claim": None, "status": d.get("status") or "open",
            }
        elif ev == "task_update":
            t = tasks.get(d.get("task_id"))
            if t:
                if d.get("blocked_by_task_ids") is not None:
                    t["blocked"] = list(d["blocked_by_task_ids"])
                if d.get("status"):
                    t["status"] = d["status"]
        elif ev == "task_complete":
            t = tasks.get(d.get("task_id"))
            if t:
                t["status"] = "done"
        elif ev == "task_claim":
            t = tasks.get(d.get("task_id"))
            if t:
                t["claim"] = d.get("owner") or name_of.get(aid, aid)
                t["claim_agent"] = aid
                t["status"] = t["status"] if t["status"] == "done" else "claimed"

    for iv in intervals:
        if iv["kind"] == "agent_active_start":
            a = agent(iv["agent"])
            a["active_ms"] += iv["e"] - iv["s"]

    agent_list = sorted(agents.values(), key=lambda a: (a["spawn_s"] is None, a["spawn_s"] or 0, a["id"]))
    root = agents.get(root_id, agent_list[0])
    order = {a["id"]: i for i, a in enumerate(agent_list)}

    # timeline intervals, ordered per lane
    tl = [iv for iv in intervals if iv["kind"] in
          ("agent_active_start", "model_request", "tool_execution_start",
           "permission_wait_start", "input_wait_start")]
    for iv in tl:
        if iv["kind"] == "tool_execution_start":
            iv["tool"] = iv["data"].get("tool") or "?"
            iv["status"] = iv["end_data"].get("status") or "?"
        elif iv["kind"] == "model_request":
            iv["purpose"] = iv["data"].get("purpose") or iv["end_data"].get("purpose") or ""
            u = iv["end_data"].get("usage") or {}
            iv["tokens"] = (u.get("input_tokens"), u.get("output_tokens"))
            iv["err"] = iv["end_data"].get("status") not in (None, "ok")
    tl.sort(key=lambda iv: (order.get(iv["agent"], 99), iv["s"]))

    return {
        "file": path.name,
        "run_id": run.get("run_id"),
        "model": meta_src.get("model"), "provider": meta_src.get("provider"),
        "base_url": meta_src.get("base_url"), "pid": meta_src.get("pid"),
        "cwd": meta_src.get("cwd"),
        "started": run.get("timestamp"),
        "snapshot": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "n_events": len(events),
        "last_elapsed": last_elapsed,
        "agents": agent_list,
        "root_id": root["id"],
        "lanes": [a["id"] for a in agent_list],
        "names": name_of,
        "intervals": tl,
        "compactions": compactions,
        "messages": messages,
        "turns": turns,
        "tasks": list(tasks.values()),
        "tool_counts": dict(tool_counts),
        "tool_err_counts": dict(tool_err_counts),
        "tokens_in": sum(a["tin"] for a in agents.values()),
        "tokens_out": sum(a["tout"] for a in agents.values()),
        "model_req_total": sum(a["model_req"] for a in agents.values()),
        "model_err_total": sum(a["model_err"] for a in agents.values()),
        "tools_total": sum(tool_counts.values()),
    }


# --------------------------------------------------------------------------
# HTML generation
# --------------------------------------------------------------------------

CSS = """
:root { color-scheme: light dark; }
.viz-root {
  --surface-1:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --wash:#efeeea; --accent:#2a78d6;
  --c-model:#2a78d6; --c-perm:#eb6834; --c-tool:#1baf7a; --c-msg:#898781;
  --c-err:#d03b3b; --c-input:#c3c2b7;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  color: var(--ink); background: var(--page); margin:0; padding:20px 24px 40px;
}
.viz-root[data-mode="dark"] {
  --surface-1:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
  --wash:#262624; --accent:#3987e5;
  --c-model:#3987e5; --c-perm:#d95926; --c-tool:#199e70; --c-msg:#898781;
  --c-err:#d03b3b; --c-input:#383835;
}
.viz-root * { box-sizing:border-box; }
h1 { font-size:18px; margin:0 0 2px; font-weight:650; }
.sub { color:var(--ink-2); font-size:12.5px; margin:0 0 12px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 16px; align-items:center; }
.chip { font-size:11.5px; color:var(--ink-2); border:1px solid var(--border);
  background:var(--surface-1); border-radius:999px; padding:3px 10px; }
.chip b { color:var(--ink); font-weight:600; }
.pill { display:inline-flex; align-items:center; gap:6px; font-size:11.5px; font-weight:600;
  border-radius:999px; padding:3px 10px; border:1px solid var(--border); background:var(--surface-1); }
.pill .dot { width:8px; height:8px; border-radius:50%; background:var(--accent); }
.pill.run .dot { animation:pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.theme-btn { margin-left:auto; font:inherit; font-size:11.5px; color:var(--ink-2);
  background:var(--surface-1); border:1px solid var(--border); border-radius:999px; padding:3px 12px; cursor:pointer; }
.card { background:var(--surface-1); border:1px solid var(--border); border-radius:10px;
  padding:14px 16px; margin:0 0 16px; overflow-x:auto; }
.card h2 { font-size:13px; font-weight:650; margin:0 0 10px; }
.card h2 .n { color:var(--muted); font-weight:400; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:0 0 16px; }
.tile { background:var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:12px 14px; }
.tile .lb { font-size:11.5px; color:var(--ink-2); }
.tile .v { font-size:24px; font-weight:600; margin-top:2px; }
.tile .x { font-size:11.5px; color:var(--muted); margin-top:2px; }
.legend { display:flex; flex-wrap:wrap; gap:12px; font-size:11.5px; color:var(--ink-2);
  align-items:center; margin-bottom:8px; }
.legend .k { display:inline-flex; align-items:center; gap:5px; }
.sw { width:14px; height:9px; border-radius:2px; display:inline-block; }
.sw.r3 { width:9px; height:9px; border-radius:50%; }
.sw.dm { width:9px; height:9px; transform:rotate(45deg); border-radius:1px; }
.sw.ln { width:14px; height:2px; border-radius:0; }
#tooltip { position:fixed; z-index:10; pointer-events:none; background:var(--surface-1);
  border:1px solid var(--border); border-radius:8px; padding:8px 10px; font-size:12px;
  box-shadow:0 4px 16px rgba(0,0,0,.12); max-width:340px; display:none; }
#tooltip .tv { font-weight:650; font-size:12.5px; }
#tooltip .tm { color:var(--muted); font-size:11px; margin-top:3px; }
#tooltip .tr { display:flex; gap:6px; margin-top:3px; color:var(--ink-2); }
#tooltip .tr i { width:10px; height:3px; border-radius:1.5px; margin-top:6px; flex:none; }
table { border-collapse:collapse; width:100%; font-size:12px; }
th { text-align:left; color:var(--muted); font-weight:500; font-size:11px;
  border-bottom:1px solid var(--axis); padding:4px 8px; white-space:nowrap; }
td { border-bottom:1px solid var(--grid); padding:4px 8px; vertical-align:top; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
td .st { font-size:10.5px; border-radius:999px; padding:1px 8px; border:1px solid var(--border); color:var(--ink-2); white-space:nowrap; }
td .st.done { color:#006300; border-color:rgba(0,99,0,.35); }
.viz-root[data-mode="dark"] td .st.done { color:#0ca30c; }
td .st.run2 { color:var(--accent); border-color:var(--accent); }
.muted { color:var(--muted); }
svg text { font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
#tree, #timeline { min-width: 980px; display: block; }
.bar { transition:filter .08s; }
.hit { fill:transparent; }
.hit:focus { outline:none; }
.hit:focus-visible { stroke:var(--accent); stroke-width:1.5; }
.foot { color:var(--muted); font-size:11.5px; margin-top:6px; }
.foot code { font-size:11px; }
"""

JS = r"""
const DATA = JSON.parse(document.getElementById('viz-data').textContent);
const $ = (t, a, parent) => { const el = document.createElementNS('http://www.w3.org/2000/svg', t);
  for (const k in a) el.setAttribute(k, a[k]); if (parent) parent.appendChild(el); return el; };
const esc = s => String(s);

/* ---------- theme toggle ---------- */
const root = document.querySelector('.viz-root');
const saved = localStorage.getItem('viz-theme');
if (saved) root.dataset.mode = saved;
document.getElementById('theme-btn').addEventListener('click', () => {
  const m = root.dataset.mode === 'dark' ? 'light' : 'dark';
  root.dataset.mode = m; localStorage.setItem('viz-theme', m);
});

/* ---------- tooltip ---------- */
const tip = document.getElementById('tooltip');
function showTip(rows, x, y) {
  tip.textContent = '';
  for (const r of rows) {
    if (r.v !== undefined) {
      const d = document.createElement('div'); d.className = 'tr';
      if (r.c) { const i = document.createElement('i'); i.style.background = r.c; d.appendChild(i); }
      const val = document.createElement('span'); val.className = 'tv'; val.textContent = r.v; d.appendChild(val);
      if (r.l) { const lb = document.createElement('span'); lb.textContent = r.l; d.appendChild(lb); }
      tip.appendChild(d);
    } else {
      const d = document.createElement('div'); d.className = 'tm'; d.textContent = r.t; tip.appendChild(d);
    }
  }
  tip.style.display = 'block';
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(x + 14, innerWidth - w - 8) + 'px';
  tip.style.top = Math.min(y + 14, innerHeight - h - 8) + 'px';
}
function hideTip() { tip.style.display = 'none'; }

/* ---------- helpers ---------- */
const names = DATA.names;
const laneName = id => (names[id] && names[id] !== id) ? names[id] : id.replace(/^agent-/, '');
function agentById(id) { return DATA.agents.find(a => a.id === id); }
const fmtDur = ms => { const s = Math.round(ms / 1000); if (s < 60) return s + 's';
  const m = Math.floor(s / 60); return m + 'm' + String(s % 60).padStart(2, '0') + 's'; };
const fmtT = ms => { const t = Math.floor(ms / 1000); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); };
const fmtN = n => n == null ? '—' : n >= 1e9 ? (n / 1e9).toFixed(1) + 'B'
  : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(n);

/* ---------- 1. agent tree ---------- */
(function drawTree() {
  const svg = document.getElementById('tree');
  const W = 1140;
  const kids = DATA.agents.filter(a => a.parent === DATA.root_id);
  const rootA = agentById(DATA.root_id);
  const perRow = 8, gapX = 8, nodeW = (W - 40 - (perRow - 1) * gapX) / perRow, nodeH = 46, gapY = 12;
  const rows = Math.max(1, Math.ceil(kids.length / perRow));
  const H = 92 + rows * (nodeH + gapY);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', '100%');
  svg.style.maxWidth = W + 'px'; svg.setAttribute('role', 'img');
  // root node
  const rw = 300, rx = (W - rw) / 2, ry = 8;
  const rootG = $('g', { tabindex: '0', class: 'hit' }, svg);
  $('rect', { x: rx, y: ry, width: rw, height: 40, rx: 8,
    fill: 'var(--accent)', opacity: 0.12, stroke: 'var(--accent)', 'stroke-width': 1 }, rootG);
  const rt = $('text', { x: W / 2, y: ry + 17, 'text-anchor': 'middle', 'font-size': 12.5,
    'font-weight': 650, fill: 'var(--ink)' }, rootG); rt.textContent = laneName(rootA.id) + '  (lead)';
  const rt2 = $('text', { x: W / 2, y: ry + 31, 'text-anchor': 'middle', 'font-size': 10.5, fill: 'var(--ink-2)' }, rootG);
  rt2.textContent = `${rootA.model_req} model calls · ${rootA.tools_ok + rootA.tools_err} tools · ${fmtN(rootA.tin)} tok in`;
  const tipRows = a => [
    { v: laneName(a.id), l: a.id === rootA.id ? 'lead agent' : 'teammate' },
    { t: (a.role || '').slice(0, 160) },
    { t: 'task: ' + ((a.task || '').slice(0, 160) || '—') },
    { v: `${a.model_req} model calls`, l: `${fmtN(a.tin)} tok in / ${fmtN(a.tout)} out` },
    { v: `${a.tools_ok + a.tools_err} tool calls`, l: a.tools_err ? a.tools_err + ' errored' : 'all ok' },
    { t: 'state: ' + (a.state === 'ended' ? 'ended ' + fmtT(a.end_s) : 'running at snapshot') },
  ];
  const bind = (el, a) => {
    el.addEventListener('pointermove', ev => showTip(tipRows(a), ev.clientX, ev.clientY));
    el.addEventListener('pointerleave', hideTip);
    el.addEventListener('focus', () => { const b = el.getBoundingClientRect(); showTip(tipRows(a), b.left, b.bottom); });
    el.addEventListener('blur', hideTip);
  };
  bind(rootG, rootA);
  // bus edges
  const busY = ry + 40 + 18;
  $('path', { d: `M ${W / 2} ${ry + 40} V ${busY}`, stroke: 'var(--axis)', fill: 'none', 'stroke-width': 1 }, svg);
  const xr = i => 20 + (i % perRow) * (nodeW + gapX);
  const yr = i => 92 + Math.floor(i / perRow) * (nodeH + gapY);
  $('path', { d: `M ${xr(0) + nodeW / 2} ${busY} H ${xr(Math.min(kids.length, perRow) - 1) + nodeW / 2}`,
    stroke: 'var(--axis)', fill: 'none', 'stroke-width': 1 }, svg);
  kids.forEach((a, i) => {
    const x = xr(i), y = yr(i), cx = x + nodeW / 2;
    $('path', { d: `M ${cx} ${busY} V ${y}`, stroke: 'var(--axis)', fill: 'none', 'stroke-width': 1 }, svg);
    const nG = $('g', { tabindex: '0', class: 'hit' }, svg);
    $('rect', { x, y, width: nodeW, height: nodeH, rx: 8, fill: 'var(--surface-1)',
      stroke: 'var(--border)', 'stroke-width': 1 }, nG);
    const dot = $('circle', { cx: x + 12, cy: y + 14, r: 4,
      fill: a.state === 'ended' ? 'var(--muted)' : 'var(--accent)' }, nG);
    if (a.state !== 'ended') $('animate', { attributeName: 'opacity', values: '1;.3;1', dur: '1.6s',
      repeatCount: 'indefinite' }, dot);
    const t1 = $('text', { x: x + 22, y: y + 18, 'font-size': 11.5, 'font-weight': 600, fill: 'var(--ink)' }, nG);
    t1.textContent = laneName(a.id);
    const t2 = $('text', { x: x + 10, y: y + 34, 'font-size': 10, fill: 'var(--ink-2)' }, nG);
    t2.textContent = `${a.model_req}m·${a.tools_ok + a.tools_err}t · ` +
      (a.state === 'ended' ? 'ended ' + fmtT(a.end_s) : 'running');
    bind(nG, a);
  });
})();

/* ---------- 2. swimlane timeline ---------- */
(function drawTimeline() {
  const svg = document.getElementById('timeline');
  const W = 1140, padL = 150, padR = 20, plotW = W - padL - padR;
  const T = DATA.last_elapsed;
  const rowH = 18, bandH = 11, laneGap = 5;
  const msRow = 26, axisH = 26, laneTop = msRow + 6;
  const lanes = DATA.lanes;
  const H = laneTop + lanes.length * (rowH + laneGap) + 8 + axisH;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', '100%');
  svg.style.maxWidth = W + 'px';
  const X = ms => padL + (ms / T) * plotW;
  const cols = getComputedStyle(root);
  const C = n => cols.getPropertyValue(n).trim();

  // turn boundaries + gridlines + axis
  const axis = $('g', {}, svg);
  const minutes = Math.ceil(T / 60000 / 15) * 15;
  for (let m = 0; m <= minutes; m += 15) {
    const x = X(m * 60000);
    $('line', { x1: x, y1: msRow, x2: x, y2: H - axisH + 6, stroke: 'var(--grid)', 'stroke-width': 1 }, axis);
    const t = $('text', { x, y: H - 8, 'text-anchor': 'middle', 'font-size': 10.5, fill: 'var(--muted)',
      style: 'font-variant-numeric:tabular-nums' }, axis); t.textContent = m + 'm';
  }
  DATA.turns.forEach(t => {
    const x = X(t.s);
    $('line', { x1: x, y1: 0, x2: x, y2: H - axisH + 6, stroke: 'var(--axis)', 'stroke-width': 1 }, axis);
    const d = $('path', { d: `M ${x} 12 l 5 5 l -5 5 l -5 -5 Z`, fill: 'var(--ink)' }, axis);
    const lb = $('text', { x: x + 9, y: 21, 'font-size': 10, fill: 'var(--ink-2)' }, axis);
    lb.textContent = 'T' + t.n + (t.preview ? ' · ' + t.preview.slice(0, 60) : '');
    const dTip = [{ v: 'Turn ' + t.n + ' start', l: fmtT(t.s) }, { t: 'trigger: ' + t.trigger },
      { t: t.preview || '' }, { t: t.end ? 'ended ' + fmtT(t.end) + ' · ' + (t.status || '') : 'still open at snapshot' }];
    const hit = $('rect', { x: x - 8, y: 2, width: 16, height: 22, class: 'hit', tabindex: '0',
      role: 'img' }, axis);
    hit.addEventListener('pointermove', ev => showTip(dTip, ev.clientX, ev.clientY));
    hit.addEventListener('pointerleave', hideTip);
    hit.addEventListener('focus', () => { const b = hit.getBoundingClientRect(); showTip(dTip, b.left, b.bottom); });
    hit.addEventListener('blur', hideTip);
  });
  { // snapshot marker
    const x = X(T);
    $('line', { x1: x, y1: 0, x2: x, y2: H - axisH + 6, stroke: 'var(--accent)', 'stroke-width': 1,
      opacity: 0.55 }, axis);
    const t = $('text', { x: x - 4, y: 12, 'text-anchor': 'end', 'font-size': 10, fill: 'var(--accent)' }, axis);
    t.textContent = 'snapshot';
  }

  // lanes
  const tipFor = iv => {
    const a = laneName(iv.agent);
    if (iv.kind === 'model_request') {
      const rows = [{ v: 'Model call', l: a + (iv.open ? ' · still open' : '') },
        { t: 'purpose: ' + (iv.purpose || '?') }];
      if (iv.tokens && iv.tokens[0] != null) rows.push({ v: fmtN(iv.tokens[0]) + ' in / ' + fmtN(iv.tokens[1]) + ' out', l: 'tokens' });
      rows.push({ t: fmtT(iv.s) + ' → ' + fmtT(iv.e) + ' · ' + fmtDur(iv.e - iv.s) });
      if (iv.err) rows.push({ t: 'ended with error' });
      return rows;
    }
    if (iv.kind === 'tool_execution_start') {
      const bad = iv.status && iv.status !== 'ok';
      return [{ v: (bad ? '✕ ' : '') + iv.tool, l: a },
        { t: 'status: ' + iv.status },
        { t: fmtT(iv.s) + ' → ' + fmtT(iv.e) + ' · ' + fmtDur(Math.max(iv.e - iv.s, 1)) }];
    }
    if (iv.kind === 'permission_wait_start')
      return [{ v: 'Permission wait', l: a + ' · ' + (iv.data.tool || '') },
        { t: fmtT(iv.s) + ' → ' + fmtT(iv.e) + ' · ' + fmtDur(iv.e - iv.s) + ' (human approval)' }];
    if (iv.kind === 'input_wait_start')
      return [{ v: 'Waiting for user input', l: a }, { t: fmtT(iv.s) + ' → ' + fmtT(iv.e) }];
    return [{ v: 'Agent active', l: a }, { t: fmtT(iv.s) + ' → ' + fmtT(iv.e) +
      (iv.open ? ' · open at snapshot' : '') }];
  };
  const fillFor = iv => iv.kind === 'model_request' ? 'var(--c-model)'
    : iv.kind === 'tool_execution_start' ? (iv.status && iv.status !== 'ok' ? 'var(--c-err)' : 'var(--c-tool)')
    : iv.kind === 'permission_wait_start' ? 'var(--c-perm)'
    : iv.kind === 'input_wait_start' ? 'var(--c-input)' : null;

  let laneY = laneTop;
  lanes.forEach(id => {
    const a = agentById(id);
    // label
    const lb = $('text', { x: padL - 10, y: laneY + rowH - 4, 'text-anchor': 'end', 'font-size': 11,
      fill: 'var(--ink)' }, svg);
    lb.textContent = laneName(id);
    const lb2 = $('text', { x: padL - 10, y: laneY + rowH + 8, 'text-anchor': 'end', 'font-size': 9,
      fill: 'var(--muted)', style: 'font-variant-numeric:tabular-nums' }, svg);
    lb2.textContent = a.state === 'ended' ? 'ended' : 'running';
    const ivs = DATA.intervals.filter(iv => iv.agent === id);
    // rows packing (agent_active is the background wash, its own layer)
    const rows = [];
    const activeIvs = ivs.filter(iv => iv.kind === 'agent_active_start');
    const marks = DATA.compactions.filter(c => c.agent === id);
    const bars = ivs.filter(iv => iv.kind !== 'agent_active_start');
    const laneG = $('g', {}, svg);
    activeIvs.forEach(iv => {
      const x1 = X(iv.s), x2 = X(iv.e);
      $('rect', { x: x1, y: laneY + (rowH - bandH) / 2 - 2, width: Math.max(x2 - x1, 1),
        height: bandH + 4, rx: 3, fill: 'var(--wash)' }, laneG);
    });
    bars.forEach(iv => {
      let x1 = X(iv.s), x2 = X(iv.e);
      const w = Math.max(x2 - x1, 1.5);
      let r = rows.findIndex(last => x1 >= last + 2);
      if (r === -1) { rows.push(0); r = rows.length - 1; }
      if (x1 < rows[r] + 2) { const d = rows[r] + 2 - x1; x1 += d; }
      rows[r] = x1 + w;
      const y = laneY + r * (bandH + 3);
      const fill = fillFor(iv);
      const barW = Math.max(w, 1.5);
      const gEl = $('g', { class: 'hit', tabindex: '0', role: 'img' }, laneG);
      if (barW >= 5) {
        const rr = Math.min(3, barW / 2);
        $('path', { d: `M ${x1} ${y} H ${x1 + barW - rr} a ${rr} ${rr} 0 0 1 ${rr} ${rr} v ${bandH - 2 * rr} a ${rr} ${rr} 0 0 1 -${rr} ${rr} H ${x1} Z`,
          fill }, gEl);
      } else {
        $('rect', { x: x1, y, width: barW, height: bandH, fill }, gEl);
      }
      // generous transparent hit target around the mark (>= 24px tall)
      $('rect', { x: x1 - 2, y: laneY - 3, width: barW + 4, height: rowH + laneGap, class: 'hit' }, gEl);
      const tt = tipFor(iv);
      gEl.addEventListener('pointermove', ev => showTip(tt, ev.clientX, ev.clientY));
      gEl.addEventListener('pointerleave', hideTip);
      gEl.addEventListener('focus', () => { const b = gEl.getBoundingClientRect(); showTip(tt, b.left, b.bottom); });
      gEl.addEventListener('blur', hideTip);
    });
    marks.forEach(c => {
      const x = X(c.s), y = laneY + rowH - 2;
      const dG = $('g', { class: 'hit', tabindex: '0', role: 'img' }, laneG);
      $('path', { d: `M ${x} ${y - 4} l 4 4 l -4 4 l -4 -4 Z`, fill: 'var(--c-msg)' }, dG);
      const tt = [{ v: 'Context compaction', l: laneName(id) }, { t: fmtT(c.s) }];
      dG.addEventListener('pointermove', ev => showTip(tt, ev.clientX, ev.clientY));
      dG.addEventListener('pointerleave', hideTip);
      dG.addEventListener('focus', () => { const b = dG.getBoundingClientRect(); showTip(tt, b.left, b.bottom); });
      dG.addEventListener('blur', hideTip);
    });
    laneY += rowH + laneGap;
  });
})();

/* ---------- 3. tool usage bars ---------- */
(function drawTools() {
  const host = document.getElementById('tools');
  const entries = Object.entries(DATA.tool_counts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return;
  const max = entries[0][1];
  const errs = DATA.tool_err_counts;
  const tbl = document.createElement('div');
  entries.forEach(([tool, n]) => {
    const row = document.createElement('div');
    row.style.cssText = 'display:grid;grid-template-columns:120px 1fr 80px;gap:10px;align-items:center;margin:5px 0;';
    const lb = document.createElement('div'); lb.style.cssText = 'font-size:12px;color:var(--ink-2);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    lb.textContent = tool; lb.title = tool;
    const track = document.createElement('div'); track.style.cssText = 'position:relative;height:14px;';
    const e = errs[tool] || 0, okN = n - e;
    const bar = document.createElement('div');
    bar.style.cssText = `position:absolute;left:0;top:0;height:14px;border-radius:0 4px 4px 0;background:var(--c-tool);width:${Math.max(0.4, okN / max * 100)}%;`;
    track.appendChild(bar);
    if (e) { const eb = document.createElement('div');
      eb.style.cssText = `position:absolute;left:${okN / max * 100}%;top:0;height:14px;width:${Math.max(0.4, e / max * 100)}%;background:var(--c-err);border-radius:0 4px 4px 0;`;
      track.appendChild(eb); }
    const val = document.createElement('div'); val.style.cssText = 'font-size:12px;font-variant-numeric:tabular-nums;';
    val.textContent = n + (e ? ` (${e} err)` : '');
    row.append(lb, track, val); tbl.appendChild(row);
    const tt = [{ v: String(n) + ' calls', l: tool }].concat(e ? [{ t: e + ' errored' }] : []);
    row.addEventListener('pointermove', ev => showTip(tt, ev.clientX, ev.clientY));
    row.addEventListener('pointerleave', hideTip);
  });
  host.appendChild(tbl);
})();

/* ---------- 4. tables ---------- */
(function buildTables() {
  const ta = document.getElementById('tbl-agents');
  const thead = document.createElement('thead'); const trh = document.createElement('tr');
  ['Agent', 'State', 'Model calls', 'Tokens in', 'Tokens out', 'Tool calls', 'Msgs →/←', 'Active'].forEach(h => {
    const th = document.createElement('th'); if (['Model calls','Tokens in','Tokens out','Tool calls','Msgs →/←','Active'].includes(h)) th.className = 'num';
    th.textContent = h; trh.appendChild(th); });
  thead.appendChild(trh); ta.appendChild(thead);
  const tb = document.createElement('tbody');
  DATA.agents.forEach(a => {
    const tr = document.createElement('tr');
    const c = (v, cls) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = v; tr.appendChild(td); };
    c(laneName(a.id));
    const st = document.createElement('td'); const sp = document.createElement('span');
    sp.className = 'st ' + (a.state === 'ended' ? '' : 'run2'); sp.textContent = a.state === 'ended' ? 'ended ' + fmtT(a.end_s) : 'running';
    st.appendChild(sp); tr.appendChild(st);
    c(String(a.model_req) + (a.model_err ? ` (${a.model_err} err)` : ''), 'num');
    c(fmtN(a.tin), 'num'); c(fmtN(a.tout), 'num');
    c(String(a.tools_ok + a.tools_err) + (a.tools_err ? ` (${a.tools_err} err)` : ''), 'num');
    c(a.msgs_sent + ' / ' + a.msgs_recv, 'num');
    c(fmtDur(a.active_ms), 'num');
    tb.appendChild(tr);
  });
  ta.appendChild(tb);

  const tt = document.getElementById('tbl-tasks');
  const th2 = document.createElement('thead'); const trh2 = document.createElement('tr');
  ['Task', 'Subject', 'Created by', 'Claimed by', 'Blocked by', 'Status'].forEach(h => { const th = document.createElement('th'); th.textContent = h; trh2.appendChild(th); });
  th2.appendChild(trh2); tt.appendChild(th2);
  const tb2 = document.createElement('tbody');
  DATA.tasks.forEach(t => {
    const tr = document.createElement('tr');
    const td = (v, cls) => { const d = document.createElement('td'); if (cls) d.className = cls; d.textContent = v; tr.appendChild(d); return d; };
    const idtd = td((t.id || '').replace('task_', '')); idtd.style.fontVariantNumeric = 'tabular-nums';
    const sub = td(t.subject || ''); sub.style.maxWidth = '420px';
    if (t.subject) { sub.title = t.subject; sub.style.overflow = 'hidden'; sub.style.textOverflow = 'ellipsis'; sub.style.whiteSpace = 'nowrap'; }
    td(t.by || ''); td(t.claim || '—');
    td(t.blocked && t.blocked.length ? t.blocked.map(b => String(b).replace('task_', '')).join(', ') : '—');
    const st = document.createElement('td'); const sp = document.createElement('span');
    sp.className = 'st ' + (t.status === 'done' ? 'done' : t.status === 'claimed' ? 'run2' : '');
    sp.textContent = t.status; st.appendChild(sp); tr.appendChild(st);
    tb2.appendChild(tr);
  });
  tt.appendChild(tb2);
})();
"""


def build_html(d: dict[str, Any], palette_report: list[str]) -> str:
    tiles = [
        ("Wall time", fmt_clock(d["last_elapsed"]), f"{d['last_elapsed']/60000:.0f} min · snapshot {d['snapshot'][11:19]}Z"),
        ("Teammates", str(len(d["agents"]) - 1), f"{sum(1 for a in d['agents'] if a['state'] != 'ended')} still running"),
        ("Tasks", str(len(d["tasks"])), f"{sum(1 for t in d['tasks'] if t['status'] == 'done')} done · {sum(1 for t in d['tasks'] if t['claim'])} claimed"),
        ("Model calls", str(d["model_req_total"]), f"{d['model_err_total']} errored" if d["model_err_total"] else "no errors"),
        ("Tool calls", str(d["tools_total"]), f"{sum(d['tool_err_counts'].values())} errored" if d["tool_err_counts"] else "no errors"),
        ("Tokens", fmt_compact(d["tokens_in"]) + " in", fmt_compact(d["tokens_out"]) + " out · " + str(d["messages"]) + " inter-agent msgs"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="lb">{lb}</div><div class="v">{v}</div><div class="x">{x}</div></div>'
        for lb, v, x in tiles)
    legend = [
        ("Model call", "var(--c-model)", "sw"), ("Tool call (ok)", "var(--c-tool)", "sw"),
        ("Tool call (error)", "var(--c-err)", "sw"), ("Permission wait", "var(--c-perm)", "sw"),
        ("Context compaction", "var(--c-msg)", "dm"), ("Waiting for user input", "var(--c-input)", "sw"),
        ("Agent active (wash)", "var(--wash)", "sw"),
        ("Turn boundary", "var(--ink)", "dm"),
    ]
    legend_html = "".join(f'<span class="k"><span class="{cls}" style="background:{c}"></span>{lb}</span>'
                          for lb, c, cls in legend)
    running = sum(1 for a in d["agents"] if a["state"] != "ended")
    state = "run" if running else "done"
    state_txt = f"{running} agent{'' if running == 1 else 's'} still running" if running else "run complete"
    data_json = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    report_html = "\n".join("<!-- " + line + " -->" for line in palette_report)
    turns_note = ", ".join(f"T{t['n']} {fmt_clock(t['s'])}" for t in d["turns"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harness trace {d['run_id']} — workflow</title>
<style>{CSS}</style>
</head>
<body>
<div class="viz-root" data-mode="light">
  {report_html}
  <h1>Agent workflow — run {d['run_id']}</h1>
  <p class="sub">Rendered from <b>{d['n_events']:,}</b> events ({d['file']}, last at {fmt_clock(d['last_elapsed'])} elapsed).
  Turns: {turns_note}.</p>
  <div class="chips">
    <span class="pill {state}"><span class="dot"></span>{state_txt}</span>
    <span class="chip">model <b>{d['model']}</b></span>
    <span class="chip">{d['provider']} @ <b>{d['base_url']}</b></span>
    <span class="chip">pid <b>{d['pid']}</b></span>
    <span class="chip">started <b>{d['started'][11:19]}Z</b></span>
    <button class="theme-btn" id="theme-btn">Toggle dark mode</button>
  </div>

  <div class="tiles">{tiles_html}</div>

  <div class="card"><h2>Agent tree <span class="n">· {len(d['agents']) - 1} teammates spawned by the lead — hover for role, task and stats</span></h2>
    <svg id="tree" role="img" aria-label="Agent tree: lead agent and spawned teammates"></svg>
  </div>

  <div class="card"><h2>Timeline <span class="n">· one lane per agent · bars are model calls, tool executions, permission waits</span></h2>
    <div class="legend">{legend_html}</div>
    <svg id="timeline" role="img" aria-label="Swimlane timeline of agent activity"></svg>
  </div>

  <div class="card"><h2>Tool usage <span class="n">· calls by tool (green = ok, red tail = errored)</span></h2>
    <div id="tools"></div>
  </div>

  <div class="card"><h2>Agents <span class="n">· table view of the timeline</span></h2>
    <table id="tbl-agents"></table>
  </div>

  <div class="card"><h2>Tasks <span class="n">· {len(d['tasks'])} created via create_task / updated via update_task</span></h2>
    <table id="tbl-tasks"></table>
  </div>

  <p class="foot">Self-contained snapshot — regenerate after the run advances:
  <code>python3 scripts/trace_workflow_viz.py traces/{d['file']} -o trace_workflow_viz.html</code></p>
</div>
<script type="application/json" id="viz-data">{data_json}</script>
<script>{JS}</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trace", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("trace_workflow_viz.html"))
    args = ap.parse_args(argv)

    # palette: series slots 1,2,3 of the reference theme (the only set that
    # clears the all-pairs floors; compaction marks are shape-coded neutral
    # ink, not a fourth hue) + status critical, validated in both modes
    reports = []
    reports += validate_palette(["#2a78d6", "#eb6834", "#1baf7a"],
                                "#fcfcfb", "light", extra_status=["#d03b3b"])
    reports += validate_palette(["#3987e5", "#d95926", "#199e70"],
                                "#1a1a19", "dark", extra_status=["#d03b3b"])

    d = parse_trace(args.trace)
    html = build_html(d, reports)
    args.output.write_text(html)
    n_open = sum(1 for iv in d["intervals"] if iv["open"])
    print(f"wrote {args.output} ({len(html)/1024:.0f} KB, {d['n_events']} events, "
          f"{len(d['agents'])} agents, {len(d['tasks'])} tasks, {n_open} spans open at snapshot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
