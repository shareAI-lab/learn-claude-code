"""Provider profile presets.

每个 profile 给出 base_url / 推荐 model / api_key_env 的默认值。
用户在 settings.json 只需写 `"provider": "deepseek"`，其余字段会从 profile 取默认。
"""
from __future__ import annotations

from typing import Any


Profile = dict[str, Any]

PROFILES: dict[str, Profile] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "default_query": None,
        "cache_mode": "auto",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_query": None,
        "cache_mode": "auto",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "api_key_env": "DASHSCOPE_API_KEY",
        "default_query": None,
        "cache_mode": "auto",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_query": None,
        "cache_mode": "explicit",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5-coder",
        "api_key_env": "OLLAMA_API_KEY",
        "default_query": None,
        "cache_mode": "off",
    },
    "vllm": {
        "base_url": "http://localhost:8000/v1",
        "model": None,
        "api_key_env": "VLLM_API_KEY",
        "default_query": None,
        "cache_mode": "off",
    },
    # fenbi 内部网关,默认中档模型
    "fenbi": {
        "base_url": "http://keapi-inner.fenbilantian.com/agi/api/openai/v1",
        "model": "pa/gpt-5.4",
        "api_key_env": "FENBI_API_KEY",
        "default_query": {"service_provider": "ppio"},
        "cache_mode": "auto",
    },
    # fenbi 快捷 profile: 从弱到强
    "fenbi-mini": {
        "base_url": "http://keapi-inner.fenbilantian.com/agi/api/openai/v1",
        "model": "pa/gpt-5.4-mini",
        "api_key_env": "FENBI_API_KEY",
        "default_query": {"service_provider": "ppio"},
        "cache_mode": "auto",
    },
    "fenbi-sonnet": {
        "base_url": "http://keapi-inner.fenbilantian.com/agi/api/openai/v1",
        "model": "pa/claude-sonnet-4-6",
        "api_key_env": "FENBI_API_KEY",
        "default_query": {"service_provider": "ppio"},
        "cache_mode": "explicit",
    },
    "fenbi-glm": {
        "base_url": "http://keapi-inner.fenbilantian.com/agi/api/openai/v1",
        "model": "zai-org/glm-5-turbo",
        "api_key_env": "FENBI_API_KEY",
        "default_query": {"service_provider": "ppio"},
        "cache_mode": "auto",
    },
    "custom": {
        "base_url": None,
        "model": None,
        "api_key_env": None,
        "default_query": None,
        "cache_mode": "auto",
    },
}


def get_profile(name: str) -> Profile:
    """按名取 profile，未知名 fallback 到 custom。"""
    return PROFILES.get(name, PROFILES["custom"]).copy()
