from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_deepgent.memory.recall import recall_memories
from coding_deepgent.memory.service import MemoryService
from coding_deepgent.memory.schemas import MemoryRecord
from coding_deepgent.memory.store import MemoryStore

DEPENDENCY_FILES = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
)
DEPENDENCY_COMMAND_HINTS = (
    "npm install",
    "npm add",
    "pnpm add",
    "yarn add",
    "pip install",
    "poetry add",
    "uv add",
)


@dataclass(frozen=True, slots=True)
class FeedbackEnforcementDecision:
    blocked: bool
    message: str = ""
    matched_rule: str | None = None


def evaluate_feedback_enforcement(
    *,
    store: MemoryStore | None,
    service: MemoryService | None = None,
    project_scope: str = "default",
    agent_scope: str | None = None,
    tool_name: str,
    args: Mapping[str, object],
) -> FeedbackEnforcementDecision:
    feedback_memories = recall_memories(
        store,
        service=service,
        project_scope=project_scope,
        agent_scope=agent_scope,
        memory_type="feedback",
        limit=50,
    )
    for record in feedback_memories:
        decision = _evaluate_feedback_record(record, tool_name=tool_name, args=args)
        if decision.blocked:
            return decision
    return FeedbackEnforcementDecision(blocked=False)


def _evaluate_feedback_record(
    record: MemoryRecord,
    *,
    tool_name: str,
    args: Mapping[str, object],
) -> FeedbackEnforcementDecision:
    text = _feedback_text(record)
    command = str(args.get("command", ""))
    path = str(args.get("path", ""))

    if "lint" in text and "commit" in text and tool_name == "bash":
        normalized_command = command.casefold()
        if "git commit" in normalized_command:
            return _blocked(
                record,
                "Feedback requires running lint before commit. Run lint first, then retry the commit.",
            )

    if ("dependency" in text or "package.json" in text) and (
        "confirm" in text or "approval" in text
    ):
        lowered_path = path.casefold()
        lowered_command = command.casefold()
        if tool_name in {"write_file", "edit_file"} and any(
            dependency_file in lowered_path for dependency_file in DEPENDENCY_FILES
        ):
            return _blocked(
                record,
                "Feedback requires confirmation before dependency changes. Stop and confirm before editing dependency files.",
            )
        if tool_name == "bash" and any(
            hint in lowered_command for hint in DEPENDENCY_COMMAND_HINTS
        ):
            return _blocked(
                record,
                "Feedback requires confirmation before dependency changes. Stop and confirm before running dependency install commands.",
            )

    if "generated" in text and (
        "do not modify" in text or "don't modify" in text or "avoid modifying" in text
    ):
        if tool_name in {"write_file", "edit_file"} and "generated" in path.casefold():
            return _blocked(
                record,
                "Feedback forbids modifying generated files. Do not edit generated paths directly.",
            )
    return FeedbackEnforcementDecision(blocked=False)


def _feedback_text(record: MemoryRecord) -> str:
    pieces: Sequence[str | None] = (record.rule, record.why, record.how_to_apply)
    return " ".join(part.casefold() for part in pieces if part)


def _blocked(record: MemoryRecord, message: str) -> FeedbackEnforcementDecision:
    return FeedbackEnforcementDecision(
        blocked=True,
        message=message,
        matched_rule=record.rule,
    )
