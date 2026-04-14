from __future__ import annotations

from dataclasses import dataclass

from coding_deepgent.mcp.loader import MCPRuntimeLoadResult
from coding_deepgent.plugins import PluginRegistry


@dataclass(frozen=True, slots=True)
class StartupContractStatus:
    plugin_count: int
    mcp_config_loaded: bool
    mcp_adapter_available: bool


def validate_startup_contract(
    *,
    validated_plugin_registry: PluginRegistry,
    mcp_runtime_load_result: MCPRuntimeLoadResult,
) -> StartupContractStatus:
    return StartupContractStatus(
        plugin_count=len(validated_plugin_registry.names()),
        mcp_config_loaded=mcp_runtime_load_result.loaded_config is not None,
        mcp_adapter_available=mcp_runtime_load_result.adapter_available,
    )


def require_startup_contract(
    startup_contract: StartupContractStatus,
) -> StartupContractStatus:
    return startup_contract
