from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

TRUNCATION_MARKER = "\n...[context payload truncated by coding-deepgent budget]"
DEFAULT_MAX_CHARS = 4000

ContextPayloadKind = Literal["memory", "todo", "todo_reminder"]
RenderableContextBlock = str | dict[str, object]


@dataclass(frozen=True, slots=True)
class ContextPayload:
    kind: ContextPayloadKind
    text: str
    source: str
    priority: int = 100

    def normalized(self) -> "ContextPayload":
        return ContextPayload(
            kind=self.kind,
            text=self.text.strip(),
            source=self.source.strip(),
            priority=self.priority,
        )


def _truncate_text(text: str, *, max_chars: int) -> str:
    if max_chars < len(TRUNCATION_MARKER) + 1:
        raise ValueError("max_chars must leave room for the truncation marker")
    if len(text) <= max_chars:
        return text
    keep = max_chars - len(TRUNCATION_MARKER)
    return text[:keep] + TRUNCATION_MARKER


def render_context_payloads(
    payloads: list[ContextPayload],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict[str, object]]:
    if not payloads:
        return []

    deduped: dict[tuple[str, str, str], ContextPayload] = {}
    for payload in payloads:
        normalized = payload.normalized()
        if not normalized.text or not normalized.source:
            continue
        key = (normalized.kind, normalized.source, normalized.text)
        previous = deduped.get(key)
        if previous is None or normalized.priority < previous.priority:
            deduped[key] = normalized

    ordered = sorted(
        deduped.values(),
        key=lambda item: (item.priority, item.kind, item.source, item.text),
    )

    rendered: list[dict[str, object]] = []
    remaining = max_chars
    for payload in ordered:
        if remaining <= 0:
            break
        text = _truncate_text(payload.text, max_chars=remaining)
        rendered.append({"type": "text", "text": text})
        remaining -= len(text)

    return rendered


def merge_system_message_content(
    current_blocks: Sequence[object],
    payloads: list[ContextPayload],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[RenderableContextBlock]:
    rendered_payloads = render_context_payloads(payloads, max_chars=max_chars)
    if not rendered_payloads:
        return _normalize_existing_blocks(current_blocks)
    return [*_normalize_existing_blocks(current_blocks), *rendered_payloads]


def _normalize_existing_blocks(
    current_blocks: Sequence[object],
) -> list[RenderableContextBlock]:
    normalized: list[RenderableContextBlock] = []
    for block in current_blocks:
        if isinstance(block, str):
            normalized.append(block)
        elif isinstance(block, dict):
            normalized.append(block)
    return normalized
