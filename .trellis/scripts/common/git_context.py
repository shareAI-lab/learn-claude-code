#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git and Session Context utilities.

Provides:
    output_json - Output context in JSON format
    output_text - Output context in text format
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .paths import (
    DIR_SCRIPTS,
    DIR_SPEC,
    DIR_TASKS,
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    FILE_TASK_JSON,
    count_lines,
    get_active_journal_file,
    get_current_task,
    get_developer,
    get_repo_root,
    get_tasks_dir,
)

# =============================================================================
# Helper Functions
# =============================================================================


def _run_git_command(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr).

    Uses UTF-8 encoding with -c i18n.logOutputEncoding=UTF-8 to ensure
    consistent output across all platforms (Windows, macOS, Linux).
    """
    try:
        # Force git to output UTF-8 for consistent cross-platform behavior
        git_args = ["git", "-c", "i18n.logOutputEncoding=UTF-8"] + args
        result = subprocess.run(
            git_args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def _read_json_file(path: Path) -> dict | None:
    """Read and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# =============================================================================
# JSON Output
# =============================================================================


def get_context_json(repo_root: Path | None = None) -> dict:
    """Get context as a dictionary.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Context dictionary.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    tasks_dir = get_tasks_dir(repo_root)
    journal_file = get_active_journal_file(repo_root)

    journal_lines = 0
    journal_relative = ""
    if journal_file and developer:
        journal_lines = count_lines(journal_file)
        journal_relative = (
            f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{journal_file.name}"
        )

    # Git info
    _, branch_out, _ = _run_git_command(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"

    _, status_out, _ = _run_git_command(["status", "--porcelain"], cwd=repo_root)
    git_status_count = len([line for line in status_out.splitlines() if line.strip()])
    is_clean = git_status_count == 0

    # Recent commits
    _, log_out, _ = _run_git_command(["log", "--oneline", "-5"], cwd=repo_root)
    commits = []
    for line in log_out.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                commits.append({"hash": parts[0], "message": parts[1]})
            elif len(parts) == 1:
                commits.append({"hash": parts[0], "message": ""})

    # Tasks
    tasks = []
    if tasks_dir.is_dir():
        for d in tasks_dir.iterdir():
            if d.is_dir() and d.name != "archive":
                task_json_path = d / FILE_TASK_JSON
                if task_json_path.is_file():
                    data = _read_json_file(task_json_path)
                    if data:
                        tasks.append(
                            {
                                "dir": d.name,
                                "name": data.get("name") or data.get("id") or "unknown",
                                "status": data.get("status", "unknown"),
                                "children": data.get("children", []),
                                "parent": data.get("parent"),
                            }
                        )

    return {
        "developer": developer or "",
        "git": {
            "branch": branch,
            "isClean": is_clean,
            "uncommittedChanges": git_status_count,
            "recentCommits": commits,
        },
        "tasks": {
            "active": tasks,
            "directory": f"{DIR_WORKFLOW}/{DIR_TASKS}",
        },
        "journal": {
            "file": journal_relative,
            "lines": journal_lines,
            "nearLimit": journal_lines > 1800,
        },
    }


def output_json(repo_root: Path | None = None) -> None:
    """Output context in JSON format.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.
    """
    context = get_context_json(repo_root)
    print(json.dumps(context, indent=2, ensure_ascii=False))


# =============================================================================
# Text Output
# =============================================================================


def get_context_text(repo_root: Path | None = None) -> str:
    """Get context as formatted text.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Formatted text output.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    lines = []
    lines.append("========================================")
    lines.append("SESSION CONTEXT")
    lines.append("========================================")
    lines.append("")

    developer = get_developer(repo_root)

    # Developer section
    lines.append("## DEVELOPER")
    if not developer:
        lines.append(
            f"ERROR: Not initialized. Run: python3 ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <name>"
        )
        return "\n".join(lines)

    lines.append(f"Name: {developer}")
    lines.append("")

    # Git status
    lines.append("## GIT STATUS")
    _, branch_out, _ = _run_git_command(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"
    lines.append(f"Branch: {branch}")

    _, status_out, _ = _run_git_command(["status", "--porcelain"], cwd=repo_root)
    status_lines = [line for line in status_out.splitlines() if line.strip()]
    status_count = len(status_lines)

    if status_count == 0:
        lines.append("Working directory: Clean")
    else:
        lines.append(f"Working directory: {status_count} uncommitted change(s)")
        lines.append("")
        lines.append("Changes:")
        _, short_out, _ = _run_git_command(["status", "--short"], cwd=repo_root)
        for line in short_out.splitlines()[:10]:
            lines.append(line)
    lines.append("")

    # Recent commits
    lines.append("## RECENT COMMITS")
    _, log_out, _ = _run_git_command(["log", "--oneline", "-5"], cwd=repo_root)
    if log_out.strip():
        for line in log_out.splitlines():
            lines.append(line)
    else:
        lines.append("(no commits)")
    lines.append("")

    # Current task
    lines.append("## CURRENT TASK")
    current_task = get_current_task(repo_root)
    if current_task:
        current_task_dir = repo_root / current_task
        task_json_path = current_task_dir / FILE_TASK_JSON
        lines.append(f"Path: {current_task}")

        if task_json_path.is_file():
            data = _read_json_file(task_json_path)
            if data:
                t_name = data.get("name") or data.get("id") or "unknown"
                t_status = data.get("status", "unknown")
                t_created = data.get("createdAt", "unknown")
                t_desc = data.get("description", "")

                lines.append(f"Name: {t_name}")
                lines.append(f"Status: {t_status}")
                lines.append(f"Created: {t_created}")
                if t_desc:
                    lines.append(f"Description: {t_desc}")

        # Check for prd.md
        prd_file = current_task_dir / "prd.md"
        if prd_file.is_file():
            lines.append("")
            lines.append("[!] This task has prd.md - read it for task details")
    else:
        lines.append("(none)")
    lines.append("")

    # Active tasks
    lines.append("## ACTIVE TASKS")
    tasks_dir = get_tasks_dir(repo_root)
    task_count = 0

    # Collect all task data for hierarchy display
    all_task_data: dict[str, dict] = {}
    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                dir_name = d.name
                t_json = d / FILE_TASK_JSON
                status = "unknown"
                assignee = "-"
                children: list[str] = []
                parent: str | None = None

                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data:
                        status = data.get("status", "unknown")
                        assignee = data.get("assignee", "-")
                        children = data.get("children", [])
                        parent = data.get("parent")

                all_task_data[dir_name] = {
                    "status": status,
                    "assignee": assignee,
                    "children": children,
                    "parent": parent,
                }

    def _children_progress(children_list: list[str]) -> str:
        if not children_list:
            return ""
        done = 0
        for c in children_list:
            if c in all_task_data and all_task_data[c]["status"] in ("completed", "done"):
                done += 1
        return f" [{done}/{len(children_list)} done]"

    def _print_task_tree(name: str, indent: int = 0) -> None:
        nonlocal task_count
        info = all_task_data[name]
        progress = _children_progress(info["children"]) if info["children"] else ""
        prefix = "  " * indent
        lines.append(f"{prefix}- {name}/ ({info['status']}){progress} @{info['assignee']}")
        task_count += 1
        for child in info["children"]:
            if child in all_task_data:
                _print_task_tree(child, indent + 1)

    for dir_name in sorted(all_task_data.keys()):
        if not all_task_data[dir_name]["parent"]:
            _print_task_tree(dir_name)

    if task_count == 0:
        lines.append("(no active tasks)")
    lines.append(f"Total: {task_count} active task(s)")
    lines.append("")

    # My tasks
    lines.append("## MY TASKS (Assigned to me)")
    my_task_count = 0

    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                t_json = d / FILE_TASK_JSON
                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data:
                        assignee = data.get("assignee", "")
                        status = data.get("status", "planning")

                        if assignee == developer and status != "done":
                            title = data.get("title") or data.get("name") or "unknown"
                            priority = data.get("priority", "P2")
                            children_list = data.get("children", [])
                            progress = _children_progress(children_list) if children_list else ""
                            lines.append(f"- [{priority}] {title} ({status}){progress}")
                            my_task_count += 1

    if my_task_count == 0:
        lines.append("(no tasks assigned to you)")
    lines.append("")

    # Journal file
    lines.append("## JOURNAL FILE")
    journal_file = get_active_journal_file(repo_root)
    if journal_file:
        journal_lines = count_lines(journal_file)
        relative = f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{journal_file.name}"
        lines.append(f"Active file: {relative}")
        lines.append(f"Line count: {journal_lines} / 2000")
        if journal_lines > 1800:
            lines.append("[!] WARNING: Approaching 2000 line limit!")
    else:
        lines.append("No journal file found")
    lines.append("")

    # Paths
    lines.append("## PATHS")
    lines.append(f"Workspace: {DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/")
    lines.append(f"Tasks: {DIR_WORKFLOW}/{DIR_TASKS}/")
    lines.append(f"Spec: {DIR_WORKFLOW}/{DIR_SPEC}/")
    lines.append("")

    lines.append("========================================")

    return "\n".join(lines)


def get_context_record_json(repo_root: Path | None = None) -> dict:
    """Get record-mode context as a dictionary.

    Focused on: my active tasks, git status, current task.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    developer = get_developer(repo_root)
    tasks_dir = get_tasks_dir(repo_root)

    # Git info
    _, branch_out, _ = _run_git_command(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"

    _, status_out, _ = _run_git_command(["status", "--porcelain"], cwd=repo_root)
    git_status_count = len([line for line in status_out.splitlines() if line.strip()])

    _, log_out, _ = _run_git_command(["log", "--oneline", "-5"], cwd=repo_root)
    commits = []
    for line in log_out.splitlines():
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                commits.append({"hash": parts[0], "message": parts[1]})

    # My tasks
    my_tasks = []
    all_task_statuses: dict[str, str] = {}
    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                t_json = d / FILE_TASK_JSON
                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data:
                        all_task_statuses[d.name] = data.get("status", "unknown")

    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                t_json = d / FILE_TASK_JSON
                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data and data.get("assignee") == developer:
                        children_list = data.get("children", [])
                        done = sum(1 for c in children_list if all_task_statuses.get(c) in ("completed", "done"))
                        my_tasks.append({
                            "dir": d.name,
                            "title": data.get("title") or data.get("name") or "unknown",
                            "status": data.get("status", "unknown"),
                            "priority": data.get("priority", "P2"),
                            "children": children_list,
                            "childrenDone": done,
                            "parent": data.get("parent"),
                            "meta": data.get("meta", {}),
                        })

    # Current task
    current_task_info = None
    current_task = get_current_task(repo_root)
    if current_task:
        task_json_path = (repo_root / current_task) / FILE_TASK_JSON
        if task_json_path.is_file():
            data = _read_json_file(task_json_path)
            if data:
                current_task_info = {
                    "path": current_task,
                    "name": data.get("name") or data.get("id") or "unknown",
                    "status": data.get("status", "unknown"),
                }

    return {
        "developer": developer or "",
        "git": {
            "branch": branch,
            "isClean": git_status_count == 0,
            "uncommittedChanges": git_status_count,
            "recentCommits": commits,
        },
        "myTasks": my_tasks,
        "currentTask": current_task_info,
    }


def get_context_text_record(repo_root: Path | None = None) -> str:
    """Get context as formatted text for record-session mode.

    Focused output: MY ACTIVE TASKS first (with [!!!] emphasis),
    then GIT STATUS, RECENT COMMITS, CURRENT TASK.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Formatted text output for record-session.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    lines: list[str] = []
    lines.append("========================================")
    lines.append("SESSION CONTEXT (RECORD MODE)")
    lines.append("========================================")
    lines.append("")

    developer = get_developer(repo_root)
    if not developer:
        lines.append(
            f"ERROR: Not initialized. Run: python3 ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <name>"
        )
        return "\n".join(lines)

    # MY ACTIVE TASKS — first and prominent
    lines.append(f"## [!!!] MY ACTIVE TASKS (Assigned to {developer})")
    lines.append("[!] Review whether any should be archived before recording this session.")
    lines.append("")

    tasks_dir = get_tasks_dir(repo_root)
    my_task_count = 0

    # Collect task data for children progress
    all_task_statuses: dict[str, str] = {}
    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                t_json = d / FILE_TASK_JSON
                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data:
                        all_task_statuses[d.name] = data.get("status", "unknown")

    def _record_children_progress(children_list: list[str]) -> str:
        if not children_list:
            return ""
        done = 0
        for c in children_list:
            if all_task_statuses.get(c) in ("completed", "done"):
                done += 1
        return f" [{done}/{len(children_list)} done]"

    if tasks_dir.is_dir():
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                t_json = d / FILE_TASK_JSON
                if t_json.is_file():
                    data = _read_json_file(t_json)
                    if data:
                        assignee = data.get("assignee", "")
                        status = data.get("status", "planning")

                        if assignee == developer:
                            title = data.get("title") or data.get("name") or "unknown"
                            priority = data.get("priority", "P2")
                            children_list = data.get("children", [])
                            progress = _record_children_progress(children_list) if children_list else ""
                            lines.append(f"- [{priority}] {title} ({status}){progress} — {d.name}")
                            my_task_count += 1

    if my_task_count == 0:
        lines.append("(no active tasks assigned to you)")
    lines.append("")

    # GIT STATUS
    lines.append("## GIT STATUS")
    _, branch_out, _ = _run_git_command(["branch", "--show-current"], cwd=repo_root)
    branch = branch_out.strip() or "unknown"
    lines.append(f"Branch: {branch}")

    _, status_out, _ = _run_git_command(["status", "--porcelain"], cwd=repo_root)
    status_lines = [line for line in status_out.splitlines() if line.strip()]
    status_count = len(status_lines)

    if status_count == 0:
        lines.append("Working directory: Clean")
    else:
        lines.append(f"Working directory: {status_count} uncommitted change(s)")
        lines.append("")
        lines.append("Changes:")
        _, short_out, _ = _run_git_command(["status", "--short"], cwd=repo_root)
        for line in short_out.splitlines()[:10]:
            lines.append(line)
    lines.append("")

    # RECENT COMMITS
    lines.append("## RECENT COMMITS")
    _, log_out, _ = _run_git_command(["log", "--oneline", "-5"], cwd=repo_root)
    if log_out.strip():
        for line in log_out.splitlines():
            lines.append(line)
    else:
        lines.append("(no commits)")
    lines.append("")

    # CURRENT TASK
    lines.append("## CURRENT TASK")
    current_task = get_current_task(repo_root)
    if current_task:
        current_task_dir = repo_root / current_task
        task_json_path = current_task_dir / FILE_TASK_JSON
        lines.append(f"Path: {current_task}")

        if task_json_path.is_file():
            data = _read_json_file(task_json_path)
            if data:
                t_name = data.get("name") or data.get("id") or "unknown"
                t_status = data.get("status", "unknown")
                lines.append(f"Name: {t_name}")
                lines.append(f"Status: {t_status}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("========================================")

    return "\n".join(lines)


def output_text(repo_root: Path | None = None) -> None:
    """Output context in text format.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.
    """
    print(get_context_text(repo_root))


# =============================================================================
# Main Entry
# =============================================================================


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Get Session Context for AI Agent")
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in JSON format (works with any --mode)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["default", "record"],
        default="default",
        help="Output mode: default (full context) or record (for record-session)",
    )

    args = parser.parse_args()

    if args.mode == "record":
        if args.json:
            print(json.dumps(get_context_record_json(), indent=2, ensure_ascii=False))
        else:
            print(get_context_text_record())
    else:
        if args.json:
            output_json()
        else:
            output_text()


if __name__ == "__main__":
    main()
