#!/usr/bin/env python3
# Harness: approval — the harness decides when to trust the model.
"""
s20_approval_policy.py - Approval Policy

The model wants to act. The harness decides if it can.

    Model wants to execute X
           |
           v
    +--------------------+
    |   Approval Check   |
    |                    |
    |  action_type       |
    |  policy            |
    |  details            |
    +--------+-----------+
             |
      +------+------+
      |      |       |
    v  v   v  v   v  v
  APPROVE  ASK  REJECT

    Policy levels:
    FULL_AUTO     — everything runs without asking
    AUTO_EDIT     — file edits auto-run, shell needs approval
    ON_REQUEST    — every action needs approval
    NEVER_AUTO    — nothing auto-runs, always ask

    Tool use log example:
    read_file(config.yaml)   — risk:low  — AUTO  (all policies)
    write_file(main.py)      — risk:med  — AUTO  (FULL_AUTO, AUTO_EDIT)
                              —           — ASK   (ON_REQUEST, NEVER_AUTO)
    bash(ls -la)             — risk:med  — AUTO  (FULL_AUTO)
                              —           — ASK   (AUTO_EDIT, ON_REQUEST, NEVER_AUTO)
    bash(sudo rm -rf /tmp)   — risk:high — ASK   (all policies)

Key insight: "The harness decides when to trust the model."
"""

import json
import os
import subprocess
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
    readline.parse_and_bind('set enable-meta-keybindings on')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# -- Approval policies --
FULL_AUTO = "FULL_AUTO"
AUTO_EDIT = "AUTO_EDIT"
ON_REQUEST = "ON_REQUEST"
NEVER_AUTO = "NEVER_AUTO"

POLICIES = {FULL_AUTO, AUTO_EDIT, ON_REQUEST, NEVER_AUTO}

POLICY_DESC = {
    FULL_AUTO:  "Everything runs without asking",
    AUTO_EDIT:  "File edits auto-run, shell commands need approval",
    ON_REQUEST: "Every action needs approval (default interactive)",
    NEVER_AUTO: "Nothing auto-runs, always ask",
}

DANGEROUS_CMDS = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/", "chmod 777"]

# -- Risk assessment --
def assess_risk(action_type: str, details: dict) -> str:
    if action_type == "read_file":
        return "low"
    if action_type in ("write_file", "edit_file"):
        return "med"
    if action_type == "bash":
        cmd = details.get("command", "")
        if any(d in cmd for d in DANGEROUS_CMDS):
            return "high"
        return "med"
    return "med"

# -- Core approval logic --
def can_auto_approve(action_type: str, policy: str, details: dict) -> bool:
    """Return True if the action can execute without user approval."""
    risk = assess_risk(action_type, details)
    if risk == "high":
        return False  # high-risk never auto-approves, regardless of policy
    if policy in (NEVER_AUTO, ON_REQUEST):
        return False
    if policy == FULL_AUTO:
        return True  # low/med risk auto-approve
    # AUTO_EDIT: file operations auto-run, bash needs approval
    if action_type in ("read_file", "write_file", "edit_file"):
        return True
    return False

# -- Approval stats tracker --
stats = {"auto": 0, "approved": 0, "rejected": 0}

def print_stats():
    total = stats["auto"] + stats["approved"] + stats["rejected"]
    print(f"=== Approval Stats ===")
    print(f"  Auto-approved: {stats['auto']}")
    print(f"  User-approved: {stats['approved']}")
    print(f"  User-rejected: {stats['rejected']}")
    print(f"  Total actions: {total}")

# -- Base tool handlers --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    if any(d in command for d in DANGEROUS_CMDS):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

def run_read(path: str) -> str:
    try:
        return safe_path(path).read_text()[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        safe_path(path).write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"]),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
]

# -- Agent loop with approval gate --
def agent_loop(messages: list, policy: str):
    system = f"You are a coding agent at {WORKDIR}. Use bash, read_file, write_file to solve tasks."
    while True:
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=TOOLS, max_tokens=4000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            risk = assess_risk(block.name, block.input)
            approved = can_auto_approve(block.name, policy, block.input)
            detail_str = json.dumps(block.input)
            if len(detail_str) > 50:
                detail_str = detail_str[:47] + "..."

            if approved:
                stats["auto"] += 1
                print(f"  \033[32m[AUTO]\033[0m {block.name}({detail_str}) risk:{risk} — executing")
            else:
                print(f"  \033[33m[ASK ]\033[0m {block.name}({detail_str}) risk:{risk} — approve? (y/n)")
                try:
                    answer = input("  > ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = "n"
                if answer == "y":
                    stats["approved"] += 1
                    print(f"  \033[32m[OK  ]\033[0m approved")
                else:
                    stats["rejected"] += 1
                    print(f"  \033[31m[SKIP]\033[0m rejected by user")
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": "Action was rejected by the user."})
                    continue

            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            print(f"  → {str(output)[:120]}")
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})

# -- Demo mode --
def demo_policies():
    actions = [
        ("read_file",  {"path": "config.yaml"}),
        ("write_file", {"path": "main.py", "content": "print(1)"}),
        ("bash",       {"command": "ls -la"}),
        ("bash",       {"command": "sudo rm -rf /tmp"}),
    ]
    print("\n=== Approval Policy Demo ===\n")
    for policy in [FULL_AUTO, AUTO_EDIT, ON_REQUEST, NEVER_AUTO]:
        print(f"--- {policy} ({POLICY_DESC[policy]}) ---")
        for action_type, details in actions:
            ok = can_auto_approve(action_type, policy, details)
            status = "\033[32mAUTO\033[0m" if ok else "\033[33m ASK\033[0m"
            d = json.dumps(details)
            if len(d) > 40:
                d = d[:37] + "..."
            risk = assess_risk(action_type, details)
            print(f"  [{status}] {action_type}({d}) risk:{risk}")
        print()

if __name__ == "__main__":
    policy = ON_REQUEST
    history = []

    print(f"Working directory: {WORKDIR}")
    print(f"Policy: {policy} — {POLICY_DESC[policy]}")
    print("Commands: /policy <level>  /approvals  /demo  /reset")
    print()

    while True:
        try:
            query = input("\033[36ms20 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()

        if cmd.startswith("/policy"):
            level = cmd[len("/policy"):].strip().upper()
            if level not in POLICIES:
                print(f"Unknown policy. Available: {', '.join(sorted(POLICIES))}")
            else:
                policy = level
                print(f"Policy set to {policy} — {POLICY_DESC[policy]}")
            print()
            continue

        if cmd == "/approvals":
            print_stats()
            print()
            continue

        if cmd == "/demo":
            demo_policies()
            continue

        if cmd == "/reset":
            stats.update({"auto": 0, "approved": 0, "rejected": 0})
            history.clear()
            print("History and stats reset.")
            print()
            continue

        # Normal interaction — approval-gated agent loop
        history.append({"role": "user", "content": query})
        agent_loop(history, policy)

        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
