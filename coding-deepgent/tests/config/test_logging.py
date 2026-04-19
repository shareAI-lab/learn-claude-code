from __future__ import annotations

from structlog.testing import capture_logs

from coding_deepgent.logging_config import (
    configure_logging,
    logger_for,
    redact_value,
    safe_environment_snapshot,
)


def test_safe_environment_snapshot_redacts_provider_secret() -> None:
    snapshot = safe_environment_snapshot(
        {
            "OPENAI_API_KEY": "sk-secret",
            "OPENAI_BASE_URL": "https://example.invalid/v1",
            "OPENAI_MODEL": "gpt-test",
        }
    )

    assert snapshot == {
        "OPENAI_API_KEY": "<set>",
        "OPENAI_BASE_URL": "https://example.invalid/v1",
        "OPENAI_MODEL": "gpt-test",
    }
    assert "sk-secret" not in str(snapshot)


def test_redact_value_masks_named_secret_fields() -> None:
    assert redact_value("OPENAI_API_KEY", "sk-secret") == "<redacted>"
    assert (
        redact_value("OPENAI_BASE_URL", "https://example.invalid/v1")
        == "https://example.invalid/v1"
    )


def test_configure_logging_initializes_structlog_without_services() -> None:
    logger = configure_logging("DEBUG")

    assert logger is not None
    assert hasattr(logger, "bind")


def test_logger_for_binds_agent_scope_fields() -> None:
    configure_logging("DEBUG")

    with capture_logs() as logs:
        logger_for(
            "runtime_pressure",
            agent_name="agent-1",
            session_id="session-1",
            entrypoint="test",
        ).debug("observed")

    assert logs[0]["component"] == "runtime_pressure"
    assert logs[0]["agent_name"] == "agent-1"
    assert logs[0]["session_id"] == "session-1"
    assert logs[0]["entrypoint"] == "test"
