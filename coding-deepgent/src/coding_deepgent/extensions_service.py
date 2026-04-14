from __future__ import annotations

from collections.abc import Sequence

from coding_deepgent.mcp import MCPRuntimeLoadResult, load_mcp_runtime_extensions
from coding_deepgent.plugins import PluginRegistry, discover_local_plugins
from coding_deepgent.skills import discover_local_skills
from coding_deepgent.settings import Settings


def plugin_registry(settings: Settings) -> PluginRegistry:
    return PluginRegistry(
        discover_local_plugins(
            workdir=settings.workdir,
            plugin_dir=settings.plugin_dir,
        )
    )


def mcp_runtime_load_result(settings: Settings) -> MCPRuntimeLoadResult:
    return load_mcp_runtime_extensions(workdir=settings.workdir)


def mcp_capabilities(result: MCPRuntimeLoadResult) -> list[object]:
    return list(result.capabilities)


def combine_extension_capabilities(
    manual_extension_capabilities: Sequence[object],
    mcp_capabilities: Sequence[object],
) -> list[object]:
    return [*manual_extension_capabilities, *mcp_capabilities]


def validate_plugin_registry(
    plugin_registry: PluginRegistry,
    settings: Settings,
    capability_registry,
) -> PluginRegistry:
    declarable_names = getattr(capability_registry, "declarable_names", None)
    known_tools = (
        set(declarable_names())
        if callable(declarable_names)
        else set(capability_registry.names())
    )
    known_skills = {
        skill.metadata.name
        for skill in discover_local_skills(
            workdir=settings.workdir,
            skill_dir=settings.skill_dir,
        )
    }
    plugin_registry.validate(
        known_tools=known_tools,
        known_skills=known_skills,
    )
    return plugin_registry
