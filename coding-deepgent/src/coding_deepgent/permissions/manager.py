from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Sequence, cast

from coding_deepgent.filesystem.policy import command_policy, path_policy
from coding_deepgent.permissions.modes import PermissionBehavior, PermissionMode
from coding_deepgent.permissions.rules import PermissionRule


class PermissionCode(StrEnum):
    ALLOWED = "allowed"
    UNKNOWN_TOOL = "unknown_tool"
    TOOL_DISABLED = "tool_disabled"
    RULE_DENIED = "rule_denied"
    RULE_ASK = "rule_ask"
    RULE_ALLOWED = "rule_allowed"
    PLAN_MODE_DENIED = "plan_mode_denied"
    PERMISSION_REQUIRED = "permission_required"
    DANGEROUS_COMMAND = "dangerous_command"
    WORKSPACE_ESCAPE = "workspace_escape"
    DONT_ASK_DENIED = "dont_ask_denied"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    behavior: PermissionBehavior
    code: PermissionCode
    message: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.behavior == "allow"


@dataclass(frozen=True, slots=True)
class ToolPermissionSubject:
    name: str
    read_only: bool
    destructive: bool
    enabled: bool = True
    domain: str = "unknown"
    source: str = "builtin"
    trusted: bool = True


READ_ONLY_BASH_COMMANDS = frozenset(
    {"ls", "pwd", "cat", "grep", "head", "tail", "find", "rg"}
)


def is_read_only_bash(command: str) -> bool:
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return False
    if not words:
        return False
    if any(token in command for token in ("|", ">", "<", "&&", ";", "$(", "`")):
        return False
    return words[0] in READ_ONLY_BASH_COMMANDS


class PermissionManager:
    def __init__(
        self,
        *,
        mode: PermissionMode = "default",
        rules: Sequence[PermissionRule] = (),
        workdir: Path | None = None,
        trusted_workdirs: Sequence[Path] = (),
    ) -> None:
        self.mode = mode
        self.rules = tuple(rules)
        self.workdir = workdir.expanduser().resolve() if workdir is not None else None
        self.trusted_workdirs = tuple(
            path.expanduser().resolve() for path in trusted_workdirs
        )

    def evaluate(
        self,
        *,
        tool_call: Mapping[str, object],
        subject: ToolPermissionSubject | None,
    ) -> PermissionDecision:
        tool_name = str(tool_call.get("name", ""))
        if subject is None:
            return PermissionDecision(
                behavior="deny",
                code=PermissionCode.UNKNOWN_TOOL,
                message=f"Error: Unknown tool `{tool_name}`",
            )
        if not subject.enabled:
            return PermissionDecision(
                behavior="deny",
                code=PermissionCode.TOOL_DISABLED,
                message=f"Error: Tool `{tool_name}` is disabled",
            )

        raw_args = tool_call.get("args", {})
        args = raw_args if isinstance(raw_args, Mapping) else {}
        hard_safety_decision = self._hard_safety_decision(tool_name, args)
        if hard_safety_decision is not None:
            return hard_safety_decision

        rule_decision = self._rule_decision(tool_name, args, subject=subject)
        if rule_decision is not None:
            return self._apply_dont_ask(rule_decision)

        decision = self._mode_decision(subject, tool_name, args)
        return self._apply_dont_ask(decision)

    def _hard_safety_decision(
        self, tool_name: str, args: Mapping[str, object]
    ) -> PermissionDecision | None:
        if tool_name == "bash":
            decision = command_policy(str(args.get("command", "")))
            if not decision.allowed:
                return PermissionDecision(
                    behavior="deny",
                    code=PermissionCode.DANGEROUS_COMMAND,
                    message=decision.message,
                )

        path_arg = args.get("path")
        if isinstance(path_arg, str):
            if self.workdir is None:
                return PermissionDecision(
                    behavior="deny",
                    code=PermissionCode.WORKSPACE_ESCAPE,
                    message="Error: Path permissions require a configured workdir",
                )
            path_decision = path_policy(
                path_arg,
                workdir=self.workdir,
                additional_workdirs=self.trusted_workdirs,
            )
            if not path_decision.allowed:
                return PermissionDecision(
                    behavior="deny",
                    code=PermissionCode.WORKSPACE_ESCAPE,
                    message=path_decision.message,
                )
        return None

    def _rule_decision(
        self,
        tool_name: str,
        args: Mapping[str, object],
        *,
        subject: ToolPermissionSubject,
    ) -> PermissionDecision | None:
        for behavior, code in (
            ("deny", PermissionCode.RULE_DENIED),
            ("ask", PermissionCode.RULE_ASK),
            ("allow", PermissionCode.RULE_ALLOWED),
        ):
            rule = next(
                (
                    candidate
                    for candidate in self.rules
                    if candidate.behavior == behavior
                    and candidate.matches(
                        tool_name,
                        args,
                        domain=subject.domain,
                        capability_source=subject.source,
                        trusted=subject.trusted,
                    )
                ),
                None,
            )
            if rule is not None:
                return PermissionDecision(
                    behavior=cast(PermissionBehavior, behavior),
                    code=code,
                    message=f"Permission {behavior} rule matched for `{tool_name}`",
                    metadata={"rule_source": rule.source, "rule_content": rule.content},
                )
        return None

    def _mode_decision(
        self,
        subject: ToolPermissionSubject,
        tool_name: str,
        args: Mapping[str, object],
    ) -> PermissionDecision:
        read_only = subject.read_only or (
            tool_name == "bash" and is_read_only_bash(str(args.get("command", "")))
        )
        if not subject.trusted and subject.destructive and not read_only:
            return PermissionDecision(
                "ask",
                PermissionCode.PERMISSION_REQUIRED,
                f"Approval required before running untrusted extension `{tool_name}`",
                metadata={
                    "tool_name": tool_name,
                    "tool_source": subject.source,
                    "trusted": False,
                },
            )
        if self.mode == "bypassPermissions":
            return PermissionDecision("allow", PermissionCode.ALLOWED)

        if self.mode == "acceptEdits":
            return PermissionDecision("allow", PermissionCode.ALLOWED)
        if self.mode == "plan":
            if read_only or not subject.destructive:
                return PermissionDecision("allow", PermissionCode.ALLOWED)
            return PermissionDecision(
                "deny",
                PermissionCode.PLAN_MODE_DENIED,
                f"Error: `{tool_name}` is not allowed in plan mode",
            )

        if read_only or not subject.destructive:
            return PermissionDecision("allow", PermissionCode.ALLOWED)

        return PermissionDecision(
            "ask",
            PermissionCode.PERMISSION_REQUIRED,
            f"Approval required before running `{tool_name}`",
            metadata={"tool_name": tool_name},
        )

    def _apply_dont_ask(self, decision: PermissionDecision) -> PermissionDecision:
        if self.mode == "dontAsk" and decision.behavior == "ask":
            return PermissionDecision(
                "deny",
                PermissionCode.DONT_ASK_DENIED,
                f"Error: `{decision.metadata.get('tool_name', 'tool')}` would require approval, but dontAsk mode denies it"
                if decision.metadata
                else "Error: Approval would be required, but dontAsk mode denies it",
                metadata=decision.metadata,
            )
        return decision
