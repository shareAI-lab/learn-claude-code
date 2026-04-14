#!/usr/bin/env python3
"""
Multi-Agent Pipeline: Create PR.

Usage:
    python3 create_pr.py [task-dir] [--dry-run]

This script:
1. Stages and commits all changes (excluding workspace/)
2. Pushes to origin
3. Creates a Draft PR using `gh pr create`
4. Updates task.json with status="completed", pr_url, and current_phase

Note: This is the only action that performs git commit, as it's the final
step after all implementation and checks are complete.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.git_context import _run_git_command
from common.paths import (
    DIR_WORKFLOW,
    FILE_TASK_JSON,
    get_current_task,
    get_repo_root,
)
from common.phase import get_phase_for_action

# =============================================================================
# Colors
# =============================================================================


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


# =============================================================================
# Helper Functions
# =============================================================================


def _read_json_file(path: Path) -> dict | None:
    """Read and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_json_file(path: Path, data: dict) -> bool:
    """Write dict to JSON file."""
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except (OSError, IOError):
        return False


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-Agent Pipeline: Create PR")
    parser.add_argument("dir", nargs="?", help="Task directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    args = parser.parse_args()
    repo_root = get_repo_root()

    # =============================================================================
    # Get Task Directory
    # =============================================================================
    target_dir = args.dir
    if not target_dir:
        # Try to get from .current-task
        current_task = get_current_task(repo_root)
        if current_task:
            target_dir = current_task

    if not target_dir:
        print(
            f"{Colors.RED}Error: No task directory specified and no current task set{Colors.NC}"
        )
        print("Usage: python3 create_pr.py [task-dir] [--dry-run]")
        return 1

    # Support relative paths
    if not target_dir.startswith("/"):
        target_dir_path = repo_root / target_dir
    else:
        target_dir_path = Path(target_dir)

    task_json = target_dir_path / FILE_TASK_JSON
    if not task_json.is_file():
        print(f"{Colors.RED}Error: task.json not found at {target_dir_path}{Colors.NC}")
        return 1

    # =============================================================================
    # Main
    # =============================================================================
    print(f"{Colors.BLUE}=== Create PR ==={Colors.NC}")
    if args.dry_run:
        print(
            f"{Colors.YELLOW}[DRY-RUN MODE] No actual changes will be made{Colors.NC}"
        )
    print()

    # Read task config
    task_data = _read_json_file(task_json)
    if not task_data:
        print(f"{Colors.RED}Error: Failed to read task.json{Colors.NC}")
        return 1

    task_name = task_data.get("name", "")
    base_branch = task_data.get("base_branch", "main")
    scope = task_data.get("scope", "core")
    dev_type = task_data.get("dev_type", "feature")

    # Map dev_type to commit prefix
    prefix_map = {
        "feature": "feat",
        "frontend": "feat",
        "backend": "feat",
        "fullstack": "feat",
        "bugfix": "fix",
        "fix": "fix",
        "refactor": "refactor",
        "docs": "docs",
        "test": "test",
    }
    commit_prefix = prefix_map.get(dev_type, "feat")

    print(f"Task: {task_name}")
    print(f"Base branch: {base_branch}")
    print(f"Scope: {scope}")
    print(f"Commit prefix: {commit_prefix}")
    print()

    # Get current branch
    _, branch_out, _ = _run_git_command(["branch", "--show-current"])
    current_branch = branch_out.strip()
    print(f"Current branch: {current_branch}")

    # Check for changes
    print(f"{Colors.YELLOW}Checking for changes...{Colors.NC}")

    # Stage changes
    _run_git_command(["add", "-A"])

    # Exclude workspace and temp files
    _run_git_command(["reset", f"{DIR_WORKFLOW}/workspace/"])
    _run_git_command(["reset", ".agent-log", ".session-id"])

    # Check if there are staged changes
    ret, _, _ = _run_git_command(["diff", "--cached", "--quiet"])
    has_staged_changes = ret != 0

    if not has_staged_changes:
        print(f"{Colors.YELLOW}No staged changes to commit{Colors.NC}")

        # Check for unpushed commits
        ret, log_out, _ = _run_git_command(
            ["log", f"origin/{current_branch}..HEAD", "--oneline"]
        )
        unpushed = len([line for line in log_out.splitlines() if line.strip()])

        if unpushed == 0:
            if args.dry_run:
                _run_git_command(["reset", "HEAD"])
            print(f"{Colors.RED}No changes to create PR{Colors.NC}")
            return 1

        print(f"Found {unpushed} unpushed commit(s)")
    else:
        # Commit changes
        print(f"{Colors.YELLOW}Committing changes...{Colors.NC}")
        commit_msg = f"{commit_prefix}({scope}): {task_name}"

        if args.dry_run:
            print(f"[DRY-RUN] Would commit with message: {commit_msg}")
            print("[DRY-RUN] Staged files:")
            _, staged_out, _ = _run_git_command(["diff", "--cached", "--name-only"])
            for line in staged_out.splitlines():
                print(f"  - {line}")
        else:
            _run_git_command(["commit", "-m", commit_msg])
            print(f"{Colors.GREEN}Committed: {commit_msg}{Colors.NC}")

    # Push to remote
    print(f"{Colors.YELLOW}Pushing to remote...{Colors.NC}")
    if args.dry_run:
        print(f"[DRY-RUN] Would push to: origin/{current_branch}")
    else:
        ret, _, err = _run_git_command(["push", "-u", "origin", current_branch])
        if ret != 0:
            print(f"{Colors.RED}Failed to push: {err}{Colors.NC}")
            return 1
        print(f"{Colors.GREEN}Pushed to origin/{current_branch}{Colors.NC}")

    # Create PR
    print(f"{Colors.YELLOW}Creating PR...{Colors.NC}")
    pr_title = f"{commit_prefix}({scope}): {task_name}"
    pr_url = ""

    if args.dry_run:
        print("[DRY-RUN] Would create PR:")
        print(f"  Title: {pr_title}")
        print(f"  Base:  {base_branch}")
        print(f"  Head:  {current_branch}")
        prd_file = target_dir_path / "prd.md"
        if prd_file.is_file():
            print("  Body:  (from prd.md)")
        pr_url = "https://github.com/example/repo/pull/DRY-RUN"
    else:
        # Check if PR already exists
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                current_branch,
                "--base",
                base_branch,
                "--json",
                "url",
                "--jq",
                ".[0].url",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        existing_pr = result.stdout.strip()

        if existing_pr:
            print(f"{Colors.YELLOW}PR already exists: {existing_pr}{Colors.NC}")
            pr_url = existing_pr
        else:
            # Read PRD as PR body
            pr_body = ""
            prd_file = target_dir_path / "prd.md"
            if prd_file.is_file():
                pr_body = prd_file.read_text(encoding="utf-8")

            # Create PR
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--draft",
                    "--base",
                    base_branch,
                    "--title",
                    pr_title,
                    "--body",
                    pr_body,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                print(f"{Colors.RED}Failed to create PR: {result.stderr}{Colors.NC}")
                return 1

            pr_url = result.stdout.strip()
            print(f"{Colors.GREEN}PR created: {pr_url}{Colors.NC}")

    # Update task.json
    print(f"{Colors.YELLOW}Updating task status...{Colors.NC}")
    if args.dry_run:
        print("[DRY-RUN] Would update task.json:")
        print("  status: completed")
        print(f"  pr_url: {pr_url}")
        print("  current_phase: (set to create-pr phase)")
    else:
        # Get the phase number for create-pr action
        create_pr_phase = get_phase_for_action(task_json, "create-pr")
        if not create_pr_phase:
            create_pr_phase = 4  # Default fallback

        task_data["status"] = "completed"
        task_data["pr_url"] = pr_url
        task_data["current_phase"] = create_pr_phase

        _write_json_file(task_json, task_data)
        print(
            f"{Colors.GREEN}Task status updated to 'completed', phase {create_pr_phase}{Colors.NC}"
        )

    # In dry-run, reset the staging area
    if args.dry_run:
        _run_git_command(["reset", "HEAD"])

    print()
    print(f"{Colors.GREEN}=== PR Created Successfully ==={Colors.NC}")
    print(f"PR URL: {pr_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
