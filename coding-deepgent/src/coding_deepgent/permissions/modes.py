from __future__ import annotations

from typing import Literal

PermissionMode = Literal[
    "default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"
]
PermissionBehavior = Literal["allow", "ask", "deny"]

EXTERNAL_PERMISSION_MODES: tuple[PermissionMode, ...] = (
    "default",
    "plan",
    "acceptEdits",
    "bypassPermissions",
    "dontAsk",
)
