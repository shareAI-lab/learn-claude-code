from __future__ import annotations

import json
from pathlib import Path

from coding_deepgent.plugins.schemas import LoadedPluginManifest, PluginManifest

PLUGIN_FILE_NAME = "plugin.json"


def plugin_root(workdir: Path, plugin_dir: Path) -> Path:
    if plugin_dir.is_absolute():
        return plugin_dir.resolve()
    return (workdir / plugin_dir).resolve()


def parse_plugin_manifest(path: Path) -> LoadedPluginManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    manifest = PluginManifest.model_validate(data)
    return LoadedPluginManifest(
        manifest=manifest,
        root=path.parent.resolve(),
        path=path.resolve(),
    )


def load_local_plugin(
    *, workdir: Path, plugin_dir: Path, name: str
) -> LoadedPluginManifest:
    root = plugin_root(workdir, plugin_dir)
    path = root / name / PLUGIN_FILE_NAME
    if not path.is_file():
        raise FileNotFoundError(f"Local plugin not found: {name}")
    loaded = parse_plugin_manifest(path)
    if loaded.manifest.name != name:
        raise ValueError(
            f"Plugin name mismatch: requested {name}, found {loaded.manifest.name}"
        )
    return loaded


def discover_local_plugins(
    *, workdir: Path, plugin_dir: Path
) -> tuple[LoadedPluginManifest, ...]:
    root = plugin_root(workdir, plugin_dir)
    if not root.exists():
        return ()
    if not root.is_dir():
        raise NotADirectoryError(f"Plugin root is not a directory: {root}")

    manifests: list[LoadedPluginManifest] = []
    for entry in sorted(root.iterdir(), key=lambda candidate: candidate.name):
        if not entry.is_dir():
            continue
        manifest_path = entry / PLUGIN_FILE_NAME
        if manifest_path.is_file():
            loaded = parse_plugin_manifest(manifest_path)
            if loaded.manifest.name != entry.name:
                raise ValueError(
                    "Plugin directory and manifest name must match: "
                    f"{entry.name} != {loaded.manifest.name}"
                )
            manifests.append(loaded)
    return tuple(manifests)
