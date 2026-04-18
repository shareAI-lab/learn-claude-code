from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dependency_injector import containers, providers

from coding_deepgent.filesystem import glob_search, grep_search
from coding_deepgent.memory import delete_memory, list_memory, save_memory
from coding_deepgent.permissions import PermissionManager
from coding_deepgent.permissions.rules import PermissionRuleSpec, expand_rule_specs
from coding_deepgent.skills import load_skill
from coding_deepgent.subagents import run_fork, run_subagent
from coding_deepgent.tasks import (
    plan_get,
    plan_save,
    task_create,
    task_get,
    task_list,
    task_update,
)
from coding_deepgent.tool_system import (
    ToolCapability,
    ToolGuardMiddleware,
    ToolPolicy,
    build_builtin_capabilities,
    build_capability_registry,
)


def _combine_tools(*groups: Sequence[object]) -> list[object]:
    combined: list[object] = []
    for group in groups:
        combined.extend(group)
    return combined


def _tools_from_capabilities(capabilities: Sequence[ToolCapability]) -> list[object]:
    return [capability.tool for capability in capabilities]


def _singleton_list(item: object) -> list[object]:
    return [item]


def _permission_rules(
    allow_rules: Sequence[PermissionRuleSpec],
    ask_rules: Sequence[PermissionRuleSpec],
    deny_rules: Sequence[PermissionRuleSpec],
):
    return expand_rule_specs(
        allow_rules=allow_rules,
        ask_rules=ask_rules,
        deny_rules=deny_rules,
    )


class ToolSystemContainer(containers.DeclarativeContainer):
    filesystem_tools: Any = providers.Dependency(default=providers.Object([]))
    todo_tools: Any = providers.Dependency(default=providers.Object([]))
    memory_tools: Any = providers.Dependency(
        default=providers.Object([save_memory, list_memory, delete_memory])
    )
    skill_tools: Any = providers.Dependency(default=providers.Object([load_skill]))
    task_tools: Any = providers.Dependency(
        default=providers.Object(
            [task_create, task_get, task_list, task_update, plan_save, plan_get]
        )
    )
    subagent_tools: Any = providers.Dependency(
        default=providers.Object([run_subagent, run_fork])
    )
    extension_capabilities: Any = providers.Dependency(default=providers.Object([]))
    permission_mode: Any = providers.Dependency(default=providers.Object("default"))
    permission_allow_rules: Any = providers.Dependency(default=providers.Object(()))
    permission_ask_rules: Any = providers.Dependency(default=providers.Object(()))
    permission_deny_rules: Any = providers.Dependency(default=providers.Object(()))
    workdir: Any = providers.Dependency(default=providers.Object(None))
    trusted_workdirs: Any = providers.Dependency(default=providers.Object(()))
    event_sink: Any = providers.Dependency(default=providers.Object(None))
    extension_tools: Any = providers.Callable(
        _tools_from_capabilities,
        extension_capabilities,
    )
    permission_rules: Any = providers.Callable(
        _permission_rules,
        permission_allow_rules,
        permission_ask_rules,
        permission_deny_rules,
    )

    base_tools: Any = providers.Callable(
        _combine_tools,
        filesystem_tools,
        todo_tools,
        memory_tools,
        skill_tools,
        task_tools,
        subagent_tools,
    )
    builtin_capabilities: Any = providers.Callable(
        build_builtin_capabilities,
        filesystem_tools=filesystem_tools,
        discovery_tools=providers.Object((glob_search, grep_search)),
        todo_tools=todo_tools,
        memory_tools=memory_tools,
        skill_tools=skill_tools,
        task_tools=task_tools,
        subagent_tools=subagent_tools,
    )
    capability_registry: Any = providers.Callable(
        build_capability_registry,
        builtin_capabilities=builtin_capabilities,
        extension_capabilities=extension_capabilities,
    )
    tools: Any = providers.Callable(
        lambda registry: registry.project("main").tools(),
        capability_registry,
    )
    permission_manager: Any = providers.Factory(
        PermissionManager,
        mode=permission_mode,
        rules=permission_rules,
        workdir=workdir,
        trusted_workdirs=trusted_workdirs,
    )
    policy: Any = providers.Factory(
        ToolPolicy,
        registry=capability_registry,
        permission_manager=permission_manager,
    )
    middleware: Any = providers.Factory(
        ToolGuardMiddleware,
        registry=capability_registry,
        policy=policy,
        event_sink=event_sink,
    )
    middleware_list: Any = providers.Callable(_singleton_list, middleware)
