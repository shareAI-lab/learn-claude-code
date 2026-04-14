#!/usr/bin/env python3
"""
Multi-Agent Pipeline: Start Worktree Agent.

Usage: python3 start.py <task-dir>
Example: python3 start.py .trellis/tasks/01-21-my-task

This script:
1. Creates worktree (if not exists) with dependency install
2. Copies environment files (from worktree.yaml config)
3. Sets .current-task in worktree
4. Starts claude agent in background
5. Registers agent to registry.json

Prerequisites:
    - task.json must exist with 'branch' field
    - agents/dispatch.md must exist (in .claude/, .cursor/, .iflow/, or .opencode/)

Configuration: .trellis/worktree.yaml
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli_adapter import CLIAdapter, get_cli_adapter
from common.git_context import _run_git_command
from common.paths import (
    DIR_WORKFLOW,
    FILE_CURRENT_TASK,
    FILE_TASK_JSON,
    get_repo_root,
)
from common.registry import (
    registry_add_agent,
    registry_get_file,
)
from common.worktree import (
    get_worktree_base_dir,
    get_worktree_config,
    get_worktree_copy_files,
    get_worktree_post_create_hooks,
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
# Constants
# =============================================================================

DEFAULT_PLATFORM = "claude"


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Pipeline: Start Worktree Agent")
    parser.add_argument("task_dir", help="Task directory path")
    parser.add_argument(
        "--platform", "-p",
        choices=["claude", "cursor", "iflow", "opencode", "qoder"],
        default=DEFAULT_PLATFORM,
        help="Platform to use (default: claude)"
    )

    args = parser.parse_args()
    task_dir_arg = args.task_dir
    platform = args.platform

    # Initialize CLI adapter
    adapter = get_cli_adapter(platform)

    project_root = get_repo_root()

    # Normalize paths
    if task_dir_arg.startswith("/"):
        task_dir_relative = task_dir_arg[len(str(project_root)) + 1 :]
        task_dir_abs = Path(task_dir_arg)
    else:
        task_dir_relative = task_dir_arg
        task_dir_abs = project_root / task_dir_arg

    task_json_path = task_dir_abs / FILE_TASK_JSON

    # =============================================================================
    # Validation
    # =============================================================================
    if not task_json_path.is_file():
        log_error(f"task.json not found at {task_json_path}")
        return 1

    dispatch_md = adapter.get_agent_path("dispatch", project_root)
    if not dispatch_md.is_file():
        log_error(f"dispatch.md not found at {dispatch_md}")
        log_info(f"Platform: {platform}")
        return 1

    config_file = get_worktree_config(project_root)
    if not config_file.is_file():
        log_error(f"worktree.yaml not found at {config_file}")
        return 1

    # =============================================================================
    # Read Task Config
    # =============================================================================
    print()
    print(f"{Colors.BLUE}=== Multi-Agent Pipeline: Start ==={Colors.NC}")
    log_info(f"Task: {task_dir_abs}")

    task_data = _read_json_file(task_json_path)
    if not task_data:
        log_error("Failed to read task.json")
        return 1

    branch = task_data.get("branch")
    task_name = task_data.get("name")
    task_status = task_data.get("status")
    worktree_path = task_data.get("worktree_path")

    # Check if task was rejected
    if task_status == "rejected":
        log_error("Task was rejected by Plan Agent")
        rejected_file = task_dir_abs / "REJECTED.md"
        if rejected_file.is_file():
            print()
            print(f"{Colors.YELLOW}Rejection reason:{Colors.NC}")
            print(rejected_file.read_text(encoding="utf-8"))
        print()
        log_info(
            "To retry, delete this directory and run plan.py again with revised requirements"
        )
        return 1

    # Check if prd.md exists (plan completed successfully)
    prd_file = task_dir_abs / "prd.md"
    if not prd_file.is_file():
        log_error("prd.md not found - Plan Agent may not have completed")
        log_info(f"Check plan log: {task_dir_abs}/.plan-log")
        return 1

    if not branch:
        log_error("branch field not set in task.json")
        log_info("Please set branch field first, e.g.:")
        log_info(
            "  jq '.branch = \"task/my-task\"' task.json > tmp && mv tmp task.json"
        )
        return 1

    log_info(f"Branch: {branch}")
    log_info(f"Name: {task_name}")

    # =============================================================================
    # Step 1: Create Worktree (if not exists)
    # =============================================================================
    if not worktree_path or not Path(worktree_path).is_dir():
        log_info("Step 1: Creating worktree...")

        # Record current branch as base_branch (PR target)
        _, base_branch_out, _ = _run_git_command(
            ["branch", "--show-current"], cwd=project_root
        )
        base_branch = base_branch_out.strip()
        log_info(f"Base branch (PR target): {base_branch}")

        # Calculate worktree path
        worktree_base = get_worktree_base_dir(project_root)
        worktree_base.mkdir(parents=True, exist_ok=True)
        worktree_base = worktree_base.resolve()
        worktree_path_obj = worktree_base / branch
        worktree_path = str(worktree_path_obj)

        # Create parent directory
        worktree_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Create branch if not exists
        ret, _, _ = _run_git_command(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=project_root,
        )
        if ret == 0:
            log_info("Branch exists, checking out...")
            ret, _, err = _run_git_command(
                ["worktree", "add", worktree_path, branch], cwd=project_root
            )
        else:
            log_info(f"Creating new branch: {branch}")
            ret, _, err = _run_git_command(
                ["worktree", "add", "-b", branch, worktree_path], cwd=project_root
            )

        if ret != 0:
            log_error(f"Failed to create worktree: {err}")
            return 1

        log_success(f"Worktree created: {worktree_path}")

        # Update task.json with worktree_path and base_branch
        task_data["worktree_path"] = worktree_path
        task_data["base_branch"] = base_branch
        _write_json_file(task_json_path, task_data)

        # ----- Copy environment files -----
        log_info("Copying environment files...")
        copy_list = get_worktree_copy_files(project_root)
        copy_count = 0

        for item in copy_list:
            if not item:
                continue

            source = project_root / item
            target = Path(worktree_path) / item

            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))
                copy_count += 1

        if copy_count > 0:
            log_success(f"Copied {copy_count} file(s)")

        # ----- Copy task directory (may not be committed yet) -----
        log_info("Copying task directory...")
        task_target_dir = Path(worktree_path) / task_dir_relative
        task_target_dir.parent.mkdir(parents=True, exist_ok=True)
        if task_target_dir.exists():
            shutil.rmtree(str(task_target_dir))
        shutil.copytree(str(task_dir_abs), str(task_target_dir))
        log_success("Task directory copied to worktree")

        # ----- Run post_create hooks -----
        log_info("Running post_create hooks...")
        post_create = get_worktree_post_create_hooks(project_root)
        hook_count = 0

        for cmd in post_create:
            if not cmd:
                continue

            log_info(f"  Running: {cmd}")
            ret = subprocess.run(cmd, shell=True, cwd=worktree_path)
            if ret.returncode != 0:
                log_error(f"Hook failed: {cmd}")
                return 1
            hook_count += 1

        if hook_count > 0:
            log_success(f"Ran {hook_count} hook(s)")
    else:
        log_info(f"Step 1: Using existing worktree: {worktree_path}")

    # =============================================================================
    # Step 2: Set .current-task in Worktree
    # =============================================================================
    log_info("Step 2: Setting current task in worktree...")

    worktree_workflow_dir = Path(worktree_path) / DIR_WORKFLOW
    worktree_workflow_dir.mkdir(parents=True, exist_ok=True)

    current_task_file = worktree_workflow_dir / FILE_CURRENT_TASK
    current_task_file.write_text(task_dir_relative, encoding="utf-8")
    log_success(f"Current task set: {task_dir_relative}")

    # =============================================================================
    # Step 3: Prepare and Start Claude Agent
    # =============================================================================
    log_info(f"Step 3: Starting {adapter.cli_name} agent...")

    # Update task status
    task_data["status"] = "in_progress"
    _write_json_file(task_json_path, task_data)

    log_file = Path(worktree_path) / ".agent-log"
    session_id_file = Path(worktree_path) / ".session-id"

    log_file.touch()

    # Generate session ID for resume support (Claude Code only)
    # OpenCode generates its own session ID, we'll extract it from logs later
    if adapter.supports_session_id_on_create:
        session_id = str(uuid.uuid4()).lower()
        session_id_file.write_text(session_id, encoding="utf-8")
        log_info(f"Session ID: {session_id}")
    else:
        session_id = None  # Will be extracted from logs after startup
        log_info("Session ID will be extracted from logs after startup")

    # Get proxy environment variables
    https_proxy = os.environ.get("https_proxy", "")
    http_proxy = os.environ.get("http_proxy", "")
    all_proxy = os.environ.get("all_proxy", "")

    # Start agent in background (cross-platform, no shell script needed)
    env = os.environ.copy()
    env["https_proxy"] = https_proxy
    env["http_proxy"] = http_proxy
    env["all_proxy"] = all_proxy

    # Clear nested-session detection so the new CLI process can start
    # (when this script runs inside a Claude Code session, CLAUDECODE=1 is inherited)
    env.pop("CLAUDECODE", None)

    # Set non-interactive env var based on platform
    env.update(adapter.get_non_interactive_env())

    # Build CLI command using adapter
    # Note: Use explicit prompt to avoid confusion with CI/CD pipelines
    # Also remind the model to follow its agent definition for better cross-model compatibility
    cli_cmd = adapter.build_run_command(
        agent="dispatch",
        prompt="Follow your agent instructions to execute the task workflow. Start by reading .trellis/.current-task to get the task directory, then execute each action in task.json next_action array in order.",
        session_id=session_id if adapter.supports_session_id_on_create else None,
        skip_permissions=True,
        verbose=True,
        json_output=True,
    )

    with log_file.open("w") as log_f:
        # Use shell=False for cross-platform compatibility
        # creationflags for Windows, start_new_session for Unix
        popen_kwargs = {
            "stdout": log_f,
            "stderr": subprocess.STDOUT,
            "cwd": worktree_path,
            "env": env,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(cli_cmd, **popen_kwargs)
    agent_pid = process.pid

    log_success(f"Agent started with PID: {agent_pid}")

    # For OpenCode: extract session ID from logs after startup
    if not adapter.supports_session_id_on_create:
        import time
        log_info("Waiting for session ID from logs...")
        # Wait a bit for the log to have session ID
        for _ in range(10):  # Try for up to 5 seconds
            time.sleep(0.5)
            try:
                log_content = log_file.read_text(encoding="utf-8", errors="replace")
                session_id = adapter.extract_session_id_from_log(log_content)
                if session_id:
                    session_id_file.write_text(session_id, encoding="utf-8")
                    log_success(f"Session ID extracted: {session_id}")
                    break
            except Exception:
                pass
        else:
            log_warn("Could not extract session ID from logs")
            session_id = "unknown"

    # =============================================================================
    # Step 4: Register to Registry (in main repo, not worktree)
    # =============================================================================
    log_info("Step 4: Registering agent to registry...")

    # Generate agent ID
    task_id = task_data.get("id")
    if not task_id:
        task_id = branch.replace("/", "-")

    registry_add_agent(
        task_id, worktree_path, agent_pid, task_dir_relative, project_root, platform
    )

    log_success(f"Agent registered: {task_id}")

    # =============================================================================
    # Summary
    # =============================================================================
    print()
    print(f"{Colors.GREEN}=== Agent Started ==={Colors.NC}")
    print()
    print(f"  ID:        {task_id}")
    print(f"  PID:       {agent_pid}")
    print(f"  Session:   {session_id}")
    print(f"  Worktree:  {worktree_path}")
    print(f"  Task:      {task_dir_relative}")
    print(f"  Log:       {log_file}")
    print(f"  Registry:  {registry_get_file(project_root)}")
    print()
    print(f"{Colors.YELLOW}To monitor:{Colors.NC} tail -f {log_file}")
    print(f"{Colors.YELLOW}To stop:{Colors.NC}    kill {agent_pid}")
    if session_id and session_id != "unknown":
        resume_cmd = adapter.get_resume_command_str(session_id, cwd=worktree_path)
        print(f"{Colors.YELLOW}To resume:{Colors.NC}  {resume_cmd}")
    else:
        print(f"{Colors.YELLOW}To resume:{Colors.NC}  (session ID not available)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
