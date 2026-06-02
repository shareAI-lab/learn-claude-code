#!/usr/bin/env python3
# Harness: workflow orchestration — deterministic multi-agent pipelines.
"""
s15_workflow_orchestration.py - Workflow Orchestration

A script (not the model) orchestrates multiple agents in structured patterns.
Three primitives: parallel (fan-out), pipeline (stages), and phase (tracking).

    parallel() — fan-out N independent agents:
    +-----------+     +-----------+     +-----------+
    | Agent A   |     | Agent B   |     | Agent C   |   (all run at once)
    | review    |     | review    |     | review    |
    +-----+-----+     +-----+-----+     +-----+-----+
          |                |                |
          +----------------+----------------+
                           |
                     collect results

    pipeline() — each item flows through stages:
    Item 1: [Stage1 ---- Stage2 ---- Stage3]
    Item 2:    [Stage1 ---- Stage2 ---- Stage3]   (overlapping)
    Item 3:       [Stage1 ---- Stage2 ---- Stage3]

    Script controls flow; agents just do their assigned work.
    This is different from s04 (subagent) where the MODEL decides
    what subagent to spawn. Here the HARNESS decides.

Key insight: "Orchestration is code, not prompts."
"""

import os
import threading
from pathlib import Path
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]


# -- Single agent runner (from s04, reused here) --
def run_agent(prompt: str, system_msg: str, tools: list = None, tool_handlers: dict = None) -> str:
    """Run one agent loop in-process, return final text output."""
    messages = [{"role": "user", "content": prompt}]
    for _ in range(20):
        kwargs = {"model": MODEL, "system": system_msg, "messages": messages, "max_tokens": 4000}
        if tools:
            kwargs["tools"] = tools
        response = client.messages.create(**kwargs)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = tool_handlers.get(block.name) if tool_handlers else None
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no output)"


# -- Workflow primitive #1: parallel() --
# Fan out N agents simultaneously, wait for all, collect results.
def parallel(tasks: list) -> list:
    """
    Run N agent prompts in parallel threads.

    tasks: list of {"prompt": str, "system": str, "label": str}
    returns: list of {"label": str, "result": str}
    """
    results = [None] * len(tasks)
    threads = []

    def worker(idx, task):
        print(f"  [parallel] {task['label']} started")
        result = run_agent(task["prompt"], task["system"])
        results[idx] = {"label": task["label"], "result": result}
        print(f"  [parallel] {task['label']} done")

    for i, task in enumerate(tasks):
        t = threading.Thread(target=worker, args=(i, task), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    return results


# -- Workflow primitive #2: pipeline() --
# Each item flows through stages. Different items can be at
# different stages simultaneously (no barrier between stages).
def pipeline(items: list, stages: list) -> list:
    """
    Process items through a series of stages.

    items: list of input values (strings)
    stages: list of {"name": str, "prompt_fn": callable(item, prev_result) -> str}
    returns: list of final results, one per item
    """
    # Simple sequential pipeline for teaching — each item completes
    # all stages before the next item starts. A production harness
    # would overlap items across stages using a thread pool.
    results = []
    for item in items:
        prev = item
        for stage in stages:
            print(f"  [pipeline] {stage['name']} on: {str(item)[:40]}")
            prompt = stage["prompt_fn"](item, prev)
            prev = run_agent(prompt, f"You are a {stage['name']} assistant. Be concise.")
        results.append(prev)
    return results


# -- Workflow primitive #3: phase() --
# Simple logging context manager for tracking workflow phases.
class phase:
    """Context manager that logs phase entry/exit."""
    _current = None

    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        print(f"\n>>> PHASE: {self.name}")
        phase._current = self.name
        return self

    def __exit__(self, *args):
        print(f">>> PHASE {self.name} complete\n")
        phase._current = None


# -- Demo: code review workflow --
# Three agents review code from different angles, then a fourth synthesizes.

BASE_SYSTEM = f"You are a code reviewer at {WORKDIR}. Be concise — 3-5 bullet points max."

REVIEW_SYSTEMS = {
    "bugs":    BASE_SYSTEM + " Focus on logic errors, edge cases, and correctness.",
    "style":   BASE_SYSTEM + " Focus on naming, structure, and consistency.",
    "security": BASE_SYSTEM + " Focus on input validation, injections, and unsafe patterns.",
}


def run_review_workflow(code_snippet: str):
    """Demo workflow: 3 parallel reviews -> 1 synthesis."""

    with phase("1. Parallel Reviews"):
        tasks = [
            {"prompt": f"Review this code:\n\n```python\n{code_snippet}\n```",
             "system": REVIEW_SYSTEMS[k], "label": k}
            for k in ["bugs", "style", "security"]
        ]
        reviews = parallel(tasks)

    with phase("2. Synthesis"):
        # Combine all reviews and have one agent produce a unified report
        all_findings = "\n\n".join(
            f"[{r['label']}]\n{r['result']}" for r in reviews if r
        )
        synthesis_prompt = (
            f"Synthesize these code review findings into a single prioritized list.\n"
            f"Group by severity (critical, warning, info).\n\n{all_findings}"
        )
        report = run_agent(synthesis_prompt, "You are a senior engineer synthesizing review feedback.")

    return report


# -- Demo: pipeline workflow --
# Transform items through multiple stages.
def run_transform_pipeline(items: list):
    """Demo pipeline: raw text -> summarize -> extract entities."""
    stages = [
        {
            "name": "summarizer",
            "prompt_fn": lambda item, prev: f"Summarize this in 1-2 sentences:\n{item}",
        },
        {
            "name": "entity_extractor",
            "prompt_fn": lambda item, prev: (
                f"Extract key entities (people, places, concepts) from this summary.\n"
                f"Output as a bullet list.\n\nSummary: {prev}"
            ),
        },
    ]
    return pipeline(items, stages)


# -- Base tools for agent use --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


# -- Agent loop for REPL (let user drive workflows) --
TOOL_HANDLERS = {
    "bash":      lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
]

SYSTEM = (
    f"You are a workflow agent at {WORKDIR}.\n"
    f"Use these workflow commands:\n"
    f"  /review <code>  — Run 3-agent parallel code review\n"
    f"  /pipeline <text> — Run summarize->extract pipeline\n"
    f"  /parallel <n> <prompt> — Spawn {n} agents with slight prompt variations\n"
    f"Normal text is sent to a single agent."
)


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=4000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    print("Workflow demo. Commands: /review /pipeline /parallel")
    print("Or type normally for single-agent chat.\n")

    # Example code snippet for review demo
    sample_code = """
def calculate_discount(price, quantity):
    if quantity > 100:
        discount = 0.5
    elif quantity > 50:
        discount = 0.3
    elif quantity > 10:
        discount = 0.1
    else:
        discount = 0

    total = price * quantity * (1 - discount)
    return total
"""

    while True:
        try:
            query = input("\033[36ms15 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()
        if cmd.startswith("/review"):
            code = query[len("/review"):].strip() or sample_code
            print("Running parallel code review workflow...")
            report = run_review_workflow(code)
            print(f"\n{report}\n")
            continue
        if cmd.startswith("/pipeline"):
            text = query[len("/pipeline"):].strip()
            if not text:
                text = "Python is a versatile programming language created by Guido van Rossum in the Netherlands."
            print("Running transform pipeline...")
            results = run_transform_pipeline([text])
            print(f"\nPipeline output:\n{results[0]}\n")
            continue
        if cmd.startswith("/demo"):
            print("Running full demo with sample code...")
            report = run_review_workflow(sample_code)
            print(f"\nSynthesized Report:\n{report}\n")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
