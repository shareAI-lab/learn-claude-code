#!/usr/bin/env python3
"""
Create Bootstrap Task for First-Time Setup.

Creates a guided task to help users fill in project guidelines
after initializing Trellis for the first time.

Usage:
    python3 create_bootstrap.py [project-type]

Arguments:
    project-type: frontend | backend | fullstack (default: fullstack)

Prerequisites:
    - .trellis/.developer must exist (run init_developer.py first)

Creates:
    .trellis/tasks/00-bootstrap-guidelines/
        - task.json    # Task metadata
        - prd.md       # Task description and guidance
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from common.paths import (
    DIR_WORKFLOW,
    DIR_SCRIPTS,
    DIR_TASKS,
    get_repo_root,
    get_developer,
    get_tasks_dir,
    set_current_task,
)


# =============================================================================
# Constants
# =============================================================================

TASK_NAME = "00-bootstrap-guidelines"


# =============================================================================
# PRD Content
# =============================================================================

def write_prd_header() -> str:
    """Write PRD header section."""
    return """# Bootstrap: Fill Project Development Guidelines

## Purpose

Welcome to Trellis! This is your first task.

AI agents use `.trellis/spec/` to understand YOUR project's coding conventions.
**Empty templates = AI writes generic code that doesn't match your project style.**

Filling these guidelines is a one-time setup that pays off for every future AI session.

---

## Your Task

Fill in the guideline files based on your **existing codebase**.
"""


def write_prd_backend_section() -> str:
    """Write PRD backend section."""
    return """

### Backend Guidelines

| File | What to Document |
|------|------------------|
| `.trellis/spec/backend/directory-structure.md` | Where different file types go (routes, services, utils) |
| `.trellis/spec/backend/database-guidelines.md` | ORM, migrations, query patterns, naming conventions |
| `.trellis/spec/backend/error-handling.md` | How errors are caught, logged, and returned |
| `.trellis/spec/backend/logging-guidelines.md` | Log levels, format, what to log |
| `.trellis/spec/backend/quality-guidelines.md` | Code review standards, testing requirements |
"""


def write_prd_frontend_section() -> str:
    """Write PRD frontend section."""
    return """

### Frontend Guidelines

| File | What to Document |
|------|------------------|
| `.trellis/spec/frontend/directory-structure.md` | Component/page/hook organization |
| `.trellis/spec/frontend/component-guidelines.md` | Component patterns, props conventions |
| `.trellis/spec/frontend/hook-guidelines.md` | Custom hook naming, patterns |
| `.trellis/spec/frontend/state-management.md` | State library, patterns, what goes where |
| `.trellis/spec/frontend/type-safety.md` | TypeScript conventions, type organization |
| `.trellis/spec/frontend/quality-guidelines.md` | Linting, testing, accessibility |
"""


def write_prd_footer() -> str:
    """Write PRD footer section."""
    return """

### Thinking Guides (Optional)

The `.trellis/spec/guides/` directory contains thinking guides that are already
filled with general best practices. You can customize them for your project if needed.

---

## How to Fill Guidelines

### Principle: Document Reality, Not Ideals

Write what your codebase **actually does**, not what you wish it did.
AI needs to match existing patterns, not introduce new ones.

### Steps

1. **Look at existing code** - Find 2-3 examples of each pattern
2. **Document the pattern** - Describe what you see
3. **Include file paths** - Reference real files as examples
4. **List anti-patterns** - What does your team avoid?

---

## Tips for Using AI

Ask AI to help analyze your codebase:

- "Look at my codebase and document the patterns you see"
- "Analyze my code structure and summarize the conventions"
- "Find error handling patterns and document them"

The AI will read your code and help you document it.

---

## Completion Checklist

- [ ] Guidelines filled for your project type
- [ ] At least 2-3 real code examples in each guideline
- [ ] Anti-patterns documented

When done:

```bash
python3 ./.trellis/scripts/task.py finish
python3 ./.trellis/scripts/task.py archive 00-bootstrap-guidelines
```

---

## Why This Matters

After completing this task:

1. AI will write code that matches your project style
2. Relevant `/trellis:before-*-dev` commands will inject real context
3. `/trellis:check-*` commands will validate against your actual standards
4. Future developers (human or AI) will onboard faster
"""


def write_prd(task_dir: Path, project_type: str) -> None:
    """Write prd.md file."""
    content = write_prd_header()

    if project_type == "frontend":
        content += write_prd_frontend_section()
    elif project_type == "backend":
        content += write_prd_backend_section()
    else:  # fullstack
        content += write_prd_backend_section()
        content += write_prd_frontend_section()

    content += write_prd_footer()

    prd_file = task_dir / "prd.md"
    prd_file.write_text(content, encoding="utf-8")


# =============================================================================
# Task JSON
# =============================================================================

def write_task_json(task_dir: Path, developer: str, project_type: str) -> None:
    """Write task.json file."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Generate subtasks and related files based on project type
    if project_type == "frontend":
        subtasks = [
            {"name": "Fill frontend guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [".trellis/spec/frontend/"]
    elif project_type == "backend":
        subtasks = [
            {"name": "Fill backend guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [".trellis/spec/backend/"]
    else:  # fullstack
        subtasks = [
            {"name": "Fill backend guidelines", "status": "pending"},
            {"name": "Fill frontend guidelines", "status": "pending"},
            {"name": "Add code examples", "status": "pending"},
        ]
        related_files = [".trellis/spec/backend/", ".trellis/spec/frontend/"]

    task_data = {
        "id": TASK_NAME,
        "name": "Bootstrap Guidelines",
        "description": "Fill in project development guidelines for AI agents",
        "status": "in_progress",
        "dev_type": "docs",
        "priority": "P1",
        "creator": developer,
        "assignee": developer,
        "createdAt": today,
        "completedAt": None,
        "commit": None,
        "subtasks": subtasks,
        "children": [],
        "parent": None,
        "relatedFiles": related_files,
        "notes": f"First-time setup task created by trellis init ({project_type} project)",
        "meta": {},
    }

    task_json = task_dir / "task.json"
    task_json.write_text(json.dumps(task_data, indent=2, ensure_ascii=False), encoding="utf-8")


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    """Main entry point."""
    # Parse project type argument
    project_type = "fullstack"
    if len(sys.argv) > 1:
        project_type = sys.argv[1]

    # Validate project type
    if project_type not in ("frontend", "backend", "fullstack"):
        print(f"Unknown project type: {project_type}, defaulting to fullstack")
        project_type = "fullstack"

    repo_root = get_repo_root()
    developer = get_developer(repo_root)

    # Check developer initialized
    if not developer:
        print("Error: Developer not initialized")
        print(f"Run: python3 ./{DIR_WORKFLOW}/{DIR_SCRIPTS}/init_developer.py <your-name>")
        return 1

    tasks_dir = get_tasks_dir(repo_root)
    task_dir = tasks_dir / TASK_NAME
    relative_path = f"{DIR_WORKFLOW}/{DIR_TASKS}/{TASK_NAME}"

    # Check if already exists
    if task_dir.exists():
        print(f"Bootstrap task already exists: {relative_path}")
        return 0

    # Create task directory
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    write_task_json(task_dir, developer, project_type)
    write_prd(task_dir, project_type)

    # Set as current task
    set_current_task(relative_path, repo_root)

    # Silent output - init command handles user-facing messages
    # Only output the task path for programmatic use
    print(relative_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
