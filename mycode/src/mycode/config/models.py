"""Pydantic 配置模型，对应 CONFIG.md §2 字段总表。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, PrivateAttr, field_validator


class CompactConfig(BaseModel):
    threshold_pct: int = Field(default=75, ge=10, le=95)
    evict_threshold_bytes: int = Field(default=4096, ge=256)
    keep_recent_tool_results: int = Field(default=3, ge=1)


class SessionConfig(BaseModel):
    dir: str = ".mycode/sessions"
    auto_save: bool = True
    redact_keys: list[str] = Field(
        default_factory=lambda: [
            "authorization",
            "api_key",
            "api-key",
            "openai_api_key",
        ]
    )


class TeamConfig(BaseModel):
    enabled: bool = False
    poll_interval_sec: int = 5
    idle_timeout_sec: int = 60


class MCPServerConfig(BaseModel):
    type: Literal["stdio", "sse", "http"] = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_sec: int = 30
    enabled: bool = True


class UIConfig(BaseModel):
    theme: Literal["dark", "light", "auto"] = "dark"
    stream: bool = True
    show_tool_args: bool = True
    confirm_destructive: bool = True


class RoleConfig(BaseModel):
    """单个角色的模型覆盖。未填字段从顶层继承。"""

    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    default_query: dict[str, str] | None = None


class RolesConfig(BaseModel):
    """分角色模型: main(主对话) / summarize(压缩摘要) / subagent(子 agent)。"""

    main: RoleConfig = Field(default_factory=RoleConfig)
    summarize: RoleConfig = Field(default_factory=RoleConfig)
    subagent: RoleConfig = Field(default_factory=RoleConfig)


class Config(BaseModel):
    """根配置对象。"""

    provider: str = "openai"
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    fallback_model: str | None = None
    default_query: dict[str, str] | None = None

    max_tokens: int = 8192
    context_window: int = 128000
    temperature: float | None = None

    compact: CompactConfig = Field(default_factory=CompactConfig)

    parallel_tools: int = Field(default=4, ge=1, le=16)
    serial_only: bool = False
    tool_result_max_bytes: int = Field(default=51200, ge=1024)

    allowed_tools: list[str] | None = None
    denied_tools: list[str] = Field(default_factory=list)
    denied_paths: list[str] = Field(
        default_factory=lambda: ["~/.ssh", "~/.aws", "~/.gnupg", "**/.env*"]
    )
    bash_deny_patterns: list[str] = Field(default_factory=list)
    allow_outside_workspace: bool = False

    skills_dirs: list[str] = Field(
        default_factory=lambda: ["./skills", "~/.mycode/skills"]
    )
    memory_files: list[str] = Field(
        default_factory=lambda: [
            "CLAUDE.md",
            "AGENTS.md",
            ".mycode/MEMORY.md",
            "~/.mycode/CLAUDE.md",
        ]
    )

    session: SessionConfig = Field(default_factory=SessionConfig)
    team: TeamConfig = Field(default_factory=TeamConfig)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    ui: UIConfig = Field(default_factory=UIConfig)
    roles: RolesConfig = Field(default_factory=RolesConfig)

    @field_validator("base_url")
    @classmethod
    def _non_empty_base_url(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("base_url must be non-empty string when provided")
        return v

    def resolved_api_key(self) -> str | None:
        """从环境变量取实际 key；不做任何打印。"""
        import os

        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)

    # M5-1: 运行时可被 EnterWorktree 工具覆盖指向 worktree 目录。
    # 用 PrivateAttr 避免污染 settings.json。
    _workspace_override: Path | None = PrivateAttr(default=None)

    def workspace_root(self) -> Path:
        if self._workspace_override is not None:
            return self._workspace_override
        return Path.cwd()

    def set_workspace_override(self, path: Path | None) -> None:
        """内部 API,EnterWorktree / ExitWorktree 使用。传 None 表示恢复默认(cwd)。"""
        self._workspace_override = path

    def derive_for_role(self, role_name: str) -> "Config":
        """派生出某个 role 专用的 Config。

        顺序:
        1. 从顶层 Config 复制一份
        2. 若 roles.<name>.provider 指定,按 provider profile 填充 base_url/model/api_key_env/default_query
        3. 再用 roles.<name> 中显式给出的字段覆盖
        """
        from ..llm.providers import get_profile

        base = self.model_copy(deep=True)
        role: RoleConfig = getattr(self.roles, role_name, None)
        if role is None:
            return base
        # provider 指定 → 用该 profile 的默认值重置四元组
        if role.provider:
            base.provider = role.provider
            profile = get_profile(role.provider)
            for k in ("base_url", "model", "api_key_env", "default_query"):
                if profile.get(k) is not None:
                    setattr(base, k, profile[k])
        # 显式字段覆盖
        for k in ("base_url", "model", "api_key_env", "default_query"):
            v = getattr(role, k, None)
            if v is not None:
                setattr(base, k, v)
        return base
