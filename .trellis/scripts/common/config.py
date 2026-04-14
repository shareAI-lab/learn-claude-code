#!/usr/bin/env python3
"""
Trellis configuration reader.

Reads settings from .trellis/config.yaml with sensible defaults.
"""

from __future__ import annotations

from pathlib import Path

from .paths import DIR_WORKFLOW, get_repo_root
from .worktree import parse_simple_yaml


# Defaults
DEFAULT_SESSION_COMMIT_MESSAGE = "chore: record journal"
DEFAULT_MAX_JOURNAL_LINES = 2000

CONFIG_FILE = "config.yaml"


def _get_config_path(repo_root: Path | None = None) -> Path:
    """Get path to config.yaml."""
    root = repo_root or get_repo_root()
    return root / DIR_WORKFLOW / CONFIG_FILE


def _load_config(repo_root: Path | None = None) -> dict:
    """Load and parse config.yaml. Returns empty dict on any error."""
    config_file = _get_config_path(repo_root)
    try:
        content = config_file.read_text(encoding="utf-8")
        return parse_simple_yaml(content)
    except (OSError, IOError):
        return {}


def get_session_commit_message(repo_root: Path | None = None) -> str:
    """Get the commit message for auto-committing session records."""
    config = _load_config(repo_root)
    return config.get("session_commit_message", DEFAULT_SESSION_COMMIT_MESSAGE)


def get_max_journal_lines(repo_root: Path | None = None) -> int:
    """Get the maximum lines per journal file."""
    config = _load_config(repo_root)
    value = config.get("max_journal_lines", DEFAULT_MAX_JOURNAL_LINES)
    try:
        return int(value)
    except (ValueError, TypeError):
        return DEFAULT_MAX_JOURNAL_LINES


def get_hooks(event: str, repo_root: Path | None = None) -> list[str]:
    """Get hook commands for a lifecycle event.

    Args:
        event: Event name (e.g. "after_create", "after_archive").
        repo_root: Repository root path.

    Returns:
        List of shell commands to execute, empty if none configured.
    """
    config = _load_config(repo_root)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return []
    commands = hooks.get(event)
    if isinstance(commands, list):
        return [str(c) for c in commands]
    return []
