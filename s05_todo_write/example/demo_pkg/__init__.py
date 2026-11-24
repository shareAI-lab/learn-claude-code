"""A tiny, dependency-free helper package for the ``s05_todo_write`` example.

The package groups small utilities for normalising, slugifying and summarising
todo items. The public names are re-exported here, so callers can use either
style::

    from demo_pkg import normalize_title, count_by_status
    from demo_pkg.utils import normalize_title, count_by_status

Importing the package has no side effects beyond defining these names.
"""

from .utils import (
    ELLIPSIS,
    STATUS_MARKERS,
    VALID_STATUSES,
    count_by_status,
    normalize_title,
    render_progress,
    slugify,
    truncate,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ELLIPSIS",
    "STATUS_MARKERS",
    "VALID_STATUSES",
    "count_by_status",
    "normalize_title",
    "render_progress",
    "slugify",
    "truncate",
]
