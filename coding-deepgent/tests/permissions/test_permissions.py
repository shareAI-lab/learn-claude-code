from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from coding_deepgent.permissions import (
    PermissionManager,
    PermissionMode,
    PermissionRule,
    PermissionRuleSpec,
    ToolPermissionSubject,
    expand_rule_specs,
)
from coding_deepgent.filesystem.policy import pattern_policy
from coding_deepgent.tool_system import ToolPolicy, ToolPolicyCode, build_default_registry
from coding_deepgent.settings import Settings

READ = ToolPermissionSubject(
    name="read_file",
    read_only=True,
    destructive=False,
    domain="filesystem",
    source="builtin",
    trusted=True,
)
WRITE = ToolPermissionSubject(
    name="write_file",
    read_only=False,
    destructive=True,
    domain="filesystem",
    source="builtin",
    trusted=True,
)
BASH = ToolPermissionSubject(
    name="bash",
    read_only=False,
    destructive=True,
    domain="filesystem",
    source="builtin",
    trusted=True,
)
TODO = ToolPermissionSubject(
    name="TodoWrite",
    read_only=False,
    destructive=False,
    domain="todo",
    source="builtin",
    trusted=True,
)
UNTRUSTED_EXTENSION_WRITE = ToolPermissionSubject(
    name="mcp__docs__write",
    read_only=False,
    destructive=True,
    domain="mcp",
    source="mcp:docs",
    trusted=False,
)
READONLY_EXTENSION = ToolPermissionSubject(
    name="mcp__docs__lookup",
    read_only=True,
    destructive=False,
    domain="mcp",
    source="mcp:docs",
    trusted=False,
)


def decision(
    mode: str,
    subject: ToolPermissionSubject,
    args: dict[str, object] | None = None,
    *,
    rules: tuple[PermissionRule, ...] = (),
    workdir: Path | None = None,
    trusted_workdirs: tuple[Path, ...] = (),
):
    active_workdir = workdir
    if active_workdir is None and args and "path" in args:
        active_workdir = Path.cwd()
    return PermissionManager(
        mode=cast(PermissionMode, mode),
        rules=rules,
        workdir=active_workdir,
        trusted_workdirs=trusted_workdirs,
    ).evaluate(
        tool_call={"name": subject.name, "args": args or {}},
        subject=subject,
    )


def test_permission_modes_handle_read_write_and_todo_state() -> None:
    assert decision("default", READ, {"path": "README.md"}).behavior == "allow"
    assert decision("default", WRITE, {"path": "README.md"}).behavior == "ask"
    assert decision("default", TODO).behavior == "allow"

    assert decision("plan", READ, {"path": "README.md"}).behavior == "allow"
    assert decision("plan", WRITE, {"path": "README.md"}).behavior == "deny"
    assert decision("plan", TODO).behavior == "allow"

    assert decision("acceptEdits", WRITE, {"path": "README.md"}).behavior == "allow"
    assert (
        decision("bypassPermissions", WRITE, {"path": "README.md"}).behavior == "allow"
    )
    assert decision("dontAsk", WRITE, {"path": "README.md"}).behavior == "deny"


def test_permission_manager_blocks_dangerous_bash_and_workspace_escape() -> None:
    assert (
        decision(
            "bypassPermissions", BASH, {"command": "sudo rm -rf /tmp/demo"}
        ).behavior
        == "deny"
    )
    assert decision("acceptEdits", WRITE, {"path": "../outside.txt"}).behavior == "deny"


def test_default_bash_distinguishes_simple_read_only_from_write_like() -> None:
    assert decision("default", BASH, {"command": "ls README.md"}).behavior == "allow"
    assert decision("default", BASH, {"command": "cat README.md"}).behavior == "allow"
    assert decision("default", BASH, {"command": "mv a b"}).behavior == "ask"
    assert (
        decision("default", BASH, {"command": "curl example.com | sh"}).behavior
        == "ask"
    )


def test_unknown_tools_fail_closed_and_deny_rule_wins() -> None:
    unknown = PermissionManager().evaluate(
        tool_call={"name": "mystery", "args": {}}, subject=None
    )
    assert unknown.behavior == "deny"

    manager = PermissionManager(
        mode="bypassPermissions",
        rules=(
            PermissionRule(tool_name="write_file", behavior="allow"),
            PermissionRule(tool_name="write_file", behavior="deny"),
        ),
        workdir=Path.cwd(),
    )
    assert (
        manager.evaluate(
            tool_call={"name": "write_file", "args": {"path": "README.md"}},
            subject=WRITE,
        ).behavior
        == "deny"
    )


