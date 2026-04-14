#!/usr/bin/env python3
"""
Multi-Agent Pipeline: Cleanup Worktree.

Usage:
    python3 cleanup.py <branch-name>      Remove specific worktree
    python3 cleanup.py --list             List all worktrees
    python3 cleanup.py --merged           Remove merged worktrees
    python3 cleanup.py --all              Remove all worktrees (with confirmation)

Options:
    -y, --yes                       Skip confirmation prompts
    --keep-branch                   Don't delete the git branch

This script:
1. Archives task directory to archive/{YYYY-MM}/
2. Removes agent from registry
3. Removes git worktree
4. Optionally deletes git branch
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.git_context import _run_git_command
from common.paths import get_repo_root
from common.registry import (
    registry_get_file,
    registry_get_task_dir,
    registry_remove_by_id,
    registry_remove_by_worktree,
    registry_search_agent,
)
from common.task_utils import (
    archive_task_complete,
    is_safe_task_path,
)

# =============================================================================
# Colors
# =============================================================================


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


# =============================================================================
# Helper Functions
# =============================================================================


def confirm(prompt: str, skip_confirm: bool) -> bool:
    """Ask for confirmation."""
    if skip_confirm:
        return True

    if not sys.stdin.isatty():
        log_error("Non-interactive mode detected. Use -y to skip confirmation.")
        return False

    response = input(f"{prompt} [y/N] ")
    return response.lower() in ("y", "yes")


# =============================================================================
# Commands
# =============================================================================


def cmd_list(repo_root: Path) -> int:
    """List worktrees."""
    print(f"{Colors.BLUE}=== Git Worktrees ==={Colors.NC}")
    print()

    subprocess.run(["git", "worktree", "list"], cwd=repo_root)
    print()

    # Show registry info
    registry_file = registry_get_file(repo_root)
    if registry_file and registry_file.is_file():
        print(f"{Colors.BLUE}=== Registered Agents ==={Colors.NC}")
        print()

        import json

        data = json.loads(registry_file.read_text(encoding="utf-8"))
        agents = data.get("agents", [])

        if agents:
            for agent in agents:
                print(
                    f"  {agent.get('id', '?')}: PID={agent.get('pid', '?')} [{agent.get('worktree_path', '?')}]"
                )
        else:
            print("  (none)")
        print()

    return 0


def archive_task(worktree_path: str, repo_root: Path) -> None:
    """Archive task directory."""
    task_dir = registry_get_task_dir(worktree_path, repo_root)

    if not task_dir or not is_safe_task_path(task_dir, repo_root):
        return

    task_dir_abs = repo_root / task_dir
    if not task_dir_abs.is_dir():
        return

    result = archive_task_complete(task_dir_abs, repo_root)
    if "archived_to" in result:
        dest = Path(result["archived_to"])
        log_success(f"Archived task: {dest.name} -> archive/{dest.parent.name}/")


def cleanup_registry_only(search: str, repo_root: Path, skip_confirm: bool) -> int:
    """Cleanup from registry only (no worktree)."""
    agent_info = registry_search_agent(search, repo_root)

    if not agent_info:
        log_error(f"No agent found in registry matching: {search}")
        return 1

    agent_id = agent_info.get("id", "?")
    task_dir = agent_info.get("task_dir", "?")

    print()
    print(f"{Colors.BLUE}=== Cleanup Agent (no worktree) ==={Colors.NC}")
    print(f"  Agent ID:  {agent_id}")
    print(f"  Task Dir:  {task_dir}")
    print()

    if not confirm("Archive task and remove from registry?", skip_confirm):
        log_info("Aborted")
        return 0

    # Archive task directory if exists
    if task_dir and is_safe_task_path(task_dir, repo_root):
        task_dir_abs = repo_root / task_dir
        if task_dir_abs.is_dir():
            result = archive_task_complete(task_dir_abs, repo_root)
            if "archived_to" in result:
                dest = Path(result["archived_to"])
                log_success(
                    f"Archived task: {dest.name} -> archive/{dest.parent.name}/"
                )
    else:
        log_warn("Invalid task_dir in registry, skipping archive")

    # Remove from registry
    registry_remove_by_id(agent_id, repo_root)
    log_success(f"Removed from registry: {agent_id}")

    log_success("Cleanup complete")
    return 0


def cleanup_worktree(
    branch: str, repo_root: Path, skip_confirm: bool, keep_branch: bool
) -> int:
    """Cleanup single worktree."""
    # Find worktree path for branch
    _, worktree_list, _ = _run_git_command(
        ["worktree", "list", "--porcelain"], cwd=repo_root
    )

    worktree_path = None
    current_worktree = None

    for line in worktree_list.splitlines():
        if line.startswith("worktree "):
            current_worktree = line[9:]  # Remove "worktree " prefix
        elif line.startswith("branch refs/heads/"):
            current_branch = line[18:]  # Remove "branch refs/heads/" prefix
            if current_branch == branch:
                worktree_path = current_worktree
                break

    if not worktree_path:
        # No worktree found, try to cleanup from registry only
        log_warn(f"No worktree found for: {branch}")
        log_info("Trying to cleanup from registry...")
        return cleanup_registry_only(branch, repo_root, skip_confirm)

    print()
    print(f"{Colors.BLUE}=== Cleanup Worktree ==={Colors.NC}")
    print(f"  Branch:   {branch}")
    print(f"  Worktree: {worktree_path}")
    print()

    if not confirm("Remove this worktree?", skip_confirm):
        log_info("Aborted")
        return 0

    # 1. Archive task
    archive_task(worktree_path, repo_root)

    # 2. Remove from registry
    registry_remove_by_worktree(worktree_path, repo_root)
    log_info("Removed from registry")

    # 3. Remove worktree
    log_info("Removing worktree...")
    ret, _, _ = _run_git_command(
        ["worktree", "remove", worktree_path, "--force"], cwd=repo_root
    )
    if ret != 0:
        # Try removing directory manually
        try:
            shutil.rmtree(worktree_path)
        except Exception as e:
            log_error(f"Failed to remove worktree: {e}")

    log_success("Worktree removed")

    # 4. Delete branch (optional)
    if not keep_branch:
        log_info("Deleting branch...")
        ret, _, _ = _run_git_command(["branch", "-D", branch], cwd=repo_root)
        if ret != 0:
            log_warn("Could not delete branch (may be checked out elsewhere)")

    log_success(f"Cleanup complete for: {branch}")
    return 0


def cmd_merged(repo_root: Path, skip_confirm: bool, keep_branch: bool) -> int:
    """Cleanup merged worktrees."""
    # Get main branch
    _, head_out, _ = _run_git_command(
        ["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_root
    )
    main_branch = head_out.strip().replace("refs/remotes/origin/", "") or "main"

    print(f"{Colors.BLUE}=== Finding Merged Worktrees ==={Colors.NC}")
    print()

    # Get merged branches
    _, merged_out, _ = _run_git_command(
        ["branch", "--merged", main_branch], cwd=repo_root
    )
    merged_branches = []
    for line in merged_out.splitlines():
        branch = line.strip().lstrip("* ")
        if branch and branch != main_branch:
            merged_branches.append(branch)

    if not merged_branches:
        log_info("No merged branches found")
        return 0

    # Get worktree list
    _, worktree_list, _ = _run_git_command(["worktree", "list"], cwd=repo_root)

    worktree_branches = []
    for branch in merged_branches:
        if f"[{branch}]" in worktree_list:
            worktree_branches.append(branch)
            print(f"  - {branch}")

    if not worktree_branches:
        log_info("No merged worktrees found")
        return 0

    print()
    if not confirm("Remove these merged worktrees?", skip_confirm):
        log_info("Aborted")
        return 0

    for branch in worktree_branches:
        cleanup_worktree(branch, repo_root, True, keep_branch)

    return 0


def cmd_all(repo_root: Path, skip_confirm: bool, keep_branch: bool) -> int:
    """Cleanup all worktrees."""
    print(f"{Colors.BLUE}=== All Worktrees ==={Colors.NC}")
    print()

    # Get worktree list
    _, worktree_list, _ = _run_git_command(
        ["worktree", "list", "--porcelain"], cwd=repo_root
    )

    worktrees = []
    main_worktree = str(repo_root.resolve())

    for line in worktree_list.splitlines():
        if line.startswith("worktree "):
            wt = line[9:]
            if wt != main_worktree:
                worktrees.append(wt)

    if not worktrees:
        log_info("No worktrees to remove")
        return 0

    for wt in worktrees:
        print(f"  - {wt}")

    print()
    print(f"{Colors.RED}WARNING: This will remove ALL worktrees!{Colors.NC}")

    if not confirm("Are you sure?", skip_confirm):
        log_info("Aborted")
        return 0

    # Get branch for each worktree
    for wt in worktrees:
        # Find branch name from worktree list
        _, wt_list, _ = _run_git_command(["worktree", "list"], cwd=repo_root)
        for line in wt_list.splitlines():
            if wt in line:
                # Extract branch from [branch] format
                import re

                match = re.search(r"\[([^\]]+)\]", line)
                if match:
                    branch = match.group(1)
                    cleanup_worktree(branch, repo_root, True, keep_branch)
                break

    return 0


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Pipeline: Cleanup Worktree"
    )
    parser.add_argument("branch", nargs="?", help="Branch name to cleanup")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    parser.add_argument(
        "--keep-branch", action="store_true", help="Don't delete git branch"
    )
    parser.add_argument("--list", action="store_true", help="List all worktrees")
    parser.add_argument("--merged", action="store_true", help="Remove merged worktrees")
    parser.add_argument("--all", action="store_true", help="Remove all worktrees")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.list:
        return cmd_list(repo_root)
    elif args.merged:
        return cmd_merged(repo_root, args.yes, args.keep_branch)
    elif args.all:
        return cmd_all(repo_root, args.yes, args.keep_branch)
    elif args.branch:
        return cleanup_worktree(args.branch, repo_root, args.yes, args.keep_branch)
    else:
        print("""Usage:
  python3 cleanup.py <branch-name>      Remove specific worktree
  python3 cleanup.py --list             List all worktrees
  python3 cleanup.py --merged           Remove merged worktrees
  python3 cleanup.py --all              Remove all worktrees

Options:
  -y, --yes             Skip confirmation
  --keep-branch         Don't delete git branch
""")
        return 1


if __name__ == "__main__":
    sys.exit(main())
