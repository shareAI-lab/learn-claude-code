"""Dependency-free string helpers for the subagent example.

The functions here are deliberately small and side-effect free so they can be
unit tested in isolation. Nothing in this module touches the network, the
filesystem, or module-level mutable state. Only the standard library is used,
and no third-party package is required.
"""

import re

__all__ = [
    "slugify",
]

_ALNUM_RUN = re.compile(r"[a-z0-9]+")
"""Runs of ASCII letters and digits, used by :func:`slugify`."""


def slugify(text: str) -> str:
    """Turn ``text`` into a lowercase, hyphen-separated slug.

    Args:
        text: Raw text. Any characters other than ASCII letters and digits
            are treated as separators.

    Returns:
        A slug such as ``"inspect-the-repo"``. Runs of separators collapse
        into a single hyphen, and the result never starts or ends with one.
        The result is never empty, because an empty or whitespace-only
        ``text`` is rejected first.

    Raises:
        TypeError: If ``text`` is not a string.
        ValueError: If ``text`` is empty, contains only whitespace, or
            contains no ASCII letters or digits.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")

    normalized = " ".join(text.split())
    if not normalized:
        raise ValueError("text must not be empty")

    slug = "-".join(_ALNUM_RUN.findall(normalized.lower()))
    if not slug:
        raise ValueError(f"text {text!r} contains no letters or digits")
    return slug
