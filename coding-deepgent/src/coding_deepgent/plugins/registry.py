from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from coding_deepgent.plugins.schemas import LoadedPluginManifest


@dataclass(frozen=True, slots=True)
class PluginCapabilityDeclaration:
    plugin_name: str
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    resources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidatedPluginDeclaration(PluginCapabilityDeclaration):
    pass


class PluginRegistry:
    def __init__(self, plugins: Iterable[LoadedPluginManifest] = ()) -> None:
        ordered = tuple(plugins)
        self._plugins = ordered
        self._by_name = {plugin.manifest.name: plugin for plugin in ordered}
        if len(self._by_name) != len(ordered):
            raise ValueError("Plugin names must be unique")

    def names(self) -> list[str]:
        return list(self._by_name)

    def get(self, name: str) -> LoadedPluginManifest | None:
        return self._by_name.get(name)

    def all(self) -> tuple[LoadedPluginManifest, ...]:
        return self._plugins

    def declarations(self) -> tuple[PluginCapabilityDeclaration, ...]:
        return tuple(
            PluginCapabilityDeclaration(
                plugin_name=plugin.manifest.name,
                skills=plugin.manifest.skills,
                tools=plugin.manifest.tools,
                resources=plugin.manifest.resources,
            )
            for plugin in self._plugins
        )

    def declared_tools(self) -> tuple[str, ...]:
        return tuple(tool for item in self.declarations() for tool in item.tools)

    def declared_skills(self) -> tuple[str, ...]:
        return tuple(skill for item in self.declarations() for skill in item.skills)

    def declared_resources(self) -> tuple[str, ...]:
        return tuple(
            resource for item in self.declarations() for resource in item.resources
        )

    def validate(
        self,
        *,
        known_tools: set[str],
        known_skills: set[str],
        known_resources: set[str] | None = None,
    ) -> tuple[ValidatedPluginDeclaration, ...]:
        validated: list[ValidatedPluginDeclaration] = []
        for item in self.declarations():
            missing_tools = [tool for tool in item.tools if tool not in known_tools]
            missing_skills = [
                skill for skill in item.skills if skill not in known_skills
            ]
            missing_resources = (
                [
                    resource
                    for resource in item.resources
                    if resource not in known_resources
                ]
                if known_resources is not None
                else []
            )
            if missing_tools or missing_skills or missing_resources:
                raise ValueError(
                    f"Plugin `{item.plugin_name}` declares unknown entries: "
                    f"tools={missing_tools}, skills={missing_skills}, "
                    f"resources={missing_resources}"
                )
            validated.append(
                ValidatedPluginDeclaration(
                    plugin_name=item.plugin_name,
                    skills=item.skills,
                    tools=item.tools,
                    resources=item.resources,
                )
            )
        return tuple(validated)
