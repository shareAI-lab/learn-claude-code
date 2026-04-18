#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ralph Loop - SubagentStop Hook for Check Agent Loop Control

Based on the Ralph Wiggum technique for autonomous agent loops.
Uses completion promises to control when the check agent can stop.

Mechanism:
- Intercepts when check subagent tries to stop (SubagentStop event)
- If verify commands configured in worktree.yaml, runs them to verify
- Otherwise, reads check.jsonl to get dynamic completion markers ({reason}_FINISH)
- Blocks stopping until verification passes or all markers found
- Has max iterations as safety limit

State file: .trellis/.ralph-state.json
- Tracks current iteration count per session
- Resets when task changes
"""

# IMPORTANT: Suppress all warnings FIRST
import warnings
warnings.filterwarnings("ignore")

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# IMPORTANT: Force stdout to use UTF-8 on Windows
# This fixes UnicodeEncodeError when outputting non-ASCII characters
if sys.platform == "win32":
    import io as _io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# =============================================================================
# Configuration
# =============================================================================

MAX_ITERATIONS = 5  # Safety limit to prevent infinite loops
STATE_TIMEOUT_MINUTES = 30  # Reset state if older than this
STATE_FILE = ".trellis/.ralph-state.json"
WORKTREE_YAML = ".trellis/worktree.yaml"
DIR_WORKFLOW = ".trellis"
FILE_CURRENT_TASK = ".current-task"

# Only control loop for check agent
TARGET_AGENT = "check"


def find_repo_root(start_path: str) -> str | None:
    """Find git repo root from start_path upwards"""
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """Read current task directory path"""
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def get_verify_commands(repo_root: str) -> list[str]:
    """
    Read verify commands from worktree.yaml.

    Returns list of commands to run, or empty list if not configured.
    Uses simple YAML parsing without external dependencies.
    """
    yaml_path = os.path.join(repo_root, WORKTREE_YAML)
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Simple YAML parsing for verify section
        # Look for "verify:" followed by list items
        lines = content.split("\n")
        in_verify_section = False
        commands = []

        for line in lines:
            stripped = line.strip()

            # Check for section start
            if stripped.startswith("verify:"):
                in_verify_section = True
                continue

            # Check for new section (not indented, ends with :)
            if (
                not line.startswith(" ")
                and not line.startswith("\t")
                and stripped.endswith(":")
                and stripped != ""
            ):
                in_verify_section = False
                continue

            # If in verify section, look for list items
            if in_verify_section:
                # Skip comments and empty lines
                if stripped.startswith("#") or stripped == "":
                    continue
                # Parse list item (- command)
                if stripped.startswith("- "):
                    cmd = stripped[2:].strip()
                    if cmd:
                        commands.append(cmd)

        return commands
    except Exception:
        return []


def run_verify_commands(repo_root: str, commands: list[str]) -> tuple[bool, str]:
    """
    Run verify commands and return (success, message).

    All commands must pass for success.
    """
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_root,
                capture_output=True,
                timeout=120,  # 2 minute timeout per command
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                stdout = result.stdout.decode("utf-8", errors="replace")
                error_output = stderr or stdout
                # Truncate long output
                if len(error_output) > 500:
                    error_output = error_output[:500] + "..."
                return False, f"Command failed: {cmd}\n{error_output}"
        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {cmd}"
        except Exception as e:
            return False, f"Command error: {cmd} - {str(e)}"

    return True, "All verify commands passed"


def get_completion_markers(repo_root: str, task_dir: str) -> list[str]:
    """
    Read check.jsonl and generate completion markers from reasons.

    Each entry's "reason" field becomes {REASON}_FINISH marker.
    Example: {"file": "...", "reason": "TypeCheck"} -> "TYPECHECK_FINISH"
    """
    check_jsonl_path = os.path.join(repo_root, task_dir, "check.jsonl")
    markers = []

    if not os.path.exists(check_jsonl_path):
        # Fallback: if no check.jsonl, use default marker
        return ["ALL_CHECKS_FINISH"]

    try:
        with open(check_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    reason = item.get("reason", "")
                    if reason:
                        # Convert to uppercase and add _FINISH suffix
                        marker = f"{reason.upper().replace(' ', '_')}_FINISH"
                        if marker not in markers:
                            markers.append(marker)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    # If no markers found, use default
    if not markers:
        markers = ["ALL_CHECKS_FINISH"]

    return markers


def load_state(repo_root: str) -> dict:
    """Load Ralph Loop state from file"""
    state_path = os.path.join(repo_root, STATE_FILE)
    if not os.path.exists(state_path):
        return {"task": None, "iteration": 0, "started_at": None}

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"task": None, "iteration": 0, "started_at": None}


def save_state(repo_root: str, state: dict) -> None:
    """Save Ralph Loop state to file"""
    state_path = os.path.join(repo_root, STATE_FILE)
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_completion(agent_output: str, markers: list[str]) -> tuple[bool, list[str]]:
    """
    Check if all completion markers are present in agent output.

    Returns:
        (all_complete, missing_markers)
    """
    missing = []
    for marker in markers:
        if marker not in agent_output:
            missing.append(marker)

    return len(missing) == 0, missing


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # If can't parse input, allow stop
        sys.exit(0)

    # Get event info
    hook_event = input_data.get("hook_event_name", "")

    # Only handle SubagentStop event
    if hook_event != "SubagentStop":
        sys.exit(0)

    # Get subagent info
    subagent_type = input_data.get("subagent_type", "")
    agent_output = input_data.get("agent_output", "")
    original_prompt = input_data.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    # Only control check agent
    if subagent_type != TARGET_AGENT:
        sys.exit(0)

    # Skip Ralph Loop for finish phase (already verified in check phase)
    if "[finish]" in original_prompt.lower():
        sys.exit(0)

    # Find repo root
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # Get current task
    task_dir = get_current_task(repo_root)
    if not task_dir:
        sys.exit(0)

    # Load state
    state = load_state(repo_root)

    # Reset state if task changed or state is too old
    should_reset = False
    if state.get("task") != task_dir:
        should_reset = True
    elif state.get("started_at"):
        try:
            started = datetime.fromisoformat(state["started_at"])
            if (datetime.now() - started).total_seconds() > STATE_TIMEOUT_MINUTES * 60:
                should_reset = True
        except (ValueError, TypeError):
            should_reset = True

    if should_reset:
        state = {
            "task": task_dir,
            "iteration": 0,
            "started_at": datetime.now().isoformat(),
        }

    # Increment iteration
    state["iteration"] = state.get("iteration", 0) + 1
    current_iteration = state["iteration"]

    # Save state
    save_state(repo_root, state)

    # Safety check: max iterations
    if current_iteration >= MAX_ITERATIONS:
        # Allow stop, reset state for next run
        state["iteration"] = 0
        save_state(repo_root, state)
        output = {
            "decision": "allow",
            "reason": f"Max iterations ({MAX_ITERATIONS}) reached. Stopping to prevent infinite loop.",
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

    # Check if verify commands are configured
    verify_commands = get_verify_commands(repo_root)

    if verify_commands:
        # Use programmatic verification
        passed, message = run_verify_commands(repo_root, verify_commands)

        if passed:
            # All verify commands passed, allow stop
            state["iteration"] = 0
            save_state(repo_root, state)
            output = {
                "decision": "allow",
                "reason": "All verify commands passed. Check phase complete.",
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
        else:
            # Verification failed, block stop
            output = {
                "decision": "block",
                "reason": f"Iteration {current_iteration}/{MAX_ITERATIONS}. Verification failed:\n{message}\n\nPlease fix the issues and try again.",
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
    else:
        # No verify commands, fall back to completion markers
        markers = get_completion_markers(repo_root, task_dir)
        all_complete, missing = check_completion(agent_output, markers)

        if all_complete:
            # All checks complete, allow stop
            state["iteration"] = 0
            save_state(repo_root, state)
            output = {
                "decision": "allow",
                "reason": "All completion markers found. Check phase complete.",
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
        else:
            # Missing markers, block stop and continue
            output = {
                "decision": "block",
                "reason": f"""Iteration {current_iteration}/{MAX_ITERATIONS}. Missing completion markers: {", ".join(missing)}.

IMPORTANT: You must ACTUALLY run the checks, not just output the markers.
- Did you run lint? What was the output?
- Did you run typecheck? What was the output?
- Did they actually pass with zero errors?

Only output a marker (e.g., LINT_FINISH) AFTER:
1. You have executed the corresponding command
2. The command completed with zero errors
3. You have shown the command output in your response

Do NOT output markers just to escape the loop. The loop exists to ensure quality.""",
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)


if __name__ == "__main__":
    main()
