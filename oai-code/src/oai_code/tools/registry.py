"""工具注册表与调度。

每个 Tool 声明 name / description / input_schema / requires / handler。
handler 返回字符串(tool_result content),失败抛异常由 loop 统一转成 "Error: ..."。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..config.models import Config


TOOL_SCHEMA_VERSION = "1"


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]
    requires: list[str] = field(default_factory=list)  # exec|write|network|delegate
    # 用于并行派发时判断是否与其他工具冲突(同文件路径串行)
    path_fields: tuple[str, ...] = ()

    def to_openai_spec(self) -> dict[str, Any]:
        """转成 OpenAI tools 数组里的单项。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class ToolRegistry:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def is_allowed(self, name: str) -> bool:
        if name in self.cfg.denied_tools:
            return False
        if self.cfg.allowed_tools is not None and name not in self.cfg.allowed_tools:
            return False
        return True

    def openai_specs(self) -> list[dict[str, Any]]:
        return [
            t.to_openai_spec()
            for t in self._tools.values()
            if self.is_allowed(t.name)
        ]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def allowed_names(self) -> list[str]:
        return [n for n in self._tools if self.is_allowed(n)]
