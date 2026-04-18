from __future__ import annotations

import json
from pathlib import Path

import pytest
from dependency_injector import providers
from pydantic import ValidationError

from coding_deepgent.containers import AppContainer
from coding_deepgent.plugins import (
    LoadedPluginManifest,
    PluginManifest,
    PluginRegistry,
    ValidatedPluginDeclaration,
    discover_local_plugins,
    load_local_plugin,
    parse_plugin_manifest,
    plugin_root,
)
from coding_deepgent.settings import Settings


def write_plugin(root: Path, name: str, payload: dict[str, object]) -> Path:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    path = plugin_dir / "plugin.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_plugin_agents(root: Path, plugin_name: str, payload: dict[str, object]) -> Path:
    plugin_dir = root / plugin_name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    path = plugin_dir / "subagents.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def valid_manifest(name: str = "demo") -> dict[str, object]:
    return {
        "name": name,
        "description": "Demo extension",
        "version": "1.0.0",
        "skills": ["demo:review"],
        "tools": ["read_file"],
        "resources": ["demo_notes"],
        "agents": [],
    }


def write_skill(root: Path, name: str = "demo:review") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Demo skill\n---\n\nUse this skill carefully.",
        encoding="utf-8",
    )


def test_plugin_manifest_schema_is_strict_and_metadata_only() -> None:
    manifest = PluginManifest.model_validate(valid_manifest())

    assert manifest.name == "demo"
    assert manifest.skills == ("demo:review",)
    assert manifest.tools == ("read_file",)
    assert manifest.resources == ("demo_notes",)
    assert manifest.agents == ()

    with pytest.raises(ValidationError):
        PluginManifest.model_validate({"name": "demo"})

    with pytest.raises(ValidationError):
        PluginManifest.model_validate({**valid_manifest(), "extra": True})

    for blocked in ("permissionMode", "mcpServers", "hooks", "prompt globals"):
        with pytest.raises(ValidationError):
            PluginManifest.model_validate({**valid_manifest(), blocked: []})


def test_plugin_manifest_values_are_explicit_local_identifiers() -> None:
    for payload in (
        {**valid_manifest(), "tools": ["../read_file"]},
        {**valid_manifest(), "skills": ["pkg.module.skill"]},
        {**valid_manifest(), "resources": ["https://example.invalid/r"]},
        {**valid_manifest(), "tools": ["read_file", "read_file"]},
    ):
        with pytest.raises(ValidationError):
            PluginManifest.model_validate(payload)


