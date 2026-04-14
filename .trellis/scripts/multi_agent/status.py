#!/usr/bin/env python3
"""
Multi-Agent Pipeline: Status Monitor.

Usage:
    python3 status.py                     Show summary of all tasks (default)
    python3 status.py -a <assignee>       Filter tasks by assignee
    python3 status.py --list              List all worktrees and agents
    python3 status.py --detail <task>     Detailed task status
    python3 status.py --watch <task>      Watch agent log in real-time
    python3 status.py --log <task>        Show recent log entries
    python3 status.py --registry          Show agent registry
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli_adapter import get_cli_adapter
from common.developer import ensure_developer
from common.paths import (
    FILE_TASK_JSON,
    get_repo_root,
    get_tasks_dir,
)
from common.phase import get_phase_info
from common.task_queue import format_task_stats, get_task_stats
from common.worktree import get_agents_dir

# =============================================================================
# Colors
# =============================================================================


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    DIM = "\033[2m"
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


def is_running(pid: int | str | None) -> bool:
    """Check if PID is running."""
    if not pid:
        return False
    try:
        pid_int = int(pid)
        os.kill(pid_int, 0)
        return True
    except (ProcessLookupError, ValueError, PermissionError, TypeError):
        return False


def status_color(status: str) -> str:
    """Get status color."""
    colors = {
        "completed": Colors.GREEN,
        "in_progress": Colors.BLUE,
        "planning": Colors.YELLOW,
    }
    return colors.get(status, Colors.DIM)


def get_registry_file(repo_root: Path) -> Path | None:
    """Get registry file path."""
    agents_dir = get_agents_dir(repo_root)
    if agents_dir:
        return agents_dir / "registry.json"
    return None


def find_agent(search: str, repo_root: Path) -> dict | None:
    """Find agent by task name or ID."""
    registry_file = get_registry_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return None

    data = _read_json_file(registry_file)
    if not data:
        return None

    for agent in data.get("agents", []):
        # Exact ID match
        if agent.get("id") == search:
            return agent
        # Partial match on task_dir
        task_dir = agent.get("task_dir", "")
        if search in task_dir:
            return agent

    return None


def calc_elapsed(started: str | None) -> str:
    """Calculate elapsed time from ISO timestamp."""
    if not started:
        return "N/A"

    try:
        # Parse ISO format
        if "+" in started:
            started = started.split("+")[0]
        if "T" in started:
            start_dt = datetime.fromisoformat(started)
        else:
            return "N/A"

        now = datetime.now()
        elapsed = (now - start_dt).total_seconds()

        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(elapsed // 3600)
            mins = int((elapsed % 3600) // 60)
            return f"{hours}h {mins}m"
    except (ValueError, TypeError):
        return "N/A"


def count_modified_files(worktree: str) -> int:
    """Count modified files in worktree."""
    if not Path(worktree).is_dir():
        return 0

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=worktree,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return len([line for line in result.stdout.splitlines() if line.strip()])
    except Exception:
        return 0


def tail_follow(file_path: Path) -> None:
    """Follow a file like 'tail -f', cross-platform compatible."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Seek to end of file
        f.seek(0, 2)

        while True:
            line = f.readline()
            if line:
                print(line, end="", flush=True)
            else:
                time.sleep(0.1)


def get_last_tool(log_file: Path, platform: str = "claude") -> str | None:
    """Get the last tool call from agent log.

    Supports both Claude Code and OpenCode log formats.

    Claude Code format:
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}}

    OpenCode format:
        {"type": "tool_use", "tool": "bash", "state": {"status": "completed"}}
    """
    if not log_file.is_file():
        return None

    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines[-100:]):
            try:
                data = json.loads(line)

                if platform == "opencode":
                    # OpenCode format: {"type": "tool_use", "tool": "bash", ...}
                    if data.get("type") == "tool_use":
                        return data.get("tool")
                else:
                    # Claude Code format: {"type": "assistant", "message": {"content": [...]}}
                    if data.get("type") == "assistant":
                        content = data.get("message", {}).get("content", [])
                        for item in content:
                            if item.get("type") == "tool_use":
                                return item.get("name")
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return None


