#!/usr/bin/env python3
"""
Registry utility functions for multi-agent pipeline.

Provides:
    registry_get_file        - Get registry file path
    registry_get_agent_by_id - Find agent by ID
    registry_get_agent_by_worktree - Find agent by worktree path
    registry_get_task_dir    - Get task dir for a worktree
    registry_remove_by_id    - Remove agent by ID
    registry_remove_by_worktree - Remove agent by worktree path
    registry_add_agent       - Add agent to registry
    registry_search_agent    - Search agent by ID or task_dir
    registry_list_agents     - List all agents
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .paths import get_repo_root
from .worktree import get_agents_dir


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
# Registry File Access
# =============================================================================

def registry_get_file(repo_root: Path | None = None) -> Path | None:
    """Get registry file path.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Path to registry.json, or None if agents dir not found.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    agents_dir = get_agents_dir(repo_root)
    if agents_dir:
        return agents_dir / "registry.json"
    return None


def _ensure_registry(repo_root: Path | None = None) -> Path | None:
    """Ensure registry file exists with valid structure.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Path to registry file, or None if cannot create.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file:
        return None

    agents_dir = registry_file.parent

    try:
        agents_dir.mkdir(parents=True, exist_ok=True)

        if not registry_file.exists():
            _write_json_file(registry_file, {"agents": []})

        return registry_file
    except (OSError, IOError):
        return None


# =============================================================================
# Agent Lookup
# =============================================================================

def registry_get_agent_by_id(
    agent_id: str,
    repo_root: Path | None = None
) -> dict | None:
    """Get agent by ID.

    Args:
        agent_id: Agent ID.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Agent dict, or None if not found.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return None

    data = _read_json_file(registry_file)
    if not data:
        return None

    for agent in data.get("agents", []):
        if agent.get("id") == agent_id:
            return agent

    return None


def registry_get_agent_by_worktree(
    worktree_path: str,
    repo_root: Path | None = None
) -> dict | None:
    """Get agent by worktree path.

    Args:
        worktree_path: Worktree path.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Agent dict, or None if not found.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return None

    data = _read_json_file(registry_file)
    if not data:
        return None

    for agent in data.get("agents", []):
        if agent.get("worktree_path") == worktree_path:
            return agent

    return None


def registry_search_agent(
    search: str,
    repo_root: Path | None = None
) -> dict | None:
    """Search agent by ID or task_dir containing search term.

    Args:
        search: Search term.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        First matching agent dict, or None if not found.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
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


def registry_get_task_dir(
    worktree_path: str,
    repo_root: Path | None = None
) -> str | None:
    """Get task directory for a worktree.

    Args:
        worktree_path: Worktree path.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Task directory path, or None if not found.
    """
    agent = registry_get_agent_by_worktree(worktree_path, repo_root)
    if agent:
        return agent.get("task_dir")
    return None


# =============================================================================
# Agent Modification
# =============================================================================

def registry_remove_by_id(agent_id: str, repo_root: Path | None = None) -> bool:
    """Remove agent by ID.

    Args:
        agent_id: Agent ID.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        True on success.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return True  # Nothing to remove

    data = _read_json_file(registry_file)
    if not data:
        return True

    agents = data.get("agents", [])
    data["agents"] = [a for a in agents if a.get("id") != agent_id]

    return _write_json_file(registry_file, data)


def registry_remove_by_worktree(
    worktree_path: str,
    repo_root: Path | None = None
) -> bool:
    """Remove agent by worktree path.

    Args:
        worktree_path: Worktree path.
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        True on success.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return True  # Nothing to remove

    data = _read_json_file(registry_file)
    if not data:
        return True

    agents = data.get("agents", [])
    data["agents"] = [a for a in agents if a.get("worktree_path") != worktree_path]

    return _write_json_file(registry_file, data)


def registry_add_agent(
    agent_id: str,
    worktree_path: str,
    pid: int,
    task_dir: str,
    repo_root: Path | None = None,
    platform: str = "claude",
) -> bool:
    """Add agent to registry (replaces if same ID exists).

    Args:
        agent_id: Agent ID.
        worktree_path: Worktree path.
        pid: Process ID.
        task_dir: Task directory path.
        repo_root: Repository root path. Defaults to auto-detected.
        platform: Platform used (e.g., 'claude', 'opencode', 'codex', 'kiro', 'antigravity'). Defaults to 'claude'.

    Returns:
        True on success.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = _ensure_registry(repo_root)
    if not registry_file:
        return False

    data = _read_json_file(registry_file)
    if not data:
        data = {"agents": []}

    # Remove existing agent with same ID
    agents = data.get("agents", [])
    agents = [a for a in agents if a.get("id") != agent_id]

    # Create new agent record
    started_at = datetime.now().isoformat()
    new_agent = {
        "id": agent_id,
        "worktree_path": worktree_path,
        "pid": pid,
        "started_at": started_at,
        "task_dir": task_dir,
        "platform": platform,
    }

    agents.append(new_agent)
    data["agents"] = agents

    return _write_json_file(registry_file, data)


def registry_list_agents(repo_root: Path | None = None) -> list[dict]:
    """List all agents.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        List of agent dicts.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    registry_file = registry_get_file(repo_root)
    if not registry_file or not registry_file.is_file():
        return []

    data = _read_json_file(registry_file)
    if not data:
        return []

    return data.get("agents", [])


# =============================================================================
# Main Entry (for testing)
# =============================================================================

if __name__ == "__main__":
    import json as json_mod

    repo = get_repo_root()
    print(f"Repository root: {repo}")
    print(f"Registry file: {registry_get_file(repo)}")
    print()
    print("Agents:")
    agents = registry_list_agents(repo)
    print(json_mod.dumps(agents, indent=2))
