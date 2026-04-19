"""四级配置加载，对应 CONFIG.md §1。

顺序（低 → 高）：
1. env defaults
2. ~/.oaic/settings.json
3. ./.oaic/settings.json
4. --config <path> / $OAIC_CONFIG
5. CLI flag overrides
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..llm.providers import get_profile
from .models import Config


ENV_PREFIX = "OAIC_"


def _deep_merge(base: dict, override: dict) -> dict:
    """dict 逐键深合并，list/scalar 整体替换。`mcp_servers` 按 key 合并。"""
    result = dict(base)
    for k, v in override.items():
        if k == "mcp_servers" and isinstance(v, dict) and isinstance(result.get(k), dict):
            merged = dict(result[k])
            merged.update(v)  # 同名 key 整体替换
            result[k] = merged
        elif isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _env_defaults() -> dict[str, Any]:
    """从 OAIC_* 环境变量推出默认字段。"""
    d: dict[str, Any] = {}
    if v := os.environ.get(f"{ENV_PREFIX}PROVIDER"):
        d["provider"] = v
    if v := os.environ.get(f"{ENV_PREFIX}MODEL"):
        d["model"] = v
    if v := os.environ.get(f"{ENV_PREFIX}BASE_URL"):
        d["base_url"] = v
    return d


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"oaic: invalid JSON in {path}: {e}")


def _apply_profile(d: dict[str, Any]) -> dict[str, Any]:
    """根据 provider 字段填充未显式覆盖的默认值。"""
    provider = d.get("provider") or "openai"
    profile = get_profile(provider)
    for key in ("base_url", "model", "api_key_env", "default_query"):
        if d.get(key) is None and profile.get(key) is not None:
            d[key] = profile[key]
    return d


def load_config(
    *,
    cli_overrides: dict[str, Any] | None = None,
    extra_config_path: str | None = None,
) -> Config:
    """执行 CONFIG.md §1 的完整加载流程。"""
    # 1. env defaults
    layers: list[dict[str, Any]] = [_env_defaults()]

    # 2. user settings
    user_settings = Path.home() / ".oaic" / "settings.json"
    layers.append(_load_json_file(user_settings))

    # 3. project settings
    project_settings = Path.cwd() / ".oaic" / "settings.json"
    layers.append(_load_json_file(project_settings))

    # 4. --config / OAIC_CONFIG
    extra = extra_config_path or os.environ.get(f"{ENV_PREFIX}CONFIG")
    if extra:
        layers.append(_load_json_file(Path(extra).expanduser()))

    # 5. CLI overrides (顶层整体替换)
    if cli_overrides:
        layers.append(cli_overrides)

    merged: dict[str, Any] = {}
    for layer in layers:
        merged = _deep_merge(merged, layer)

    merged = _apply_profile(merged)

    try:
        return Config.model_validate(merged)
    except ValidationError as e:
        lines = ["oaic: invalid config"]
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            lines.append(f"  - {loc}: {err['msg']}")
        raise SystemExit("\n".join(lines))