def get_last_message(log_file: Path, max_len: int = 100, platform: str = "claude") -> str | None:
    """Get the last assistant text from agent log.

    Supports both Claude Code and OpenCode log formats.

    Claude Code format:
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}

    OpenCode format:
        {"type": "text", "text": "..."}
    """
    if not log_file.is_file():
        return None

    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines[-100:]):
            try:
                data = json.loads(line)

                if platform == "opencode":
                    # OpenCode format: {"type": "text", "text": "..."}
                    if data.get("type") == "text":
                        text = data.get("text", "")
                        if text:
                            return text[:max_len]
                else:
                    # Claude Code format: {"type": "assistant", "message": {"content": [...]}}
                    if data.get("type") == "assistant":
                        content = data.get("message", {}).get("content", [])
                        for item in content:
                            if item.get("type") == "text":
                                text = item.get("text", "")
                                if text:
                                    return text[:max_len]
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return None


# =============================================================================
# Commands
# =============================================================================


def cmd_help() -> int:
    """Show help."""
    print("""Multi-Agent Pipeline: Status Monitor

Usage:
  python3 status.py                         Show summary of all tasks
  python3 status.py -a <assignee>           Filter tasks by assignee
  python3 status.py --list                  List all worktrees and agents
  python3 status.py --detail <task>         Detailed task status
  python3 status.py --progress <task>       Quick progress view with recent activity
  python3 status.py --watch <task>          Watch agent log in real-time
  python3 status.py --log <task>            Show recent log entries
  python3 status.py --registry              Show agent registry

Examples:
  python3 status.py -a taosu
  python3 status.py --detail my-task
  python3 status.py --progress my-task
  python3 status.py --watch 01-16-worktree-support
  python3 status.py --log worktree-support
""")
    return 0


def cmd_list(repo_root: Path) -> int:
    """List worktrees and agents."""
    print(f"{Colors.BLUE}=== Git Worktrees ==={Colors.NC}")
    print()

    subprocess.run(["git", "worktree", "list"], cwd=repo_root)
    print()

    print(f"{Colors.BLUE}=== Registered Agents ==={Colors.NC}")
    print()

    registry_file = get_registry_file(repo_root)
    if not registry_file or not registry_file.is_file():
        print("  (no registry found)")
        return 0

    data = _read_json_file(registry_file)
    if not data or not data.get("agents"):
        print("  (no agents registered)")
        return 0

    for agent in data["agents"]:
        agent_id = agent.get("id", "?")
        pid = agent.get("pid")
        wt = agent.get("worktree_path", "?")
        started = agent.get("started_at", "?")

        if is_running(pid):
            status_icon = f"{Colors.GREEN}●{Colors.NC}"
        else:
            status_icon = f"{Colors.RED}○{Colors.NC}"

        print(f"  {status_icon} {agent_id} (PID: {pid})")
        print(f"    {Colors.DIM}Worktree: {wt}{Colors.NC}")
        print(f"    {Colors.DIM}Started:  {started}{Colors.NC}")
        print()

    return 0


