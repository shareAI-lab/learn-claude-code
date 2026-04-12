from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from coding_deepgent.config import load_settings

OUTPUT_LIMIT = 50_000
DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


@dataclass(frozen=True)
class CommandPolicyDecision:
    allowed: bool
    reason: str
    message: str


@dataclass(frozen=True)
class PathPolicyDecision:
    allowed: bool
    reason: str
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class PatternPolicyDecision:
    allowed: bool
    reason: str
    message: str


def workspace_root(*, workdir: Path | None = None) -> Path:
    return (workdir or load_settings().workdir).resolve()


def command_policy(command: str) -> CommandPolicyDecision:
    if any(item in command for item in DANGEROUS_COMMANDS):
        return CommandPolicyDecision(
            allowed=False,
            reason="dangerous_command",
            message="Error: Dangerous command blocked",
        )
    return CommandPolicyDecision(allowed=True, reason="allowed", message="")


def safe_path(path_str: str, *, workdir: Path | None = None) -> Path:
    root = workspace_root(workdir=workdir)
    path = (root / path_str).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path


def path_policy(path_str: str, *, workdir: Path | None = None) -> PathPolicyDecision:
    try:
        path = safe_path(path_str, workdir=workdir)
    except ValueError as exc:
        return PathPolicyDecision(
            allowed=False,
            reason="workspace_escape",
            message=f"Error: {exc}",
        )
    return PathPolicyDecision(
        allowed=True,
        reason="allowed",
        message="",
        path=path,
    )


def pattern_policy(pattern: str) -> PatternPolicyDecision:
    if pattern.startswith("/"):
        return PatternPolicyDecision(
            allowed=False,
            reason="workspace_escape",
            message="Error: Glob pattern must stay inside the workspace",
        )

    if ".." in PurePosixPath(pattern).parts:
        return PatternPolicyDecision(
            allowed=False,
            reason="workspace_escape",
            message="Error: Glob pattern must stay inside the workspace",
        )

    return PatternPolicyDecision(allowed=True, reason="allowed", message="")
