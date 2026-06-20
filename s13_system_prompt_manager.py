#!/usr/bin/env python3
"""
s13_system_prompt_manager.py - Dynamic Environment-Aware System Prompt Assembly

Demonstrates how to probe the real runtime environment (OS, paths, shell, user,
available tools) and assemble a system prompt that reflects it honestly. The
same script produces a correct prompt on Windows, macOS, and Linux without
modification.

Run:  python s13_system_prompt_manager.py
      python s13_system_prompt_manager.py --json   # emit env dict as JSON
      python s13_system_prompt_manager.py --raw    # print only the prompt

No API key required — this script only assembles and prints the prompt.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


# ── Static prompt fragments ──────────────────────────────────────────────────

IDENTITY = (
    "You are a coding agent. Act, don't explain. "
    "Use tools to solve tasks. Be concise."
)

SAFETY_CONSTRAINTS = (
    "Safety constraints:\n"
    "- Never execute commands that escape the working directory.\n"
    "- Never delete files outside the workspace.\n"
    "- Confirm with the user before running destructive operations.\n"
    "- Treat all paths as relative to the working directory unless absolute."
)


# ── Environment probes ───────────────────────────────────────────────────────

def probe_os() -> dict[str, Any]:
    """Probe operating system and platform information.

    Returns:
        dict with keys: system, release, version, machine, processor,
        python_version, is_windows, is_macos, is_linux
    """
    system = platform.system()
    return {
        "system": system,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "is_windows": system == "Windows",
        "is_macos": system == "Darwin",
        "is_linux": system == "Linux",
    }


def probe_paths() -> dict[str, str]:
    """Probe important filesystem paths.

    Returns:
        dict with keys: cwd, home, temp, python_executable, path_separator
    """
    temp_dir = (
        os.environ.get("TEMP")
        or os.environ.get("TMPDIR")
        or os.environ.get("TMP")
        or "/tmp"
    )
    return {
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
        "temp": str(Path(temp_dir)),
        "python_executable": sys.executable,
        "path_separator": os.sep,
        "path_list_separator": os.pathsep,
    }


def probe_user_shell() -> dict[str, str]:
    """Probe current user and shell information.

    Returns:
        dict with keys: user, shell, hostname, terminal
    """
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"

    shell = (
        os.environ.get("SHELL")
        or os.environ.get("COMSPEC")
        or os.environ.get("shell")
        or "unknown"
    )
    terminal = (
        os.environ.get("TERM")
        or os.environ.get("WT_SESSION")  # Windows Terminal
        or "unknown"
    )

    return {
        "user": user,
        "shell": shell,
        "hostname": platform.node(),
        "terminal": terminal,
    }


def probe_tools() -> dict[str, str]:
    """Probe which common development tools are available on PATH.

    Returns:
        dict mapping tool name -> absolute path (only for tools found)
    """
    candidates = [
        "git", "python", "python3", "py",
        "node", "npm", "pnpm", "yarn",
        "docker", "make", "cmake",
        "curl", "wget",
        "rg", "fd", "jq",
        "code", "vim", "nvim",
    ]
    found: dict[str, str] = {}
    for name in candidates:
        path = shutil.which(name)
        if path:
            found[name] = path
    return found


def probe_project() -> dict[str, Any]:
    """Probe project context: git branch, project files.

    Returns:
        dict with keys: is_git_repo, branch (optional), project_files
    """
    cwd = Path.cwd()
    info: dict[str, Any] = {
        "is_git_repo": (cwd / ".git").exists(),
        "project_files": [],
    }

    if info["is_git_repo"]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    markers = ["README.md", "package.json", "pyproject.toml", "requirements.txt",
               "Cargo.toml", "go.mod", ".env.example"]
    info["project_files"] = [m for m in markers if (cwd / m).exists()]

    return info


def probe_environment() -> dict[str, Any]:
    """Run all probes and return a combined environment dict.

    Returns:
        dict with keys: os, paths, user_shell, tools, project, timestamp
    """
    return {
        "os": probe_os(),
        "paths": probe_paths(),
        "user_shell": probe_user_shell(),
        "tools": probe_tools(),
        "project": probe_project(),
    }


# ── Prompt section formatters ────────────────────────────────────────────────

def format_environment(os_info: dict[str, Any], user_shell: dict[str, str]) -> str:
    """Format the environment section of the system prompt.

    Args:
        os_info: output of probe_os()
        user_shell: output of probe_user_shell()

    Returns:
        Formatted string describing the runtime environment.
    """
    lines = [
        "Environment:",
        f"  OS: {os_info['system']} {os_info['release']} ({os_info['machine']})",
        f"  Python: {os_info['python_version']} ({os_info['python_implementation']})",
        f"  User: {user_shell['user']}@{user_shell['hostname']}",
        f"  Shell: {user_shell['shell']}",
    ]
    if os_info["is_windows"]:
        lines.append("  Platform note: Windows — use backslash paths, "
                     "prefer PowerShell or cmd.exe commands.")
    elif os_info["is_macos"]:
        lines.append("  Platform note: macOS — use Unix commands, "
                     "paths under /Users/.")
    elif os_info["is_linux"]:
        lines.append("  Platform note: Linux — use Unix commands, "
                     "paths under /home/.")
    return "\n".join(lines)


def format_tools(tools: dict[str, str]) -> str:
    """Format the available-tools section of the system prompt.

    Args:
        tools: dict mapping tool name -> path (from probe_tools)

    Returns:
        Formatted string listing available tools.
    """
    if not tools:
        return "Available tools: (none detected on PATH)"
    lines = ["Available tools on PATH:"]
    for name in sorted(tools):
        lines.append(f"  - {name}: {tools[name]}")
    return "\n".join(lines)


def format_workspace(paths: dict[str, str]) -> str:
    """Format the workspace section of the system prompt.

    Args:
        paths: output of probe_paths()

    Returns:
        Formatted string describing workspace paths.
    """
    lines = [
        "Workspace:",
        f"  Working directory: {paths['cwd']}",
        f"  Home directory: {paths['home']}",
        f"  Temp directory: {paths['temp']}",
        f"  Python executable: {paths['python_executable']}",
        f"  Path separator: '{paths['path_separator']}'",
    ]
    return "\n".join(lines)


def format_project(project: dict[str, Any]) -> str:
    """Format the optional project-context section.

    Args:
        project: output of probe_project()

    Returns:
        Formatted string, or empty string if no project context.
    """
    if not project["is_git_repo"] and not project["project_files"]:
        return ""
    lines = ["Project context:"]
    if project["is_git_repo"]:
        branch = project.get("branch", "unknown")
        lines.append(f"  Git repository: yes (branch: {branch})")
    else:
        lines.append("  Git repository: no")
    if project["project_files"]:
        lines.append(f"  Project files: {', '.join(project['project_files'])}")
    return "\n".join(lines)


# ── Prompt assembly with cache ───────────────────────────────────────────────

_last_env_key: str | None = None
_last_prompt: str | None = None


def assemble_system_prompt(env: dict[str, Any]) -> str:
    """Assemble the full system prompt from probed environment data.

    Args:
        env: output of probe_environment()

    Returns:
        The assembled system prompt as a single string.
    """
    sections = [
        IDENTITY,
        format_environment(env["os"], env["user_shell"]),
        format_tools(env["tools"]),
        format_workspace(env["paths"]),
        SAFETY_CONSTRAINTS,
    ]
    project_section = format_project(env["project"])
    if project_section:
        sections.append(project_section)
    return "\n\n".join(sections)


def get_system_prompt(env: dict[str, Any], *, verbose: bool = True) -> str:
    """Cache wrapper — reassemble only when environment changes.

    Uses json.dumps for deterministic serialization. Python's hash() has
    process randomization and fails on nested dicts/lists, so it is not
    suitable for cache keys.

    Args:
        env: output of probe_environment()
        verbose: if True, print cache hit/miss diagnostics to stderr

    Returns:
        The assembled system prompt (cached if env unchanged).
    """
    global _last_env_key, _last_prompt
    key = json.dumps(env, sort_keys=True, ensure_ascii=False, default=str)
    if key == _last_env_key and _last_prompt:
        if verbose:
            print("[cache hit] system prompt unchanged", file=sys.stderr)
        return _last_prompt
    _last_env_key = key
    _last_prompt = assemble_system_prompt(env)
    if verbose:
        loaded = ["identity", "environment", "tools", "workspace", "safety"]
        if format_project(env["project"]):
            loaded.append("project")
        print(f"[assembled] sections: {', '.join(loaded)}", file=sys.stderr)
    return _last_prompt


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    """Entry point — parse args, probe env, print assembled prompt.

    Returns:
        Exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        description="Assemble a system prompt from the real runtime environment."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit the probed environment as JSON instead of the prompt.",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="Print only the prompt, no section labels or diagnostics.",
    )
    parser.add_argument(
        "--show-env", action="store_true",
        help="Print each probed environment fact before the prompt.",
    )
    args = parser.parse_args()

    env = probe_environment()

    if args.json:
        print(json.dumps(env, indent=2, ensure_ascii=False, default=str))
        return 0

    if args.show_env:
        print("=== Probed Environment ===")
        print(f"OS:         {env['os']['system']} {env['os']['release']} "
              f"({env['os']['machine']})")
        print(f"Python:     {env['os']['python_version']} "
              f"({env['os']['python_implementation']})")
        print(f"User:       {env['user_shell']['user']}@{env['user_shell']['hostname']}")
        print(f"Shell:      {env['user_shell']['shell']}")
        print(f"CWD:        {env['paths']['cwd']}")
        print(f"Home:       {env['paths']['home']}")
        print(f"Temp:       {env['paths']['temp']}")
        print(f"Python exe: {env['paths']['python_executable']}")
        print(f"Tools:      {', '.join(sorted(env['tools'])) or '(none)'}")
        if env["project"]["is_git_repo"]:
            print(f"Git branch: {env['project'].get('branch', 'unknown')}")
        print()

    prompt = get_system_prompt(env, verbose=not args.raw)

    if args.raw:
        print(prompt)
    else:
        print("=== Assembled System Prompt ===")
        print()
        print("```")
        print(prompt)
        print("```")
        print()
        print(f"Prompt length: {len(prompt)} characters")

    # Demonstrate cache: second call with same env should hit cache
    if not args.raw and not args.json:
        print()
        print("=== Cache demonstration (second call) ===")
        get_system_prompt(env)

    return 0


if __name__ == "__main__":
    sys.exit(main())
