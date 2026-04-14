"""
Common utilities for Trellis workflow scripts.

This module provides shared functionality used by other Trellis scripts.
"""

import io
import sys

# =============================================================================
# Windows Encoding Fix (MUST be at top, before any other output)
# =============================================================================
# On Windows, stdout defaults to the system code page (often GBK/CP936).
# This causes UnicodeEncodeError when printing non-ASCII characters.
#
# Any script that imports from common will automatically get this fix.
# =============================================================================


def _configure_stream(stream: object) -> object:
    """Configure a stream for UTF-8 encoding on Windows."""
    # Try reconfigure() first (Python 3.7+, more reliable)
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        return stream
    # Fallback: detach and rewrap with TextIOWrapper
    elif hasattr(stream, "detach"):
        return io.TextIOWrapper(
            stream.detach(),  # type: ignore[union-attr]
            encoding="utf-8",
            errors="replace",
        )
    return stream


if sys.platform == "win32":
    sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
    sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
    sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


def configure_encoding() -> None:
    """
    Configure stdout/stderr/stdin for UTF-8 encoding on Windows.

    This is automatically called when importing from common,
    but can be called manually for scripts that don't import common.

    Safe to call multiple times.
    """
    global sys
    if sys.platform == "win32":
        sys.stdout = _configure_stream(sys.stdout)  # type: ignore[assignment]
        sys.stderr = _configure_stream(sys.stderr)  # type: ignore[assignment]
        sys.stdin = _configure_stream(sys.stdin)  # type: ignore[assignment]


from .paths import (
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    DIR_TASKS,
    DIR_ARCHIVE,
    DIR_SPEC,
    DIR_SCRIPTS,
    FILE_DEVELOPER,
    FILE_CURRENT_TASK,
    FILE_TASK_JSON,
    FILE_JOURNAL_PREFIX,
    get_repo_root,
    get_developer,
    check_developer,
    get_tasks_dir,
    get_workspace_dir,
    get_active_journal_file,
    count_lines,
    get_current_task,
    get_current_task_abs,
    set_current_task,
    clear_current_task,
    has_current_task,
    generate_task_date_prefix,
)
