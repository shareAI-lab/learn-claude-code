from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from coding_deepgent.permissions import (
    PermissionCode,
    PermissionManager,
    ToolPermissionSubject,
)

from .capabilities import CapabilityRegistry


class ToolPolicyCode(StrEnum):
    ALLOWED = "allowed"
    UNKNOWN_TOOL = "unknown_tool"
    TOOL_DISABLED = "tool_disabled"
    PERMISSION_REQUIRED = "permission_required"
    PERMISSION_DENIED = "permission_denied"
    DANGEROUS_COMMAND = "dangerous_command"
    WORKSPACE_ESCAPE = "workspace_escape"


_PERMISSION_CODE_MAP = {
    PermissionCode.ALLOWED: ToolPolicyCode.ALLOWED,
    PermissionCode.UNKNOWN_TOOL: ToolPolicyCode.UNKNOWN_TOOL,
    PermissionCode.TOOL_DISABLED: ToolPolicyCode.TOOL_DISABLED,
    PermissionCode.PERMISSION_REQUIRED: ToolPolicyCode.PERMISSION_REQUIRED,
    PermissionCode.RULE_ASK: ToolPolicyCode.PERMISSION_REQUIRED,
    PermissionCode.RULE_DENIED: ToolPolicyCode.PERMISSION_DENIED,
    PermissionCode.PLAN_MODE_DENIED: ToolPolicyCode.PERMISSION_DENIED,
    PermissionCode.DONT_ASK_DENIED: ToolPolicyCode.PERMISSION_DENIED,
    PermissionCode.DANGEROUS_COMMAND: ToolPolicyCode.DANGEROUS_COMMAND,
    PermissionCode.WORKSPACE_ESCAPE: ToolPolicyCode.WORKSPACE_ESCAPE,
    PermissionCode.RULE_ALLOWED: ToolPolicyCode.ALLOWED,
}


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    code: ToolPolicyCode
    message: str = ""
    behavior: str = "allow"


class ToolPolicy:
    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        permission_manager: PermissionManager | None = None,
    ) -> None:
        self.registry = registry
        self.permission_manager = permission_manager or PermissionManager()

    def evaluate(self, tool_call: Mapping[str, object]) -> ToolPolicyDecision:
        tool_name = str(tool_call.get("name", ""))
        capability = self.registry.get(tool_name)
        subject = (
            ToolPermissionSubject(
                name=capability.name,
                read_only=capability.read_only,
                destructive=capability.destructive,
                enabled=capability.enabled,
                domain=capability.domain,
                source=capability.source,
                trusted=capability.trusted,
            )
            if capability is not None
            else None
        )
        decision = self.permission_manager.evaluate(
            tool_call=tool_call, subject=subject
        )
        return ToolPolicyDecision(
            allowed=decision.allowed,
            code=_PERMISSION_CODE_MAP.get(
                decision.code, ToolPolicyCode.PERMISSION_DENIED
            ),
            message=decision.message,
            behavior=decision.behavior,
        )
