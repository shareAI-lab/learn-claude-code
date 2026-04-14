#!/usr/bin/env python3
"""
Initialize developer for workflow.

Usage:
    python3 init_developer.py <developer-name>

This creates:
    - .trellis/.developer file with developer info
    - .trellis/workspace/<name>/ directory structure
"""

from __future__ import annotations

import sys

from common.paths import (
    DIR_WORKFLOW,
    FILE_DEVELOPER,
    get_developer,
)
from common.developer import init_developer


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <developer-name>")
        print()
        print("Example:")
        print(f"  {sys.argv[0]} john")
        sys.exit(1)

    name = sys.argv[1]

    # Check if already initialized
    existing = get_developer()
    if existing:
        print(f"Developer already initialized: {existing}")
        print()
        print(f"To reinitialize, remove {DIR_WORKFLOW}/{FILE_DEVELOPER} first")
        sys.exit(0)

    if init_developer(name):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
