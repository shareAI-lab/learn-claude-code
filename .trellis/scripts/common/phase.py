#!/usr/bin/env python3
"""
Phase Management Utilities.

Centralized phase tracking for multi-agent pipeline.

Provides:
    get_current_phase     - Returns current phase number
    get_total_phases      - Returns total phase count
    get_phase_action      - Returns action name for phase
    get_phase_info        - Returns "N/M (action)" format
    set_phase             - Sets current_phase
    advance_phase         - Advances to next phase
    get_phase_for_action  - Returns phase number for action
    map_subagent_to_action - Map subagent type to action name
    is_phase_completed    - Check if phase is completed
    is_current_action     - Check if at specific action
"""

from __future__ import annotations

import json
from pathlib import Path


def _read_json_file(path: Path) -> dict | None:
    """Read and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_json_file(path: Path, data: dict) -> bool:
    """Write dict to JSON file."""
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except (OSError, IOError):
        return False


# =============================================================================
# Phase Functions
# =============================================================================

def get_current_phase(task_json: Path) -> int:
    """Get current phase number.

    Args:
        task_json: Path to task.json file.

    Returns:
        Current phase number, or 0 if not found.
    """
    data = _read_json_file(task_json)
    if not data:
        return 0
    return data.get("current_phase", 0) or 0


def get_total_phases(task_json: Path) -> int:
    """Get total number of phases.

    Args:
        task_json: Path to task.json file.

    Returns:
        Total phase count, or 0 if not found.
    """
    data = _read_json_file(task_json)
    if not data:
        return 0

    next_action = data.get("next_action", [])
    if isinstance(next_action, list):
        return len(next_action)
    return 0


def get_phase_action(task_json: Path, phase: int) -> str:
    """Get action name for a specific phase.

    Args:
        task_json: Path to task.json file.
        phase: Phase number.

    Returns:
        Action name, or "unknown" if not found.
    """
    data = _read_json_file(task_json)
    if not data:
        return "unknown"

    next_action = data.get("next_action", [])
    if isinstance(next_action, list):
        for item in next_action:
            if isinstance(item, dict) and item.get("phase") == phase:
                return item.get("action", "unknown")
    return "unknown"


def get_phase_info(task_json: Path) -> str:
    """Get formatted phase info: "N/M (action)".

    Args:
        task_json: Path to task.json file.

    Returns:
        Formatted string like "1/4 (implement)".
    """
    data = _read_json_file(task_json)
    if not data:
        return "N/A"

    current_phase = data.get("current_phase", 0) or 0
    total_phases = get_total_phases(task_json)
    action_name = get_phase_action(task_json, current_phase)

    if current_phase == 0 or current_phase is None:
        return f"0/{total_phases} (pending)"
    else:
        return f"{current_phase}/{total_phases} ({action_name})"


def set_phase(task_json: Path, phase: int) -> bool:
    """Set current phase to a specific value.

    Args:
        task_json: Path to task.json file.
        phase: Phase number to set.

    Returns:
        True on success, False on error.
    """
    data = _read_json_file(task_json)
    if not data:
        return False

    data["current_phase"] = phase
    return _write_json_file(task_json, data)


def advance_phase(task_json: Path) -> bool:
    """Advance to next phase.

    Args:
        task_json: Path to task.json file.

    Returns:
        True on success, False on error or at final phase.
    """
    data = _read_json_file(task_json)
    if not data:
        return False

    current = data.get("current_phase", 0) or 0
    total = get_total_phases(task_json)
    next_phase = current + 1

    if next_phase > total:
        return False  # Already at final phase

    data["current_phase"] = next_phase
    return _write_json_file(task_json, data)


def get_phase_for_action(task_json: Path, action: str) -> int:
    """Get phase number for a specific action name.

    Args:
        task_json: Path to task.json file.
        action: Action name.

    Returns:
        Phase number, or 0 if not found.
    """
    data = _read_json_file(task_json)
    if not data:
        return 0

    next_action = data.get("next_action", [])
    if isinstance(next_action, list):
        for item in next_action:
            if isinstance(item, dict) and item.get("action") == action:
                return item.get("phase", 0)
    return 0


def map_subagent_to_action(subagent_type: str) -> str:
    """Map subagent type to action name.

    Used by hooks to determine which action a subagent corresponds to.

    Args:
        subagent_type: Subagent type string.

    Returns:
        Corresponding action name.
    """
    mapping = {
        "implement": "implement",
        "check": "check",
        "debug": "debug",
        "research": "research",
    }
    return mapping.get(subagent_type, subagent_type)


def is_phase_completed(task_json: Path, phase: int) -> bool:
    """Check if a phase is completed (current_phase > phase).

    Args:
        task_json: Path to task.json file.
        phase: Phase number to check.

    Returns:
        True if phase is completed.
    """
    current = get_current_phase(task_json)
    return current > phase


def is_current_action(task_json: Path, action: str) -> bool:
    """Check if we're at a specific action.

    Args:
        task_json: Path to task.json file.
        action: Action name to check.

    Returns:
        True if current phase matches the action.
    """
    current = get_current_phase(task_json)
    action_phase = get_phase_for_action(task_json, action)
    return current == action_phase


# =============================================================================
# Main Entry (for testing)
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        print(f"Task JSON: {path}")
        print(f"Phase info: {get_phase_info(path)}")
        print(f"Current phase: {get_current_phase(path)}")
        print(f"Total phases: {get_total_phases(path)}")
    else:
        print("Usage: python3 phase.py <task.json>")
