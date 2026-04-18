from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from coding_deepgent.plugins import discover_local_plugins
from coding_deepgent.subagents.schemas import AgentDefinition

SUBAGENT_DIRNAME = ".coding-deepgent"
SUBAGENT_FILE_NAME = "SUBAGENTS.json"
PLUGIN_SUBAGENT_FILE_NAME = "subagents.json"


class LocalSubagentCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents: tuple[AgentDefinition, ...] = Field(default_factory=tuple)

    @field_validator("agents")
    @classmethod
    def _agent_names_must_be_unique(
        cls, value: tuple[AgentDefinition, ...]
    ) -> tuple[AgentDefinition, ...]:
        names = [item.agent_type for item in value]
        if len(set(names)) != len(names):
            raise ValueError("duplicate agent definitions are not allowed")
        return value


def local_subagent_path(workdir: Path) -> Path:
    return workdir / SUBAGENT_DIRNAME / SUBAGENT_FILE_NAME


def parse_local_subagent_catalog(path: Path) -> LocalSubagentCatalog:
    data = json.loads(path.read_text(encoding="utf-8"))
    return LocalSubagentCatalog.model_validate(data)


def parse_plugin_subagent_catalog(path: Path) -> LocalSubagentCatalog:
    return parse_local_subagent_catalog(path)


def discover_local_subagent_definitions(*, workdir: Path) -> tuple[AgentDefinition, ...]:
    path = local_subagent_path(workdir)
    if not path.exists():
        return ()
    if not path.is_file():
        raise FileNotFoundError(f"Local subagent catalog is not a file: {path}")
    return parse_local_subagent_catalog(path).agents


def discover_plugin_subagent_definitions(
    *,
    workdir: Path,
    plugin_dir: Path,
) -> tuple[AgentDefinition, ...]:
    definitions: list[AgentDefinition] = []
    for plugin in discover_local_plugins(workdir=workdir, plugin_dir=plugin_dir):
        declared_agents = plugin.manifest.agents
        if not declared_agents:
            continue
        catalog_path = plugin.root / PLUGIN_SUBAGENT_FILE_NAME
        if not catalog_path.is_file():
            raise FileNotFoundError(
                f"Plugin `{plugin.manifest.name}` declares agents but is missing {PLUGIN_SUBAGENT_FILE_NAME}"
            )
        catalog = parse_plugin_subagent_catalog(catalog_path)
        catalog_names = {item.agent_type for item in catalog.agents}
        if catalog_names != set(declared_agents):
            raise ValueError(
                f"Plugin `{plugin.manifest.name}` agent catalog mismatch: manifest={sorted(declared_agents)} catalog={sorted(catalog_names)}"
            )
        for definition in catalog.agents:
            if not definition.agent_type.startswith(f"{plugin.manifest.name}:"):
                raise ValueError(
                    f"Plugin subagent `{definition.agent_type}` must be namespaced with `{plugin.manifest.name}:`"
                )
            definitions.append(definition)
    return tuple(definitions)
