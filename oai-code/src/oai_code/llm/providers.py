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
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_query": None,
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "api_key_env": "DASHSCOPE_API_KEY",
        "default_query": None,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_query": None,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5-coder",
        "api_key_env": "OLLAMA_API_KEY",
        "default_query": None,
    },
    "vllm": {
        "base_url": "http://localhost:8000/v1",
        "model": None,
        "api_key_env": "VLLM_API_KEY",
        "default_query": None,
    },
    "fenbi": {
        "base_url": "http://keapi-inner.fenbilantian.com/agi/api/openai/v1",
        "model": "pa/gpt-5.4",
        "api_key_env": "FENBI_API_KEY",
        "default_query": {"service_provider": "ppio"},
    },
    "custom": {
        "base_url": None,
        "model": None,
        "api_key_env": None,
        "default_query": None,
    },
}


def get_profile(name: str) -> Profile:
    """按名取 profile，未知名 fallback 到 custom。"""
    return PROFILES.get(name, PROFILES["custom"]).copy()
