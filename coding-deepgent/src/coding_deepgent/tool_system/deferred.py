from __future__ import annotations

import inspect
import json
import re
from collections.abc import Mapping
from typing import Any, cast

from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .capabilities import CapabilityRegistry, ToolCapability
from .middleware import ToolGuardMiddleware
from .policy import ToolPolicy

_WORD_SPLIT = re.compile(r"[\W_]+")


class ToolSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Search deferred tools by exact name or keywords. Use "
            "`select:<tool_name>` or `select:<tool_a>,<tool_b>` for exact selection."
        ),
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum deferred-tool matches to return.",
    )

    @field_validator("query")
    @classmethod
    def _query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query required")
        return value


class DeferredToolMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    execution: str = Field(..., min_length=1)
    rendering_result: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    call_via: str = Field(..., min_length=1)


class ToolSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    total_deferred_tools: int = Field(..., ge=0)
    matches: list[DeferredToolMatch] = Field(default_factory=list)


class InvokeDeferredToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    tool_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Exact deferred tool name returned by ToolSearch. "
            "Only tools on the deferred surface are allowed."
        ),
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON object matching the deferred tool's parameters schema exactly.",
    )
    runtime: ToolRuntime

    @field_validator("tool_name")
    @classmethod
    def _tool_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("tool_name required")
        return value


def _runtime_policy(runtime: ToolRuntime) -> ToolPolicy:
    context = getattr(runtime, "context", None)
    policy = getattr(context, "tool_policy", None)
    if not isinstance(policy, ToolPolicy):
        raise RuntimeError("Deferred tool bridge requires tool policy in runtime context")
    return policy


def _runtime_registry(runtime: ToolRuntime) -> CapabilityRegistry:
    registry = _runtime_policy(runtime).registry
    if not isinstance(registry, CapabilityRegistry):
        raise RuntimeError("Deferred tool bridge requires capability registry access")
    return registry


def _deferred_capabilities(
    registry: CapabilityRegistry,
) -> tuple[ToolCapability, ...]:
    return registry.capabilities_for_projection("deferred")


def _normalize_search_tokens(value: str) -> tuple[str, ...]:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    pieces = _WORD_SPLIT.split(camel_split.lower())
    return tuple(piece for piece in pieces if piece)


def _searchable_text(capability: ToolCapability) -> str:
    description = str(getattr(capability.tool, "description", "") or "")
    return " ".join(
        (
            capability.name,
            description,
            capability.source,
            capability.domain,
            capability.family,
            capability.execution,
            capability.rendering_result,
            *capability.tags,
        )
    ).lower()


def _search_score(capability: ToolCapability, terms: tuple[str, ...]) -> int:
    searchable = _searchable_text(capability)
    name_lower = capability.name.lower()
    name_tokens = set(_normalize_search_tokens(capability.name))
    score = 0
    for term in terms:
        if term == name_lower:
            score += 100
            continue
        if name_lower.startswith(term):
            score += 60
            continue
        if term in name_tokens:
            score += 40
            continue
        if term in searchable:
            score += 20
            continue
        return -1
    return score


def _selected_deferred_capabilities(
    registry: CapabilityRegistry,
    *,
    query: str,
    max_results: int,
) -> tuple[ToolCapability, ...]:
    deferred = _deferred_capabilities(registry)
    query = query.strip()
    lowered = query.lower()
    if lowered.startswith("select:"):
        requested = [
            item.strip().lower()
            for item in query.split(":", 1)[1].split(",")
            if item.strip()
        ]
        selected: list[ToolCapability] = []
        for tool_name in requested:
            for capability in deferred:
                if capability.name.lower() == tool_name:
                    selected.append(capability)
                    break
        return tuple(selected[:max_results])

    terms = tuple(term for term in _normalize_search_tokens(query) if term)
    if not terms:
        return ()

    scored = [
        (capability, _search_score(capability, terms))
        for capability in deferred
    ]
    ranked = [
        capability
        for capability, score in sorted(
            scored,
            key=lambda item: (-item[1], item[0].name),
        )
        if score >= 0
    ]
    return tuple(ranked[:max_results])


def _tool_parameters(capability: ToolCapability) -> dict[str, Any]:
    schema = cast(Any, capability.tool.tool_call_schema)
    return cast(dict[str, Any], schema.model_json_schema())


