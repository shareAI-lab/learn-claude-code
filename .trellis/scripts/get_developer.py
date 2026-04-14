#!/usr/bin/env python3
"""
Get current developer name.

This is a wrapper that uses common/paths.py
"""

from __future__ import annotations

import sys

from common.paths import get_developer


def main() -> None:
    """CLI entry point."""
    developer = get_developer()
    if developer:
        print(developer)
    else:
        print("Developer not initialized", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
