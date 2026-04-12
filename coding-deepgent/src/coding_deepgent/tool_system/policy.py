from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from coding_deepgent.filesystem.policy import command_policy, path_policy

from .capabilities import CapabilityRegistry


class ToolPolicyCode(StrEnum):
    ALLOWED = "allowed"
    UNKNOWN_TOOL = "unknown_tool"
    TOOL_DISABLED = "tool_disabled"
    DANGEROUS_COMMAND = "dangerous_command"
    WORKSPACE_ESCAPE = "workspace_escape"


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    code: ToolPolicyCode
    message: str = ""


class ToolPolicy:
    def __init__(self, *, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def evaluate(self, tool_call: Mapping[str, object]) -> ToolPolicyDecision:
        tool_name = str(tool_call.get("name", ""))
        capability = self.registry.get(tool_name)
        if capability is None:
            return ToolPolicyDecision(
                allowed=False,
                code=ToolPolicyCode.UNKNOWN_TOOL,
                message=f"Error: Unknown tool `{tool_name}`",
            )

        if not capability.enabled:
            return ToolPolicyDecision(
                allowed=False,
                code=ToolPolicyCode.TOOL_DISABLED,
                message=f"Error: Tool `{tool_name}` is disabled",
            )

        raw_args = tool_call.get("args", {})
        args = raw_args if isinstance(raw_args, Mapping) else {}

        if tool_name == "bash":
            command_decision = command_policy(str(args.get("command", "")))
            if not command_decision.allowed:
                return ToolPolicyDecision(
                    allowed=False,
                    code=ToolPolicyCode.DANGEROUS_COMMAND,
                    message=command_decision.message,
                )

        path_arg = args.get("path")
        if isinstance(path_arg, str):
            path_decision = path_policy(path_arg)
            if not path_decision.allowed:
                return ToolPolicyDecision(
                    allowed=False,
                    code=ToolPolicyCode.WORKSPACE_ESCAPE,
                    message=path_decision.message,
                )

        return ToolPolicyDecision(allowed=True, code=ToolPolicyCode.ALLOWED)
