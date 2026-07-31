from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    repo_root: Path
    workdir: Path
    skills_dir: Path
    memory_dir: Path
    memory_index: Path
    transcripts_dir: Path
    tool_result_dir: Path
    task_dir: Path
    mailbox_dir: Path
    scheduled_tasks_path: Path
    worktrees_dir: Path
    primary_model: str
    fallback_model: str | None
    default_max_tokens: int = 8_000
    escalated_max_tokens: int = 64_000
    max_continuations: int = 3
    max_transient_retries: int = 10
    max_reactive_compacts: int = 1
    base_delay_ms: int = 500
    max_consecutive_529: int = 3
    context_limit: int = 50_000
    keep_recent: int = 3
    persist_threshold: int = 20_000
    idle_poll_interval: float = 5.0
    idle_timeout: float = 60.0
    permission_poll_interval: float = 0.5
    permission_timeout: float = 300.0

    @classmethod
    def from_env(cls, repo_root: Path) -> "AppConfig":
        root = repo_root.resolve()
        workdir = root
        memory_dir = workdir / ".memory"
        tool_result_dir = workdir / ".task_outputs" / "tool-results"
        return cls(
            repo_root=root,
            workdir=workdir,
            skills_dir=workdir / "skills",
            memory_dir=memory_dir,
            memory_index=memory_dir / "MEMORY.md",
            transcripts_dir=workdir / ".transcripts",
            tool_result_dir=tool_result_dir,
            task_dir=workdir / ".tasks",
            mailbox_dir=workdir / ".mailboxes",
            scheduled_tasks_path=workdir / ".scheduled_tasks.json",
            worktrees_dir=workdir / ".worktrees",
            primary_model=os.environ["MODEL_ID"],
            fallback_model=os.getenv("FALLBACK_MODEL_ID"),
        )