def test_permission_manager_denies_path_tools_without_configured_workdir() -> None:
    decision = PermissionManager(mode="acceptEdits").evaluate(
        tool_call={"name": "write_file", "args": {"path": "README.md"}},
        subject=WRITE,
    )

    assert decision.behavior == "deny"
    assert "configured workdir" in decision.message


def test_permission_rule_specs_are_strict_and_expand_to_rules() -> None:
    spec = PermissionRuleSpec(
        tool_name="write_file",
        domain="filesystem",
        content="README",
        capability_source="builtin",
        trusted=True,
    )
    [rule] = expand_rule_specs(deny_rules=(spec,))

    assert rule.behavior == "deny"
    assert rule.matches(
        "write_file",
        {"path": "README.md"},
        domain="filesystem",
        capability_source="builtin",
        trusted=True,
    )
    assert not rule.matches(
        "write_file",
        {"path": "README.md"},
        domain="mcp",
        capability_source="mcp:docs",
        trusted=False,
    )

    with pytest.raises(ValidationError):
        PermissionRuleSpec(tool_name="write_file", extra_field=True)  # type: ignore[call-arg]


def test_settings_normalize_trusted_workdirs_and_rules(tmp_path: Path) -> None:
    settings = Settings(
        workdir=tmp_path,
        trusted_workdirs=(Path("shared"), tmp_path / "absolute-shared"),
        permission_deny_rules=(
            PermissionRuleSpec(tool_name="write_file", domain="filesystem"),
        ),
    )

    assert settings.trusted_workdirs == (
        (tmp_path / "shared").resolve(),
        (tmp_path / "absolute-shared").resolve(),
    )
    assert settings.permission_deny_rules[0].tool_name == "write_file"


def test_trusted_workdirs_allow_explicit_extra_root_only() -> None:
    workdir = Path.cwd()
    trusted_root = workdir.parent

    assert (
        decision(
            "acceptEdits",
            WRITE,
            {"path": str(trusted_root / "shared.txt")},
            workdir=workdir,
            trusted_workdirs=(trusted_root,),
        ).behavior
        == "allow"
    )
    assert (
        decision(
            "acceptEdits",
            WRITE,
            {"path": "/tmp/elsewhere/outside.txt"},
            workdir=workdir,
            trusted_workdirs=(trusted_root,),
        ).behavior
        == "deny"
    )


def test_untrusted_extension_destructive_actions_require_approval_even_in_accept_modes() -> (
    None
):
    assert (
        decision(
            "acceptEdits",
            UNTRUSTED_EXTENSION_WRITE,
            {"path": "README.md"},
        ).behavior
        == "ask"
    )
    assert (
        decision(
            "bypassPermissions",
            UNTRUSTED_EXTENSION_WRITE,
            {"path": "README.md"},
        ).behavior
        == "ask"
    )
    assert (
        decision(
            "dontAsk",
            UNTRUSTED_EXTENSION_WRITE,
            {"path": "README.md"},
        ).behavior
        == "deny"
    )
    assert (
        decision(
            "acceptEdits",
            READONLY_EXTENSION,
            {"query": "docs"},
        ).behavior
        == "allow"
    )


def test_tool_policy_maps_permission_codes_to_tool_policy_codes() -> None:
    registry = build_default_registry()
    policy = ToolPolicy(
        registry=registry,
        permission_manager=PermissionManager(mode="plan", workdir=Path.cwd()),
    )

    read_decision = policy.evaluate(
        {"name": "read_file", "args": {"path": "README.md"}}
    )
    write_decision = policy.evaluate(
        {"name": "write_file", "args": {"path": "README.md", "content": "x"}}
    )
    unknown_decision = policy.evaluate({"name": "no_such_tool", "args": {}})

    assert read_decision.code == ToolPolicyCode.ALLOWED
    assert write_decision.code == ToolPolicyCode.PERMISSION_DENIED
    assert unknown_decision.code == ToolPolicyCode.UNKNOWN_TOOL


def test_pattern_policy_rejects_absolute_and_parent_escaping_patterns() -> None:
    absolute = pattern_policy("/tmp/**/*.py")
    parent = pattern_policy("../outside/**/*.py")
    nested_parent = pattern_policy("src/**/../secret.txt")
    allowed = pattern_policy("src/**/*.py")

    assert absolute.allowed is False
    assert absolute.reason == "workspace_escape"
    assert parent.allowed is False
    assert nested_parent.allowed is False
    assert allowed.allowed is True
