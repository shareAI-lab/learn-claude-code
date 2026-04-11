"""Small shared helpers for the Deep Agents teaching track.

The chapter files stay runnable and readable, while this module keeps
repeated OpenAI-compatible model configuration and safe filesystem helpers in
one place. It intentionally does not instantiate a Deep Agents model at import
time, so tests can import pure helpers without an API key or network access.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

load_dotenv(override=True)

WORKDIR = Path.cwd()
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
OUTPUT_LIMIT = 50_000
DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def resolve_openai_model() -> str:
    """Return the model name for the OpenAI-interface Deep Agents track.

    `OPENAI_MODEL` is the canonical variable for this track.  `MODEL_ID` is
    only treated as a compatibility fallback when it does not look like the
    existing Anthropic default from `.env.example`; this avoids accidentally
    driving the OpenAI interface with `claude-*` names.
    """

    openai_model = os.getenv("OPENAI_MODEL", "").strip()
    if openai_model:
        return openai_model

    legacy_model = os.getenv("MODEL_ID", "").strip()
    if legacy_model and not legacy_model.lower().startswith("claude"):
        return legacy_model

    return DEFAULT_OPENAI_MODEL


def require_openai_api_key() -> None:
    """Fail with a teaching-oriented message before a live model call."""

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Set OPENAI_API_KEY before running the Deep Agents demos. "
            "OPENAI_BASE_URL is optional for OpenAI-compatible endpoints."
        )


def build_openai_chat_model(*, temperature: float = 0.0, timeout: int = 60):
    """Build ChatOpenAI lazily so imports/tests do not require credentials."""

    require_openai_api_key()
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": resolve_openai_model(),
        "temperature": temperature,
        "timeout": timeout,
    }
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def safe_path(path_str: str) -> Path:
    """Resolve a workspace-local path and reject traversal outside WORKDIR."""

    path = (WORKDIR / path_str).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path


def run_bash(command: str) -> str:
    """Run a bounded shell command in the teaching workspace."""

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
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:OUTPUT_LIMIT]
    except Exception as exc:
        return f"Error: {exc}"


def write_file(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        content = file_path.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as exc:
        return f"Error: {exc}"


def message_text(message: Any) -> str:
    """Extract printable text from Deep Agents BaseMessage or dict content."""

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
            else:
                text = (
                    getattr(block, "text", None)
                    or getattr(block, "content", None)
                )
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return ""


def latest_text(messages: Iterable[Any]) -> str:
    for message in reversed(list(messages)):
        text = message_text(message)
        if text:
            return text
    return ""
