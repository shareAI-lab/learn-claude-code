#!/usr/bin/env python3
"""Shared helpers for the Deep Agents s01-s05 teaching track.

This module intentionally stays tiny.  The chapter files should still be read
as the teaching surface; the shared code only avoids repeating the same safe
file tools and OpenAI-compatible model setup in every script.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(override=True)

WORKDIR = Path.cwd()
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
OUTPUT_LIMIT = 50_000
DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def deepagents_model_name() -> str:
    """Return the model name for the Deep Agents track.

    ``OPENAI_MODEL`` is the explicit Deep Agents-track variable.  ``MODEL_ID``
    is accepted only as a compatibility fallback when it does not look like an
    Anthropic model from the original ``agents/`` track.
    """

    openai_model = os.getenv("OPENAI_MODEL", "").strip()
    if openai_model:
        return openai_model

    legacy_model = os.getenv("MODEL_ID", "").strip()
    if legacy_model and not legacy_model.lower().startswith("claude"):
        return legacy_model

    return DEFAULT_OPENAI_MODEL


# Backward-compatible alias while the track rename propagates through tests and
# external notes.
langchain_model_name = deepagents_model_name


def build_openai_model(*, temperature: float = 0.0, timeout: int = 60):
    """Build a ChatOpenAI model lazily.

    Importing chapter modules should never require credentials.  The API key is
    checked only when a demo is actually run.
    """

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required to run the Deep Agents examples. "
            "Set OPENAI_MODEL to choose a model and OPENAI_BASE_URL for an "
            "OpenAI-compatible endpoint."
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": deepagents_model_name(),
        "temperature": temperature,
        "timeout": timeout,
    }
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def create_agent_runtime(system_prompt: str, tools: Iterable[Any]):
    """Create the stage-track agent with the current OpenAI-style model."""

    from langchain.agents import create_agent

    return create_agent(
        model=build_openai_model(),
        tools=list(tools),
        system_prompt=system_prompt,
    )


def safe_path(path_str: str) -> Path:
    """Resolve a path inside the current workspace, rejecting escapes."""

    path = (WORKDIR / path_str).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path


def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    if any(item in command for item in DANGEROUS_COMMANDS):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"

    output = (result.stdout + result.stderr).strip()
    return output[:OUTPUT_LIMIT] if output else "(no output)"


def read_file(path: str, limit: int | None = None) -> str:
    """Read a workspace file, optionally limiting returned lines."""

    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except Exception as exc:  # teaching tool: report errors as tool output
        return f"Error: {exc}"


def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""

    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text fragment in a workspace file."""

    try:
        file_path = safe_path(path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(
            content.replace(old_text, new_text, 1),
            encoding="utf-8",
        )
        return f"Edited {path}"
    except Exception as exc:
        return f"Error: {exc}"


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "")


def extract_text(content: Any) -> str:
    """Extract readable text from Deep Agents or dict message content."""

    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if (
                    block.get("type") in {"text", "output_text"}
                    and block.get("text")
                ):
                    texts.append(str(block["text"]))
                elif block.get("content"):
                    texts.append(str(block["content"]))
                continue
            text = getattr(block, "text", None)
            if text:
                texts.append(str(text))
        return "\n".join(texts).strip()

    text_attr = getattr(content, "text", None)
    if isinstance(text_attr, str):
        return text_attr.strip()
    if callable(text_attr):
        try:
            return str(text_attr()).strip()
        except TypeError:
            pass
    return str(content).strip()


def latest_assistant_text(result: Any) -> str:
    """Return the final assistant text from an agent/model result."""

    if isinstance(result, dict):
        messages = result.get("messages") or []
        for message in reversed(messages):
            role = (
                message.get("role")
                if isinstance(message, dict)
                else getattr(message, "type", "")
            )
            if role in {"assistant", "ai"}:
                text = extract_text(_message_content(message))
                if text:
                    return text
        if messages:
            return extract_text(_message_content(messages[-1]))
    return extract_text(_message_content(result))


def invoke_and_append(agent: Any, messages: list[dict[str, Any]]) -> str:
    """Invoke a Deep Agents agent and append only the final answer to history.

    Deep Agents owns the internal model -> tool -> tool-result loop. For the
    next CLI turn we keep a compact teaching history: the user's prompt plus
    the final assistant answer, while the original ``agents/`` files remain
    the place to inspect every raw provider block.
    """

    result = agent.invoke({"messages": messages})
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text