def cmd_summary(repo_root: Path, filter_assignee: str | None = None) -> int:
    """Show summary of all tasks."""
    ensure_developer(repo_root)

    tasks_dir = get_tasks_dir(repo_root)
    if not tasks_dir.is_dir():
        print("No tasks directory found")
        return 0

    registry_file = get_registry_file(repo_root)

    # Count running agents
    running_count = 0
    total_agents = 0

    if registry_file and registry_file.is_file():
        data = _read_json_file(registry_file)
        if data:
            agents = data.get("agents", [])
            total_agents = len(agents)
            for agent in agents:
                if is_running(agent.get("pid")):
                    running_count += 1

    # Task queue stats
    task_stats = get_task_stats(repo_root)

    print(f"{Colors.BLUE}=== Multi-Agent Status ==={Colors.NC}")
    print(
        f"  Agents:  {Colors.GREEN}{running_count}{Colors.NC} running / {total_agents} registered"
    )
    print(f"  Tasks:   {format_task_stats(task_stats)}")
    print()

    # Process tasks
    running_tasks = []
    stopped_tasks = []
    regular_tasks = []

    registry_data = (
        _read_json_file(registry_file)
        if registry_file and registry_file.is_file()
        else None
    )

    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue

        name = d.name
        task_json = d / FILE_TASK_JSON
        status = "unknown"
        assignee = "unassigned"
        priority = "P2"

        if task_json.is_file():
            data = _read_json_file(task_json)
            if data:
                status = data.get("status", "unknown")
                assignee = data.get("assignee", "unassigned")
                priority = data.get("priority", "P2")

        # Filter by assignee
        if filter_assignee and assignee != filter_assignee:
            continue

        # Check agent status
        agent_info = None
        if registry_data:
            for agent in registry_data.get("agents", []):
                if name in agent.get("task_dir", ""):
                    agent_info = agent
                    break

        if agent_info:
            pid = agent_info.get("pid")
            worktree = agent_info.get("worktree_path", "")
            started = agent_info.get("started_at")
            agent_platform = agent_info.get("platform", "claude")

            if is_running(pid):
                # Running agent
                task_dir_rel = agent_info.get("task_dir", "")
                worktree_task_json = Path(worktree) / task_dir_rel / "task.json"
                phase_source = task_json
                if worktree_task_json.is_file():
                    phase_source = worktree_task_json

                phase_info_str = get_phase_info(phase_source)
                elapsed = calc_elapsed(started)
                modified = count_modified_files(worktree)

                worktree_data = _read_json_file(phase_source)
                branch = worktree_data.get("branch", "N/A") if worktree_data else "N/A"

                log_file = Path(worktree) / ".agent-log"
                last_tool = get_last_tool(log_file, platform=agent_platform)

                running_tasks.append(
                    {
                        "name": name,
                        "priority": priority,
                        "assignee": assignee,
                        "phase_info": phase_info_str,
                        "elapsed": elapsed,
                        "branch": branch,
                        "modified": modified,
                        "last_tool": last_tool,
                        "pid": pid,
                    }
                )
            else:
                # Stopped agent
                task_dir_rel = agent_info.get("task_dir", "")
                worktree_task_json = Path(worktree) / task_dir_rel / "task.json"
                worktree_status = "unknown"

                if worktree_task_json.is_file():
                    wt_data = _read_json_file(worktree_task_json)
                    if wt_data:
                        worktree_status = wt_data.get("status", "unknown")

                session_id_file = Path(worktree) / ".session-id"
                log_file = Path(worktree) / ".agent-log"

                stopped_tasks.append(
                    {
                        "name": name,
                        "worktree": worktree,
                        "status": worktree_status,
                        "session_id_file": session_id_file,
                        "log_file": log_file,
                        "platform": agent_info.get("platform", "claude"),
                    }
                )
        else:
            # Regular task
            regular_tasks.append(
                {
                    "name": name,
                    "status": status,
                    "priority": priority,
                    "assignee": assignee,
                }
            )

    # Output running agents
    if running_tasks:
        print(f"{Colors.CYAN}Running Agents:{Colors.NC}")
        for t in running_tasks:
            priority_color = (
                Colors.RED
                if t["priority"] == "P0"
                else (Colors.YELLOW if t["priority"] == "P1" else Colors.BLUE)
            )
            print(
                f"{Colors.GREEN}▶{Colors.NC} {Colors.CYAN}{t['name']}{Colors.NC} {Colors.GREEN}[running]{Colors.NC} {priority_color}[{t['priority']}]{Colors.NC} @{t['assignee']}"
            )
            print(f"  Phase:    {t['phase_info']}")
            print(f"  Elapsed:  {t['elapsed']}")
            print(f"  Branch:   {Colors.DIM}{t['branch']}{Colors.NC}")
            print(f"  Modified: {t['modified']} file(s)")
            if t["last_tool"]:
                print(f"  Activity: {Colors.YELLOW}{t['last_tool']}{Colors.NC}")
            print(f"  PID:      {Colors.DIM}{t['pid']}{Colors.NC}")
            print()

    # Output stopped agents
    if stopped_tasks:
        print(f"{Colors.RED}Stopped Agents:{Colors.NC}")
        for t in stopped_tasks:
            if t["status"] == "completed":
                print(
                    f"{Colors.GREEN}✓{Colors.NC} {t['name']} {Colors.GREEN}[completed]{Colors.NC}"
                )
            else:
                if t["session_id_file"].is_file():
                    session_id = (
                        t["session_id_file"].read_text(encoding="utf-8").strip()
                    )
                    last_msg = get_last_message(t["log_file"], 150, platform=t.get("platform", "claude"))
                    print(
                        f"{Colors.RED}○{Colors.NC} {t['name']} {Colors.RED}[stopped]{Colors.NC}"
                    )
                    if last_msg:
                        print(f'{Colors.DIM}"{last_msg}"{Colors.NC}')
                    # Use CLI adapter for platform-specific resume command
                    adapter = get_cli_adapter(t.get("platform", "claude"))
                    resume_cmd = adapter.get_resume_command_str(session_id, cwd=t["worktree"])
                    print(f"{Colors.YELLOW}{resume_cmd}{Colors.NC}")
                else:
                    print(
                        f"{Colors.RED}○{Colors.NC} {t['name']} {Colors.RED}[stopped]{Colors.NC} {Colors.DIM}(no session-id){Colors.NC}"
                    )
            print()

    # Separator
    if (running_tasks or stopped_tasks) and regular_tasks:
        print(f"{Colors.DIM}───────────────────────────────────────{Colors.NC}")
        print()

    # Output regular tasks grouped by assignee
    if regular_tasks:
        # Sort by assignee, priority, status
        regular_tasks.sort(
            key=lambda x: (
                x["assignee"],
                {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x["priority"], 2),
                {"in_progress": 0, "planning": 1, "completed": 2}.get(x["status"], 1),
            )
        )

        current_assignee = None
        for t in regular_tasks:
            if t["assignee"] != current_assignee:
                if current_assignee is not None:
                    print()
                print(f"{Colors.CYAN}@{t['assignee']}:{Colors.NC}")
                current_assignee = t["assignee"]

            color = status_color(t["status"])
            priority_color = (
                Colors.RED
                if t["priority"] == "P0"
                else (Colors.YELLOW if t["priority"] == "P1" else Colors.BLUE)
            )
            print(
                f"  {color}●{Colors.NC} {t['name']} ({t['status']}) {priority_color}[{t['priority']}]{Colors.NC}"
            )

    if running_tasks:
        print()
        print(f"{Colors.DIM}─────────────────────────────────────{Colors.NC}")
        print(f"{Colors.DIM}Use --progress <name> for quick activity view{Colors.NC}")
        print(f"{Colors.DIM}Use --detail <name> for more info{Colors.NC}")

    print()
    return 0


