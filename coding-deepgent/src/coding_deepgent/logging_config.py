from __future__ import annotations

import logging as stdlib_logging
from collections.abc import Mapping
from typing import Any

import structlog

_REDACTED = "<redacted>"
_SET = "<set>"
_MISSING = "<missing>"

_SECRET_FIELD_NAMES = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "TOKEN",
    "SECRET",
    "PASSWORD",
}


def redact_value(name: str, value: str | None) -> str:
    if not value:
        return _MISSING
    if any(secret_name in name.upper() for secret_name in _SECRET_FIELD_NAMES):
        return _REDACTED
    return value


def presence_label(value: str | None) -> str:
    return _SET if value else _MISSING


def safe_environment_snapshot(env: Mapping[str, str | None]) -> dict[str, str]:
    return {
        "OPENAI_API_KEY": presence_label(env.get("OPENAI_API_KEY")),
        "OPENAI_BASE_URL": env.get("OPENAI_BASE_URL") or "<default>",
        "OPENAI_MODEL": env.get("OPENAI_MODEL") or env.get("MODEL_ID") or "<default>",
    }


def configure_logging(level: str = "INFO") -> Any:
    resolved_level = getattr(stdlib_logging, level.upper(), stdlib_logging.INFO)
    stdlib_logging.basicConfig(level=resolved_level, format="%(message)s", force=True)
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("coding_deepgent")


def logger_for(
    component: str,
    *,
    agent_name: str | None = None,
    session_id: str | None = None,
    **fields: object,
) -> Any:
    logger = structlog.get_logger("coding_deepgent").bind(
        component=component.strip() or "runtime"
    )
    if agent_name is not None:
        logger = logger.bind(agent_name=agent_name)
    if session_id is not None:
        logger = logger.bind(session_id=session_id)
    if fields:
        logger = logger.bind(**fields)
    return logger
