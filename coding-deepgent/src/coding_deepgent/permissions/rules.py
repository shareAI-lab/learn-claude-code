from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from coding_deepgent.permissions.modes import PermissionBehavior


@dataclass(frozen=True, slots=True)
class PermissionRule:
    """A small explicit allow/deny/ask rule for local tool permission checks."""

    tool_name: str
    behavior: PermissionBehavior
    content: str | None = None
    source: str = "local"

    def matches(self, tool_name: str, args: Mapping[str, object]) -> bool:
        if self.tool_name != tool_name:
            return False
        if self.content is None:
            return True
        haystack = "\n".join(str(value) for value in args.values())
        return self.content in haystack