def cmd_detail(target: str, repo_root: Path) -> int:
    """Show detailed task status."""
    agent = find_agent(target, repo_root)
    if not agent:
        print(f"Agent not found: {target}")
        return 1

    agent_id = agent.get("id", "?")
    pid = agent.get("pid")
    worktree = agent.get("worktree_path", "?")
    task_dir = agent.get("task_dir", "?")
    started = agent.get("started_at", "?")
    platform = agent.get("platform", "claude")

    # Check for session-id
    session_id = ""
    session_id_file = Path(worktree) / ".session-id"
    if session_id_file.is_file():
        session_id = session_id_file.read_text(encoding="utf-8").strip()

    print(f"{Colors.BLUE}=== Agent Detail: {agent_id} ==={Colors.NC}")
    print()
    print(f"  ID:        {agent_id}")
    print(f"  PID:       {pid}")
    print(f"  Session:   {session_id or 'N/A'}")
    print(f"  Worktree:  {worktree}")
    print(f"  Task Dir:  {task_dir}")
    print(f"  Started:   {started}")
    print()

    # Status
    if is_running(pid):
        print(f"  Status:    {Colors.GREEN}Running{Colors.NC}")
    else:
        print(f"  Status:    {Colors.RED}Stopped{Colors.NC}")
        if session_id:
            print()
            # Use CLI adapter for platform-specific resume command
            adapter = get_cli_adapter(platform)
            resume_cmd = adapter.get_resume_command_str(session_id, cwd=worktree)
            print(f"  {Colors.YELLOW}Resume:{Colors.NC} {resume_cmd}")

    # Task info
    task_json = repo_root / task_dir / "task.json"
    if task_json.is_file():
        print()
        print(f"{Colors.BLUE}=== Task Info ==={Colors.NC}")
        print()
        data = _read_json_file(task_json)
        if data:
            print(f"  Status:      {data.get('status', 'unknown')}")
            print(f"  Branch:      {data.get('branch', 'N/A')}")
            print(f"  Base Branch: {data.get('base_branch', 'N/A')}")

    # Git changes
    if Path(worktree).is_dir():
        print()
        print(f"{Colors.BLUE}=== Git Changes ==={Colors.NC}")
        print()

        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=worktree,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        changes = result.stdout.strip()
        if changes:
            for line in changes.splitlines()[:10]:
                print(f"  {line}")
            total = len(changes.splitlines())
            if total > 10:
                print(f"  ... and {total - 10} more")
        else:
            print("  (no changes)")

    print()
    return 0


def cmd_watch(target: str, repo_root: Path) -> int:
    """Watch agent log in real-time."""
    agent = find_agent(target, repo_root)
    if not agent:
        print(f"Agent not found: {target}")
        return 1

    worktree = agent.get("worktree_path", "")
    log_file = Path(worktree) / ".agent-log"

    if not log_file.is_file():
        print(f"Log file not found: {log_file}")
        return 1

    print(f"{Colors.BLUE}Watching:{Colors.NC} {log_file}")
    print(f"{Colors.DIM}Press Ctrl+C to stop{Colors.NC}")
    print()

    try:
        tail_follow(log_file)
    except KeyboardInterrupt:
        print()  # Clean newline after Ctrl+C
    return 0


