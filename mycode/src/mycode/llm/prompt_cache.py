"""M6-4: Prompt Cache 支持。

两件事:

1) apply_cache_control(messages, mode)
   - mode="explicit" 时,给 system 首条与最后一条 user 消息注入
     `cache_control={type:"ephemeral"}` 标记(Anthropic / OpenRouter Claude 族)
   - mode="auto"/"off" 时原样返回

   注意: 我们并不修改原 messages,而是返回一份浅拷贝,
   且只在命中的消息里把 string content 转成 list[dict] 形式。

2) extract_cached_tokens(usage_dict) -> int
   归一后端差异:
   - OpenAI:   usage.prompt_tokens_details.cached_tokens
   - DeepSeek: usage.prompt_cache_hit_tokens
   - Anthropic/OpenRouter: usage.cache_read_input_tokens
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def resolve_cache_mode(cfg_mode: str, profile_mode: str | None) -> str:
    """若用户把 mode 留成默认 'auto',且 profile 指定了更具体值,用 profile。

    其他情况下以用户配置为准。
    """
    if cfg_mode == "auto" and profile_mode in ("off", "explicit"):
        return profile_mode
    return cfg_mode


def _wrap_content_for_cache(content: Any) -> list[dict[str, Any]]:
    """把 string 或 list content 规范成 list[dict],并给最后一块加 cache_control。"""
    if isinstance(content, str):
        blocks: list[dict[str, Any]] = [{"type": "text", "text": content}]
    elif isinstance(content, list):
        blocks = deepcopy(content)
    else:
        # 未知类型,不动
        return content  # type: ignore[return-value]
    if not blocks:
        return blocks
    # 挑最后一个 text block 打标记;没有 text 就给末块打
    target = None
    for b in reversed(blocks):
        if isinstance(b, dict) and b.get("type") == "text":
            target = b
            break
    if target is None:
        target = blocks[-1] if isinstance(blocks[-1], dict) else None
    if isinstance(target, dict):
        target["cache_control"] = {"type": "ephemeral"}
    return blocks


def apply_cache_control(
    messages: list[dict[str, Any]],
    mode: str,
) -> list[dict[str, Any]]:
    """返回处理后的 messages 副本;仅在 mode='explicit' 时注入 cache_control。"""
    if mode != "explicit":
        return messages
    if not messages:
        return messages

    out: list[dict[str, Any]] = [dict(m) for m in messages]

    # 1) 给第一条 system 打标
    for m in out:
        if m.get("role") == "system":
            m["content"] = _wrap_content_for_cache(m.get("content", ""))
            break

    # 2) 给最后一条 user 打标(跳过 tool_result)
    for m in reversed(out):
        if m.get("role") == "user":
            m["content"] = _wrap_content_for_cache(m.get("content", ""))
            break

    return out


def extract_cached_tokens(usage: Any) -> int:
    """从 usage dict 里按后端差异取 cached_tokens,找不到返回 0。"""
    if usage is None:
        return 0
    if not isinstance(usage, dict):
        try:
            usage = dict(usage)
        except Exception:
            return 0

    # OpenAI: usage.prompt_tokens_details.cached_tokens
    details = usage.get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        v = details.get("cached_tokens")
        if isinstance(v, int) and v > 0:
            return v

    # DeepSeek: usage.prompt_cache_hit_tokens
    v = usage.get("prompt_cache_hit_tokens")
    if isinstance(v, int) and v > 0:
        return v

    # Anthropic / OpenRouter Claude: usage.cache_read_input_tokens
    v = usage.get("cache_read_input_tokens")
    if isinstance(v, int) and v > 0:
        return v

    # 直接 cached_tokens(部分兼容网关)
    v = usage.get("cached_tokens")
    if isinstance(v, int) and v > 0:
        return v

    return 0
