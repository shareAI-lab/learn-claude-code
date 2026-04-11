from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during import-only environments
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(override=True)

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
STATUS_FILE = PROJECT_ROOT / "project_status.json"


@dataclass(frozen=True)
class ProjectSettings:
    workdir: Path
    model_name: str


def resolve_workdir() -> Path:
    configured = os.getenv("CODING_DEEPGENT_WORKDIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd().resolve()


def deepgent_model_name() -> str:
    openai_model = os.getenv("OPENAI_MODEL", "").strip()
    if openai_model:
        return openai_model

    legacy_model = os.getenv("MODEL_ID", "").strip()
    if legacy_model and not legacy_model.lower().startswith("claude"):
        return legacy_model

    return DEFAULT_OPENAI_MODEL


def load_settings() -> ProjectSettings:
    return ProjectSettings(workdir=resolve_workdir(), model_name=deepgent_model_name())


def build_openai_model(*, temperature: float = 0.0, timeout: int = 60):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required to run coding-deepgent. "
            "Set OPENAI_MODEL to choose a model and OPENAI_BASE_URL for an OpenAI-compatible endpoint."
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": deepgent_model_name(),
        "temperature": temperature,
        "timeout": timeout,
    }
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)
