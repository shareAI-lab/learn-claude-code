#!/usr/bin/env python3
# Deep Agents track: resilience -- recover instead of crashing.
"""
s11_error_recovery.py - Error Recovery with Deep Agents

This chapter demonstrates three recovery ideas on top of the staged Deep Agents
track:
- compact and retry when history is too large
- back off and retry on transient model failures
- continue cleanly instead of crashing the whole session
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ExtendedModelResponse
from langgraph.types import Command
from langchain.messages import AIMessage
from langchain.tools import tool

try:
    from ._deepagents_gating import build_stage_agent
    from .common import WORKDIR, build_openai_model, extract_text, latest_assistant_text
    from ._common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file
except ImportError:
    from _deepagents_gating import build_stage_agent
    from common import WORKDIR, build_openai_model, extract_text, latest_assistant_text
    from _common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file

MAX_RECOVERY_ATTEMPTS = 3
BACKOFF_BASE_DELAY = 1.0
BACKOFF_MAX_DELAY = 30.0
TOKEN_THRESHOLD = 50_000
SYSTEM = f'You are a coding agent at {WORKDIR}. Recover cleanly from long context and transient errors.'


def estimate_tokens(messages: list[Any]) -> int:
    return len(json.dumps(messages, default=str)) // 4


def auto_compact(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conversation_text = json.dumps(messages, default=str)[:80_000]
    prompt = (
        'Summarize this conversation for continuity. Include task overview, files touched, '\
        'key decisions, and next steps. Be concise but concrete.\n\n' + conversation_text
    )
    response = build_openai_model().invoke(prompt)
    summary = latest_assistant_text(response).strip() or extract_text(getattr(response, 'content', ''))
    return [{
        'role': 'user',
        'content': (
            'This session continues from a previous conversation that was compacted.\n\n'
            f'{summary}\n\nContinue from where we left off without re-asking the user.'
        ),
    }]


def backoff_delay(attempt: int) -> float:
    delay = min(BACKOFF_BASE_DELAY * (2 ** attempt), BACKOFF_MAX_DELAY)
    return delay + random.uniform(0, 1)


class RetryMiddleware(AgentMiddleware):
    def __init__(self, max_retries: int = MAX_RECOVERY_ATTEMPTS):
        self.max_retries = max_retries

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return handler(request)
            except Exception as exc:  # transient transport/provider errors
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(backoff_delay(attempt))
        raise last_error or RuntimeError('Retry middleware exhausted without a captured error')


@tool
def bash(command: str) -> str:
    """Run a shell command in the workspace."""
    return raw_bash(command)

@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace."""
    return raw_read_file(path, limit)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""
    return raw_write_file(path, content)

@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a workspace file."""
    return raw_edit_file(path, old_text, new_text)

TOOLS = [bash, read_file, write_file, edit_file]


@dataclass
class RecoveryState:
    recovery_count: int = 0


def build_agent():
    return build_stage_agent(
        's11',
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        extra_middleware=[RetryMiddleware()],
    )


def agent_loop(messages: list[dict[str, Any]], state: RecoveryState) -> str:
    if estimate_tokens(messages) > TOKEN_THRESHOLD:
        messages[:] = auto_compact(messages)
    try:
        result = build_agent().invoke({"messages": messages})
    except Exception:
        state.recovery_count += 1
        if state.recovery_count > MAX_RECOVERY_ATTEMPTS:
            raise
        time.sleep(backoff_delay(state.recovery_count - 1))
        result = build_agent().invoke({"messages": messages})
    text = extract_text(result['messages'][-1].content)
    if text:
        messages.append({'role': 'assistant', 'content': text})
    return text


if __name__ == '__main__':
    history: list[dict[str, Any]] = []
    state = RecoveryState()
    while True:
        try:
            query = input('\033[36ms11-da >> \033[0m')
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ('q', 'exit', ''):
            break
        history.append({'role': 'user', 'content': query})
        try:
            print(agent_loop(history, state) or '(no response)')
        except RuntimeError as exc:
            print(f'Error: {exc}')
        print()
