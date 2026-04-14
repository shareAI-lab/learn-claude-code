#!/usr/bin/env python3
"""
Task utility functions.

Provides:
    is_safe_task_path  - Validate task path is safe to operate on
    find_task_by_name  - Find task directory by name
    archive_task_dir   - Archive task to monthly directory
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from .paths import get_repo_root


# =============================================================================
# Path Safety
# =============================================================================

def is_safe_task_path(task_path: str, repo_root: Path | None = None) -> bool:
    """Check if a relative task path is safe to operate on.

    Args:
        task_path: Task path (relative to repo_root).
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        True if safe, False if dangerous.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    # Check empty or null
    if not task_path or task_path == "null":
        print("Error: empty or null task path", file=sys.stderr)
        return False

    # Reject absolute paths
    if task_path.startswith("/"):
        print(f"Error: absolute path not allowed: {task_path}", file=sys.stderr)
        return False

    # Reject ".", "..", paths starting with "./" or "../", or containing ".."
    if task_path in (".", "..") or task_path.startswith("./") or task_path.startswith("../") or ".." in task_path:
        print(f"Error: path traversal not allowed: {task_path}", file=sys.stderr)
        return False

    # Final check: ensure resolved path is not the repo root
    abs_path = repo_root / task_path
    if abs_path.exists():
        try:
            resolved = abs_path.resolve()
            root_resolved = repo_root.resolve()
            if resolved == root_resolved:
                print(f"Error: path resolves to repo root: {task_path}", file=sys.stderr)
                return False
        except (OSError, IOError):
            pass

    return True


# =============================================================================
# Task Lookup
# =============================================================================

def find_task_by_name(task_name: str, tasks_dir: Path) -> Path | None:
    """Find task directory by name (exact or suffix match).

    Args:
        task_name: Task name to find.
        tasks_dir: Tasks directory path.

    Returns:
        Absolute path to task directory, or None if not found.
    """
    if not task_name or not tasks_dir or not tasks_dir.is_dir():
        return None

    # Try exact match first
    exact_match = tasks_dir / task_name
    if exact_match.is_dir():
        return exact_match

    # Try suffix match (e.g., "my-task" matches "01-21-my-task")
    for d in tasks_dir.iterdir():
        if d.is_dir() and d.name.endswith(f"-{task_name}"):
            return d

    return None


# =============================================================================
# Archive Operations
# =============================================================================

def archive_task_dir(task_dir_abs: Path, repo_root: Path | None = None) -> Path | None:
    """Archive a task directory to archive/{YYYY-MM}/.

    Args:
        task_dir_abs: Absolute path to task directory.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Path to archived directory, or None on error.
    """
    if not task_dir_abs.is_dir():
        print(f"Error: task directory not found: {task_dir_abs}", file=sys.stderr)
        return None

    # Get tasks directory (parent of the task)
    tasks_dir = task_dir_abs.parent
    archive_dir = tasks_dir / "archive"
    year_month = datetime.now().strftime("%Y-%m")
    month_dir = archive_dir / year_month

    # Create archive directory
    try:
        month_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError) as e:
        print(f"Error: Failed to create archive directory: {e}", file=sys.stderr)
        return None

    # Move task to archive
    task_name = task_dir_abs.name
    dest = month_dir / task_name

    try:
        shutil.move(str(task_dir_abs), str(dest))
    except (OSError, IOError, shutil.Error) as e:
        print(f"Error: Failed to move task to archive: {e}", file=sys.stderr)
        return None

    return dest


def archive_task_complete(
    task_dir_abs: Path,
    repo_root: Path | None = None
) -> dict[str, str]:
    """Complete archive workflow: archive directory.

    Args:
        task_dir_abs: Absolute path to task directory.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Dict with archive result info.
    """
    if not task_dir_abs.is_dir():
        print(f"Error: task directory not found: {task_dir_abs}", file=sys.stderr)
        return {}

    archive_dest = archive_task_dir(task_dir_abs, repo_root)
    if archive_dest:
        return {"archived_to": str(archive_dest)}

    return {}


# =============================================================================
# Main Entry (for testing)
# =============================================================================

if __name__ == "__main__":
    from .paths import get_tasks_dir

    repo = get_repo_root()
    tasks = get_tasks_dir(repo)

    print(f"Tasks dir: {tasks}")
    print(f"is_safe_task_path('.trellis/tasks/test'): {is_safe_task_path('.trellis/tasks/test', repo)}")
    print(f"is_safe_task_path('../test'): {is_safe_task_path('../test', repo)}")
