from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from coding_deepgent.permission_specs import PermissionRuleSpec

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
STATUS_FILE = PROJECT_ROOT / "project_status.json"

CheckpointerBackend = Literal["none", "memory"]
StoreBackend = Literal["none", "memory"]
PermissionMode = Literal[
    "default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"
]


def resolve_workdir() -> Path:
    configured = os.getenv("CODING_DEEPGENT_WORKDIR", "").strip()
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODING_DEEPGENT_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    workdir: Path = Field(default_factory=resolve_workdir)
    session_dir: Path = Field(default=Path(".coding-deepgent/sessions"))
    skill_dir: Path = Field(default=Path("skills"))
    plugin_dir: Path = Field(default=Path("plugins"))
    model_name: str = Field(default_factory=deepgent_model_name)
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    checkpointer_backend: CheckpointerBackend = "none"
    store_backend: StoreBackend = "none"
    permission_mode: PermissionMode = "default"
    permission_allow_rules: tuple[PermissionRuleSpec, ...] = ()
    permission_ask_rules: tuple[PermissionRuleSpec, ...] = ()
    permission_deny_rules: tuple[PermissionRuleSpec, ...] = ()
    trusted_workdirs: tuple[Path, ...] = ()
    custom_system_prompt: str | None = None
    append_system_prompt: str | None = None
    agent_name: str = "coding-deepgent"
    entrypoint: str = "coding-deepgent"
    model_timeout_seconds: int = Field(default=60, ge=1, le=600)
    auto_compact_threshold_tokens: int | None = Field(default=8000, ge=1)
    keep_recent_tool_results: int = Field(default=3, ge=0)
    keep_recent_messages_after_compact: int = Field(default=4, ge=0)

    @field_validator("workdir", mode="before")
    @classmethod
    def _resolve_workdir_value(cls, value: Any) -> Path:
        if value in (None, ""):
            return resolve_workdir()
        return Path(value).expanduser().resolve()

    @field_validator("model_name", mode="before")
    @classmethod
    def _resolve_model_name_value(cls, value: Any) -> str:
        resolved = str(value or "").strip()
        if not resolved:
            return deepgent_model_name()
        if resolved.lower().startswith("claude"):
            return DEFAULT_OPENAI_MODEL
        return resolved

    @model_validator(mode="after")
    def _normalize_paths(self) -> "Settings":
        if not self.session_dir.is_absolute():
            self.session_dir = (self.workdir / self.session_dir).resolve()
        else:
            self.session_dir = self.session_dir.expanduser().resolve()

        if not self.skill_dir.is_absolute():
            self.skill_dir = (self.workdir / self.skill_dir).resolve()
        else:
            self.skill_dir = self.skill_dir.expanduser().resolve()

        if not self.plugin_dir.is_absolute():
            self.plugin_dir = (self.workdir / self.plugin_dir).resolve()
        else:
            self.plugin_dir = self.plugin_dir.expanduser().resolve()

        normalized_trusted_workdirs: list[Path] = []
        for path in self.trusted_workdirs:
            if path.is_absolute():
                normalized = path.expanduser().resolve()
            else:
                normalized = (self.workdir / path).resolve()
            if normalized not in normalized_trusted_workdirs:
                normalized_trusted_workdirs.append(normalized)
        self.trusted_workdirs = tuple(normalized_trusted_workdirs)
        return self


def load_settings() -> Settings:
    return Settings()


def build_openai_model(
    settings: Settings | None = None,
    *,
    temperature: float = 0.0,
    timeout: int | None = None,
):
    active_settings = settings or load_settings()
    if active_settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY is required to run coding-deepgent. "
            "Set OPENAI_MODEL to choose a model and OPENAI_BASE_URL for an OpenAI-compatible endpoint."
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": active_settings.model_name,
        "temperature": temperature,
        "timeout": timeout or active_settings.model_timeout_seconds,
        "api_key": active_settings.openai_api_key.get_secret_value(),
    }
    if active_settings.openai_base_url:
        kwargs["base_url"] = active_settings.openai_base_url
    return ChatOpenAI(**kwargs)