def test_local_plugin_loader_is_deterministic_and_does_not_execute_code(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    write_plugin(root, "zeta", valid_manifest("zeta"))
    alpha_path = write_plugin(root, "alpha", valid_manifest("alpha"))
    (root / "alpha" / "explode.py").write_text(
        "raise RuntimeError('must not run')",
        encoding="utf-8",
    )

    assert plugin_root(tmp_path, Path("plugins")) == root.resolve()
    assert parse_plugin_manifest(alpha_path).manifest.name == "alpha"
    assert load_local_plugin(workdir=tmp_path, plugin_dir=Path("plugins"), name="alpha")
    assert [
        item.manifest.name
        for item in discover_local_plugins(workdir=tmp_path, plugin_dir=Path("plugins"))
    ] == ["alpha", "zeta"]

    with pytest.raises(FileNotFoundError):
        load_local_plugin(workdir=tmp_path, plugin_dir=Path("plugins"), name="missing")


def test_plugin_registry_exposes_declarations_without_runtime_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    write_plugin(root, "alpha", valid_manifest("alpha"))
    write_plugin(
        root,
        "beta",
        {
            **valid_manifest("beta"),
            "tools": ["TodoWrite"],
            "skills": [],
            "resources": ["beta_resource"],
        },
    )

    registry = PluginRegistry(
        discover_local_plugins(workdir=tmp_path, plugin_dir=Path("plugins"))
    )

    assert registry.names() == ["alpha", "beta"]
    assert registry.declared_tools() == ("read_file", "TodoWrite")
    assert registry.declared_skills() == ("demo:review",)
    assert registry.declared_resources() == ("demo_notes", "beta_resource")
    assert registry.declared_agents() == ()

    validated = registry.validate(
        known_tools={"read_file", "TodoWrite"},
        known_skills={"demo:review"},
    )
    assert isinstance(validated[0], ValidatedPluginDeclaration)


def test_plugin_registry_validation_fails_for_unknown_tool_or_skill(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    write_plugin(root, "alpha", valid_manifest("alpha"))
    registry = PluginRegistry(
        discover_local_plugins(workdir=tmp_path, plugin_dir=Path("plugins"))
    )

    with pytest.raises(ValueError, match="unknown entries"):
        registry.validate(known_tools={"TodoWrite"}, known_skills=set())


def test_plugin_registry_rejects_duplicate_plugin_names(tmp_path: Path) -> None:
    first_path = write_plugin(tmp_path / "plugins-a", "demo", valid_manifest("demo"))
    second_path = write_plugin(tmp_path / "plugins-b", "demo", valid_manifest("demo"))

    with pytest.raises(ValueError, match="Plugin names must be unique"):
        PluginRegistry(
            [
                LoadedPluginManifest(
                    manifest=parse_plugin_manifest(first_path).manifest,
                    root=first_path.parent,
                    path=first_path,
                ),
                LoadedPluginManifest(
                    manifest=parse_plugin_manifest(second_path).manifest,
                    root=second_path.parent,
                    path=second_path,
                ),
            ]
        )


def test_plugin_registry_resource_validation_requires_explicit_known_resources(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    write_plugin(root, "alpha", valid_manifest("alpha"))
    registry = PluginRegistry(
        discover_local_plugins(workdir=tmp_path, plugin_dir=Path("plugins"))
    )

    with pytest.raises(ValueError, match="unknown entries"):
        registry.validate(
            known_tools={"read_file"},
            known_skills={"demo:review"},
            known_resources=set(),
        )

    validated = registry.validate(
        known_tools={"read_file"},
        known_skills={"demo:review"},
        known_resources={"demo_notes"},
    )
    assert validated[0].resources == ("demo_notes",)


def test_settings_resolves_plugin_dir_under_workdir(tmp_path: Path) -> None:
    settings = Settings(workdir=tmp_path, plugin_dir=Path("extensions"))

    assert settings.plugin_dir == (tmp_path / "extensions").resolve()


def test_app_container_validates_plugin_declarations_against_known_local_capabilities(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "skills")
    write_plugin(tmp_path / "plugins", "demo", valid_manifest("demo"))

    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    validated = container.validated_plugin_registry()

    assert validated.names() == ["demo"]


def test_app_container_blocks_invalid_plugin_declarations_on_explicit_startup_validation(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "skills")
    write_plugin(
        tmp_path / "plugins",
        "demo",
        {
            **valid_manifest("demo"),
            "tools": ["no_such_tool"],
            "resources": [],
        },
    )

    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    with pytest.raises(ValueError, match="unknown entries"):
        container.startup_contract()
    with pytest.raises(ValueError, match="unknown entries"):
        container.agent()


def test_app_container_validates_plugin_provided_subagent_definitions(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "skills")
    write_plugin(
        tmp_path / "plugins",
        "demo",
        {
            **valid_manifest("demo"),
            "agents": ["demo:docs_review"],
        },
    )
    write_plugin_agents(
        tmp_path / "plugins",
        "demo",
        {
            "agents": [
                {
                    "agent_type": "demo:docs_review",
                    "description": "Review docs",
                    "when_to_use": "Use for plugin-provided docs review.",
                    "instructions": "Review docs from the plugin catalog.",
                    "tool_allowlist": ["read_file", "glob"],
                    "disallowed_tools": ["write_file"],
                    "max_turns": 6,
                }
            ]
        },
    )

    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    validated = container.validated_plugin_registry()

    assert validated.names() == ["demo"]
    assert validated.declared_agents() == ("demo:docs_review",)


def test_child_only_tools_are_not_plugin_declarable(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "skills")
    write_plugin(
        tmp_path / "plugins",
        "demo",
        {
            **valid_manifest("demo"),
            "tools": ["glob"],
            "resources": [],
        },
    )

    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    with pytest.raises(ValueError, match="unknown entries"):
        container.startup_contract()