def cmd_log(target: str, repo_root: Path) -> int:
    """Show recent log entries."""
    agent = find_agent(target, repo_root)
    if not agent:
        print(f"Agent not found: {target}")
        return 1

    worktree = agent.get("worktree_path", "")
    platform = agent.get("platform", "claude")
    log_file = Path(worktree) / ".agent-log"

    if not log_file.is_file():
        print(f"Log file not found: {log_file}")
        return 1

    print(f"{Colors.BLUE}=== Recent Log: {target} ==={Colors.NC}")
    print(f"{Colors.DIM}Platform: {platform}{Colors.NC}")
    print()

    lines = log_file.read_text(encoding="utf-8").splitlines()
    for line in lines[-50:]:
        try:
            data = json.loads(line)
            msg_type = data.get("type", "")

            if platform == "opencode":
                # OpenCode format
                if msg_type == "text":
                    text = data.get("text", "")
                    if text:
                        display = text[:300]
                        if len(text) > 300:
                            display += "..."
                        print(f"{Colors.BLUE}[TEXT]{Colors.NC} {display}")
                elif msg_type == "tool_use":
                    tool_name = data.get("tool", "unknown")
                    status = data.get("state", {}).get("status", "")
                    print(f"{Colors.YELLOW}[TOOL]{Colors.NC} {tool_name} ({status})")
                elif msg_type == "step_start":
                    print(f"{Colors.CYAN}[STEP]{Colors.NC} Start")
                elif msg_type == "step_finish":
                    reason = data.get("reason", "")
                    print(f"{Colors.CYAN}[STEP]{Colors.NC} Finish ({reason})")
                elif msg_type == "error":
                    error_msg = data.get("message", "")
                    print(f"{Colors.RED}[ERROR]{Colors.NC} {error_msg}")
            else:
                # Claude Code format
                if msg_type == "system":
                    subtype = data.get("subtype", "")
                    print(f"{Colors.CYAN}[SYSTEM]{Colors.NC} {subtype}")
                elif msg_type == "user":
                    content = data.get("message", {}).get("content", "")
                    if content:
                        print(f"{Colors.GREEN}[USER]{Colors.NC} {content[:200]}")
                elif msg_type == "assistant":
                    content = data.get("message", {}).get("content", [])
                    if content:
                        item = content[0]
                        text = item.get("text")
                        tool = item.get("name")
                        if text:
                            display = text[:300]
                            if len(text) > 300:
                                display += "..."
                            print(f"{Colors.BLUE}[ASSISTANT]{Colors.NC} {display}")
                        elif tool:
                            print(f"{Colors.YELLOW}[TOOL]{Colors.NC} {tool}")
                elif msg_type == "result":
                    tool_name = data.get("tool", "unknown")
                    print(f"{Colors.DIM}[RESULT]{Colors.NC} {tool_name} completed")
        except json.JSONDecodeError:
            continue

    return 0


def cmd_registry(repo_root: Path) -> int:
    """Show agent registry."""
    registry_file = get_registry_file(repo_root)

    print(f"{Colors.BLUE}=== Agent Registry ==={Colors.NC}")
    print()
    print(f"File: {registry_file}")
    print()

    if registry_file and registry_file.is_file():
        data = _read_json_file(registry_file)
        if data:
            print(json.dumps(data, indent=2))
    else:
        print("(registry not found)")

    return 0


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-Agent Pipeline: Status Monitor")
    parser.add_argument("-a", "--assignee", help="Filter by assignee")
    parser.add_argument(
        "--list", action="store_true", help="List all worktrees and agents"
    )
    parser.add_argument("--detail", metavar="TASK", help="Detailed task status")
    parser.add_argument("--progress", metavar="TASK", help="Quick progress view")
    parser.add_argument("--watch", metavar="TASK", help="Watch agent log")
    parser.add_argument("--log", metavar="TASK", help="Show recent log entries")
    parser.add_argument("--registry", action="store_true", help="Show agent registry")
    parser.add_argument("target", nargs="?", help="Target task")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.list:
        return cmd_list(repo_root)
    elif args.detail:
        return cmd_detail(args.detail, repo_root)
    elif args.progress:
        return cmd_detail(args.progress, repo_root)  # Similar to detail
    elif args.watch:
        return cmd_watch(args.watch, repo_root)
    elif args.log:
        return cmd_log(args.log, repo_root)
    elif args.registry:
        return cmd_registry(repo_root)
    elif args.target:
        return cmd_detail(args.target, repo_root)
    else:
        return cmd_summary(repo_root, args.assignee)


if __name__ == "__main__":
    sys.exit(main())
