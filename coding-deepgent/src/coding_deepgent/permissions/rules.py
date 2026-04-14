from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, cast

from coding_deepgent.permission_specs import PermissionRuleSpec
from coding_deepgent.permissions.modes import PermissionBehavior


@dataclass(frozen=True, slots=True)
class PermissionRule:
    """A small explicit allow/deny/ask rule for local tool permission checks."""

    tool_name: str
    behavior: PermissionBehavior
    content: str | None = None
    match_domain: str | None = None
    match_capability_source: str | None = None
    match_trusted: bool | None = None
    source: str = "local"

    def matches(
        self,
        tool_name: str,
        args: Mapping[str, object],
        *,
        domain: str | None = None,
        capability_source: str | None = None,
        trusted: bool | None = None,
    ) -> bool:
        if self.tool_name != tool_name:
            return False
        if self.match_domain is not None and self.match_domain != domain:
            return False
        if (
            self.match_capability_source is not None
            and self.match_capability_source != capability_source
        ):
            return False
        if self.match_trusted is not None and self.match_trusted != trusted:
            return False
        if self.content is None:
            return True
        haystack = "\n".join(str(value) for value in args.values())
        return self.content in haystack


def expand_rule_specs(
    *,
    allow_rules: Sequence[PermissionRuleSpec] = (),
    ask_rules: Sequence[PermissionRuleSpec] = (),
    deny_rules: Sequence[PermissionRuleSpec] = (),
) -> tuple[PermissionRule, ...]:
    rules: list[PermissionRule] = []
    for behavior, specs in (
        ("allow", allow_rules),
        ("ask", ask_rules),
        ("deny", deny_rules),
    ):
        rules.extend(
            PermissionRule(
                tool_name=spec.tool_name,
                behavior=cast(PermissionBehavior, behavior),
                content=spec.content,
                match_domain=spec.domain,
                match_capability_source=spec.capability_source,
                match_trusted=spec.trusted,
                source=spec.rule_source,
            )
            for spec in specs
        )
    return tuple(rules)