def _render_match(capability: ToolCapability) -> DeferredToolMatch:
    description = str(getattr(capability.tool, "description", "") or "").strip()
    return DeferredToolMatch(
        name=capability.name,
        description=description or capability.name,
        source=capability.source,
        execution=capability.execution,
        rendering_result=capability.rendering_result,
        tags=list(capability.tags),
        parameters=_tool_parameters(capability),
        call_via=(
            "invoke_deferred_tool(tool_name=<name>, arguments=<json object matching parameters>)"
        ),
    )


@tool(
    "ToolSearch",
    args_schema=ToolSearchInput,
    description=(
        "Search deferred tools and return their full JSON parameter schemas. "
        "Use this before invoke_deferred_tool when the current visible tool list "
        "does not expose the needed advanced or extension capability."
    ),
)
def tool_search(
    query: str,
    runtime: ToolRuntime,
    max_results: int = 5,
) -> str:
    registry = _runtime_registry(runtime)
    matches = _selected_deferred_capabilities(
        registry,
        query=query,
        max_results=max_results,
    )
    return ToolSearchResult(
        query=query,
        total_deferred_tools=len(_deferred_capabilities(registry)),
        matches=[_render_match(capability) for capability in matches],
    ).model_dump_json()


def _validated_deferred_args(
    capability: ToolCapability,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    schema = cast(Any, capability.tool.tool_call_schema)
    validated = schema.model_validate(dict(arguments))
    return cast(dict[str, Any], validated.model_dump())


def _call_tool_function(
    capability: ToolCapability,
    *,
    runtime: ToolRuntime,
    arguments: dict[str, Any],
) -> ToolMessage | Command[Any]:
    tool_object = capability.tool
    tool_func = getattr(tool_object, "func", None)
    if callable(tool_func):
        kwargs = dict(arguments)
        if "runtime" in inspect.signature(tool_func).parameters:
            kwargs["runtime"] = runtime
        result = tool_func(**kwargs)
    else:
        result = tool_object.invoke(arguments)
    if isinstance(result, (ToolMessage, Command)):
        return result
    rendered = result if isinstance(result, str) else json.dumps(result)
    return ToolMessage(
        content=rendered,
        tool_call_id=str(getattr(runtime, "tool_call_id", "") or ""),
    )


def _execute_deferred_capability(
    request: ToolCallRequest,
    capability: ToolCapability,
) -> ToolMessage | Command[Any]:
    validated_args = _validated_deferred_args(
        capability,
        cast(Mapping[str, Any], request.tool_call.get("args", {})),
    )
    return _call_tool_function(
        capability,
        runtime=request.runtime,
        arguments=validated_args,
    )


@tool(
    "invoke_deferred_tool",
    args_schema=InvokeDeferredToolInput,
    description=(
        "Execute one deferred tool by exact name. Use ToolSearch first, then pass "
        "arguments that exactly match the deferred tool's parameters schema."
    ),
)
def invoke_deferred_tool(
    tool_name: str,
    arguments: dict[str, Any],
    runtime: ToolRuntime,
) -> str:
    registry = _runtime_registry(runtime)
    capability = registry.get(tool_name)
    if capability is None or capability.exposure != "deferred" or not capability.enabled:
        return f"Error: Unknown deferred tool `{tool_name}`."

    tool_policy = _runtime_policy(runtime)
    context = getattr(runtime, "context", None)
    middleware = ToolGuardMiddleware(
        registry=registry,
        policy=tool_policy,
        event_sink=getattr(context, "event_sink", None),
    )
    tool_call = {
        "name": capability.name,
        "args": dict(arguments),
        "id": str(getattr(runtime, "tool_call_id", "") or f"deferred:{capability.name}"),
        "type": "tool_call",
    }
    request = ToolCallRequest(
        tool_call=cast(Any, tool_call),
        tool=capability.tool,
        state=getattr(runtime, "state", None),
        runtime=runtime,
    )
    result = middleware.wrap_tool_call(
        request,
        lambda current_request: _execute_deferred_capability(
            current_request,
            capability,
        ),
    )
    if isinstance(result, Command):
        raise RuntimeError(
            "Deferred tool bridge does not support command-update tools"
        )
    return str(result.content)
