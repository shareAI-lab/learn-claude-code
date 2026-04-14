#!/usr/bin/env python3
"""
Worktree utilities for Multi-Agent Pipeline.

Provides:
    get_worktree_config         - Get worktree.yaml path
    get_worktree_base_dir       - Get worktree storage directory
    get_worktree_copy_files     - Get files to copy list
    get_worktree_post_create_hooks - Get post-create hooks
    get_agents_dir              - Get agents registry directory
"""

from __future__ import annotations

from pathlib import Path

from .paths import (
    DIR_WORKFLOW,
    get_repo_root,
    get_workspace_dir,
)


# =============================================================================
# YAML Simple Parser (no dependencies)
# =============================================================================


def _unquote(s: str) -> str:
    """Remove exactly one layer of matching surrounding quotes.

    Unlike str.strip('"'), this only removes the outermost pair,
    preserving any nested quotes inside the value.

    Examples:
        _unquote('"hello"')        -> 'hello'
        _unquote("'hello'")        -> 'hello'
        _unquote('"echo \\'hi\\'"')  -> "echo 'hi'"
        _unquote('hello')          -> 'hello'
        _unquote('"hello\\'')       -> '"hello\\''  (mismatched, unchanged)
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def parse_simple_yaml(content: str) -> dict:
    """Parse simple YAML with nested dict support (no dependencies).

    Supports:
        - key: value (string)
        - key: (followed by list items)
            - item1
            - item2
        - key: (followed by nested dict)
            nested_key: value
            nested_key2:
              - item

    Uses indentation to detect nesting (2+ spaces deeper = child).

    Args:
        content: YAML content string.

    Returns:
        Parsed dict (values can be str, list[str], or dict).
    """
    lines = content.splitlines()
    result: dict = {}
    _parse_yaml_block(lines, 0, 0, result)
    return result


def _parse_yaml_block(
    lines: list[str], start: int, min_indent: int, target: dict
) -> int:
    """Parse a YAML block into target dict, returning next line index."""
    i = start
    current_list: list | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Calculate indentation
        indent = len(line) - len(line.lstrip())

        # If dedented past our block, we're done
        if indent < min_indent:
            break

        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(_unquote(stripped[2:].strip()))
            i += 1
        elif ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = _unquote(value.strip())
            current_list = None

            if value:
                # key: value
                target[key] = value
                i += 1
            else:
                # key: (no value) — peek ahead to determine list vs nested dict
                next_i, next_line = _next_content_line(lines, i + 1)
                if next_i >= len(lines):
                    target[key] = {}
                    i = next_i
                elif next_line.strip().startswith("- "):
                    # It's a list
                    current_list = []
                    target[key] = current_list
                    i += 1
                else:
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > indent:
                        # It's a nested dict
                        nested: dict = {}
                        target[key] = nested
                        i = _parse_yaml_block(lines, i + 1, next_indent, nested)
                    else:
                        # Empty value, same or less indent follows
                        target[key] = {}
                        i += 1
        else:
            i += 1

    return i


def _next_content_line(lines: list[str], start: int) -> tuple[int, str]:
    """Find the next non-empty, non-comment line."""
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return i, lines[i]
        i += 1
    return i, ""


def _yaml_get_value(config_file: Path, key: str) -> str | None:
    """Read simple value from worktree.yaml.

    Args:
        config_file: Path to config file.
        key: Key to read.

    Returns:
        Value string or None.
    """
    try:
        content = config_file.read_text(encoding="utf-8")
        data = parse_simple_yaml(content)
        value = data.get(key)
        if isinstance(value, str):
            return value
    except (OSError, IOError):
        pass
    return None


def _yaml_get_list(config_file: Path, section: str) -> list[str]:
    """Read list from worktree.yaml.

    Args:
        config_file: Path to config file.
        section: Section name.

    Returns:
        List of items.
    """
    try:
        content = config_file.read_text(encoding="utf-8")
        data = parse_simple_yaml(content)
        value = data.get(section)
        if isinstance(value, list):
            return [str(item) for item in value]
    except (OSError, IOError):
        pass
    return []


# =============================================================================
# Worktree Configuration
# =============================================================================

# Worktree config file relative path (relative to repo root)
WORKTREE_CONFIG_PATH = f"{DIR_WORKFLOW}/worktree.yaml"


def get_worktree_config(repo_root: Path | None = None) -> Path:
    """Get worktree.yaml config file path.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Absolute path to config file.
    """
    if repo_root is None:
        repo_root = get_repo_root()
    return repo_root / WORKTREE_CONFIG_PATH


def get_worktree_base_dir(repo_root: Path | None = None) -> Path:
    """Get worktree base directory.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Absolute path to worktree base directory.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    config = get_worktree_config(repo_root)
    worktree_dir = _yaml_get_value(config, "worktree_dir")

    # Default value
    if not worktree_dir:
        worktree_dir = "../worktrees"

    # Handle relative path
    if worktree_dir.startswith("../") or worktree_dir.startswith("./"):
        # Relative to repo_root
        return repo_root / worktree_dir
    else:
        # Absolute path
        return Path(worktree_dir)


def get_worktree_copy_files(repo_root: Path | None = None) -> list[str]:
    """Get files to copy list.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        List of file paths to copy.
    """
    if repo_root is None:
        repo_root = get_repo_root()
    config = get_worktree_config(repo_root)
    return _yaml_get_list(config, "copy")


def get_worktree_post_create_hooks(repo_root: Path | None = None) -> list[str]:
    """Get post_create hooks.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        List of commands to run.
    """
    if repo_root is None:
        repo_root = get_repo_root()
    config = get_worktree_config(repo_root)
    return _yaml_get_list(config, "post_create")


# =============================================================================
# Agents Registry
# =============================================================================

def get_agents_dir(repo_root: Path | None = None) -> Path | None:
    """Get agents directory for current developer.

    Args:
        repo_root: Repository root path. Defaults to auto-detected.

    Returns:
        Absolute path to agents directory, or None if no workspace.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    workspace_dir = get_workspace_dir(repo_root)
    if workspace_dir:
        return workspace_dir / ".agents"
    return None


# =============================================================================
# Main Entry (for testing)
# =============================================================================

if __name__ == "__main__":
    repo = get_repo_root()
    print(f"Repository root: {repo}")
    print(f"Worktree config: {get_worktree_config(repo)}")
    print(f"Worktree base dir: {get_worktree_base_dir(repo)}")
    print(f"Copy files: {get_worktree_copy_files(repo)}")
    print(f"Post create hooks: {get_worktree_post_create_hooks(repo)}")
    print(f"Agents dir: {get_agents_dir(repo)}")
