"""Backward-compatible imports for the frontend JSONL bridge.

New code should import runtime event production from
`coding_deepgent.frontend.producer` and transport behavior from
`coding_deepgent.frontend.adapters.jsonl`.
"""

from .adapters.jsonl import run_jsonl_bridge, run_stdio_bridge
from .producer import (
    BridgeSession,
    EventEmitter,
    PromptRunner,
    PromptRunResult,
    _run_streaming_prompt,
    build_default_prompt_runner,
    build_fake_prompt_runner,
)

__all__ = [
    "BridgeSession",
    "EventEmitter",
    "PromptRunner",
    "PromptRunResult",
    "_run_streaming_prompt",
    "build_default_prompt_runner",
    "build_fake_prompt_runner",
    "run_jsonl_bridge",
    "run_stdio_bridge",
]

