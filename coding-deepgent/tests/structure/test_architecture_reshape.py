from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "coding_deepgent"


def _text(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


def test_domain_and_service_modules_do_not_import_cli() -> None:
    checked = [
        *sorted((SRC / "filesystem").glob("*.py")),
        *sorted((SRC / "hooks").glob("*.py")),
        *sorted((SRC / "sessions").glob("*.py")),
        *sorted((SRC / "mcp").glob("*.py")),
        *sorted((SRC / "plugins").glob("*.py")),
        *sorted((SRC / "permissions").glob("*.py")),
        *sorted((SRC / "skills").glob("*.py")),
        *sorted((SRC / "tasks").glob("*.py")),
        *sorted((SRC / "todo").glob("*.py")),
        SRC / "extensions_service.py",
        SRC / "startup.py",
    ]
    offenders = [
        str(path.relative_to(ROOT))
        for path in checked
        if "coding_deepgent.cli" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_app_uses_shared_agent_loop_service_and_not_direct_hook_or_runtime_logic() -> None:
    text = _text("app.py")
    public_surface_text = _text("__init__.py")

    assert "from coding_deepgent import agent_loop_service" in text
    assert "dispatch_runtime_hook" not in text
    assert "normalize_messages" not in text
    assert "latest_assistant_text" not in text
    assert "agent_loop_service.run_agent_loop(" in text
    assert "SESSION_STATE" not in text
    assert "SESSION_STATE" not in public_surface_text


def test_tool_middleware_uses_shared_hook_dispatcher() -> None:
    text = _text("tool_system/middleware.py")

    assert "dispatch_context_hook" in text
    assert "HookPayload(" not in text
    assert '"hook_start"' not in text


def test_startup_contract_is_explicit() -> None:
    bootstrap_text = _text("bootstrap.py")
    app_text = _text("app.py")
    startup_text = _text("startup.py")
    container_text = _text("containers/app.py")
    agent_service_text = _text("agent_service.py")
    agent_provider_block = container_text.split("agent: Any = providers.Factory(", 1)[1]

    assert "def validate_container_startup" in bootstrap_text
    assert "validate_container_startup(container=container)" in app_text
    assert "validate_startup_contract" in startup_text
    assert "require_startup_contract" in startup_text
    assert "create_compiled_agent_after_startup_validation" in agent_provider_block
    assert "startup_contract=validated_startup_contract" in agent_provider_block
    assert "validated_plugin_registry=validated_plugin_registry" not in agent_provider_block
    assert "create_compiled_agent_after_startup_validation" in agent_service_text


def test_filesystem_execution_primary_path_is_runtime_aware() -> None:
    tools_text = _text("filesystem/tools.py")
    discovery_text = _text("filesystem/discovery.py")
    service_text = _text("filesystem/service.py")
    policy_text = _text("filesystem/policy.py")

    assert "ToolRuntime" in tools_text
    assert "ToolRuntime" in discovery_text
    assert "runtime_from_context(" in tools_text
    assert "runtime_from_context(" in discovery_text
    assert "safe_path(" not in tools_text
    assert "safe_path(" not in discovery_text
    assert "FilesystemRuntime" in service_text
    assert "load_settings" not in policy_text
    assert "Path.cwd()" not in policy_text


def test_cli_module_stays_a_thin_entrypoint() -> None:
    cli_text = _text("cli.py")

    assert "CliRuntime =" not in cli_text
    assert "SessionSummary =" not in cli_text
    assert "DoctorCheck =" not in cli_text
