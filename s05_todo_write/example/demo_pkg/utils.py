"""Dependency-free helpers for shaping and summarising todo items.

The functions here are deliberately small and side-effect free so they can be
unit tested in isolation. Nothing in this module touches the network, the
filesystem, or module-level mutable state.
"""

import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "ELLIPSIS",
    "STATUS_MARKERS",
    "VALID_STATUSES",
    "count_by_status",
    "normalize_title",
    "render_progress",
    "slugify",
    "truncate",
]

VALID_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed")
"""Statuses accepted by :func:`count_by_status`."""

STATUS_MARKERS: dict[str, str] = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "completed": "[x]",
}
"""Progress-bar marker rendered for each status."""

ELLIPSIS: str = "..."
"""Suffix appended by :func:`truncate` when text is shortened."""

_ALNUM_RUN = re.compile(r"[a-z0-9]+")
"""Runs of ASCII letters and digits, used by :func:`slugify`."""


def normalize_title(title: str) -> str:
    """Collapse runs of whitespace and strip the ends of ``title``.

    Args:
        title: Raw todo text as typed by a user.

    Returns:
        The title with leading/trailing whitespace removed and every internal
        run of whitespace replaced by a single space.

    Raises:
        TypeError: If ``title`` is not a string.
        ValueError: If ``title`` is empty or contains only whitespace.
    """
    if not isinstance(title, str):
        raise TypeError(f"title must be a str, got {type(title).__name__}")

    normalized = " ".join(title.split())
    if not normalized:
        raise ValueError("title must not be empty")
    return normalized


def slugify(title: str) -> str:
    """Turn ``title`` into a lowercase, hyphen-separated slug.

    Args:
        title: Raw todo text. Any characters other than ASCII letters and
            digits are treated as separators.

    Returns:
        A slug such as ``"inspect-the-repo"``. The result is never empty,
        because an empty or punctuation-only ``title`` is rejected by
        :func:`normalize_title` first.

    Raises:
        TypeError: If ``title`` is not a string.
        ValueError: If ``title`` is empty or contains no ASCII letters/digits.
    """
    normalized = normalize_title(title).lower()

    slug = "-".join(_ALNUM_RUN.findall(normalized))
    if not slug:
        raise ValueError(f"title {title!r} contains no letters or digits")
    return slug


def truncate(text: str, limit: int) -> str:
    """Shorten ``text`` to at most ``limit`` characters.

    Args:
        text: The string to shorten.
        limit: Maximum length of the returned string, in characters. This
            counts the appended :data:`ELLIPSIS` when truncation happens.

    Returns:
        ``text`` unchanged when it already fits, otherwise its first
        ``limit - len(ELLIPSIS)`` characters followed by ``"..."``.

    Raises:
        TypeError: If ``text`` is not a string or ``limit`` is not an int.
        ValueError: If ``limit`` is smaller than ``len(ELLIPSIS)``.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError(f"limit must be an int, got {type(limit).__name__}")
    if limit < len(ELLIPSIS):
        raise ValueError(f"limit must be at least {len(ELLIPSIS)}, got {limit}")

    if len(text) <= limit:
        return text
    return text[: limit - len(ELLIPSIS)] + ELLIPSIS


def count_by_status(items: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Count todo ``items`` per status.

    Args:
        items: Todo mappings, each with a ``"status"`` key.

    Returns:
        A dict with one entry per :data:`VALID_STATUSES` member, in that order,
        including zeros for statuses that never occur. Callers can therefore
        index the result without ``KeyError``.

    Raises:
        TypeError: If an item is not a mapping or lacks a ``"status"`` key.
        ValueError: If an item carries a status outside :data:`VALID_STATUSES`.
    """
    counts: dict[str, int] = {status: 0 for status in VALID_STATUSES}

    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise TypeError(
                f"item {index} must be a mapping, got {type(item).__name__}"
            )
        if "status" not in item:
            raise TypeError(f'item {index} is missing the "status" key')

        status = item["status"]
        if status not in counts:
            raise ValueError(
                f"item {index} has invalid status {status!r}; "
                f"expected one of {VALID_STATUSES}"
            )
        counts[status] += 1

    return counts


def render_progress(items: Iterable[Mapping[str, Any]]) -> str:
    """Render ``items`` as a progress bar plus per-status counters.

    Args:
        items: Todo mappings, each with ``"content"`` and ``"status"`` keys.

    Returns:
        A single line such as ``"(1/2 completed) [x] done [ ] todo"``. The
        markers follow :data:`STATUS_MARKERS`.

    Raises:
        TypeError: If an item is not a mapping or is missing a required key.
        ValueError: If an item carries an invalid status.
    """
    item_list = list(items)
    counts = count_by_status(item_list)

    markers: list[str] = []
    for index, item in enumerate(item_list):
        if "content" not in item:
            raise TypeError(f'item {index} is missing the "content" key')
        marker = STATUS_MARKERS[item["status"]]
        markers.append(f"{marker} {item['content']}")

    total = len(item_list)
    summary = f"({counts['completed']}/{total} completed)"
    return " ".join([summary, *markers]) if markers else summary
