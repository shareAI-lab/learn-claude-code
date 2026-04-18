#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent Pipeline Context Injection Hook

Core Design Philosophy:
- Dispatch becomes a pure dispatcher, only responsible for "calling subagents"
- Hook is responsible for injecting all context, subagent works autonomously with complete info
- Each agent has a dedicated jsonl file defining its context
- No resume needed, no segmentation, behavior controlled by code not prompt

Trigger: PreToolUse (before Task tool call)

Context Source: .trellis/.current-task points to task directory
- implement.jsonl - Implement agent dedicated context
- check.jsonl     - Check agent dedicated context
- debug.jsonl     - Debug agent dedicated context
- research.jsonl  - Research agent dedicated context (optional, usually not needed)
- cr.jsonl        - Code review dedicated context
- prd.md          - Requirements document
- info.md         - Technical design
- codex-review-output.txt - Code Review results
"""

# IMPORTANT: Suppress all warnings FIRST
import warnings
warnings.filterwarnings("ignore")

import json
import os
import sys
from pathlib import Path

# IMPORTANT: Force stdout to use UTF-8 on Windows
# This fixes UnicodeEncodeError when outputting non-ASCII characters
if sys.platform == "win32":
    import io as _io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    elif hasattr(sys.stdout, "detach"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# =============================================================================
# Path Constants (change here to rename directories)
# =============================================================================

DIR_WORKFLOW = ".trellis"
DIR_WORKSPACE = "workspace"
DIR_TASKS = "tasks"
DIR_SPEC = "spec"
FILE_CURRENT_TASK = ".current-task"
FILE_TASK_JSON = "task.json"

# Agents that don't update phase (can be called at any time)
AGENTS_NO_PHASE_UPDATE = {"debug", "research"}

# =============================================================================
# Subagent Constants (change here to rename subagent types)
# =============================================================================

AGENT_IMPLEMENT = "implement"
AGENT_CHECK = "check"
AGENT_DEBUG = "debug"
AGENT_RESEARCH = "research"

# Agents that require a task directory
AGENTS_REQUIRE_TASK = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_DEBUG)
# All supported agents
AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_DEBUG, AGENT_RESEARCH)


def find_repo_root(start_path: str) -> str | None:
    """
    Find git repo root from start_path upwards

    Returns:
        Repo root path, or None if not found
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_current_task(repo_root: str) -> str | None:
    """
    Read current task directory path from .trellis/.current-task

    Returns:
        Task directory relative path (relative to repo_root)
        None if not set
    """
    current_task_file = os.path.join(repo_root, DIR_WORKFLOW, FILE_CURRENT_TASK)
    if not os.path.exists(current_task_file):
        return None

    try:
        with open(current_task_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def update_current_phase(repo_root: str, task_dir: str, subagent_type: str) -> None:
    """
    Update current_phase in task.json based on subagent_type.

    This ensures phase tracking is always accurate, regardless of whether
    dispatch agent remembers to update it.

    Logic:
    - Read next_action array from task.json
    - Find the next phase whose action matches subagent_type
    - Only move forward, never backward
    - Some agents (debug, research) don't update phase
    """
    if subagent_type in AGENTS_NO_PHASE_UPDATE:
        return

    task_json_path = os.path.join(repo_root, task_dir, FILE_TASK_JSON)
    if not os.path.exists(task_json_path):
        return

    try:
        with open(task_json_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        current_phase = task_data.get("current_phase", 0)
        next_actions = task_data.get("next_action", [])

        # Map action names to subagent types
        # "implement" -> "implement", "check" -> "check", "finish" -> "check"
        action_to_agent = {
            "implement": "implement",
            "check": "check",
            "finish": "check",  # finish uses check agent
        }

        # Find the next phase that matches this subagent_type
        new_phase = None
        for action in next_actions:
            phase_num = action.get("phase", 0)
            action_name = action.get("action", "")
            expected_agent = action_to_agent.get(action_name)

            # Only consider phases after current_phase
            if phase_num > current_phase and expected_agent == subagent_type:
                new_phase = phase_num
                break

        if new_phase is not None:
            task_data["current_phase"] = new_phase

            with open(task_json_path, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception:
        # Don't fail the hook if phase update fails
        pass


def read_file_content(base_path: str, file_path: str) -> str | None:
    """Read file content, return None if file doesn't exist"""
    full_path = os.path.join(base_path, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def read_directory_contents(
    base_path: str, dir_path: str, max_files: int = 20
) -> list[tuple[str, str]]:
    """
    Read all .md files in a directory

    Args:
        base_path: Base path (usually repo_root)
        dir_path: Directory relative path
        max_files: Max files to read (prevent huge directories)

    Returns:
        [(file_path, content), ...]
    """
    full_path = os.path.join(base_path, dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []

    results = []
    try:
        # Only read .md files, sorted by filename
        md_files = sorted(
            [
                f
                for f in os.listdir(full_path)
                if f.endswith(".md") and os.path.isfile(os.path.join(full_path, f))
            ]
        )

        for filename in md_files[:max_files]:
            file_full_path = os.path.join(full_path, filename)
            relative_path = os.path.join(dir_path, filename)
            try:
                with open(file_full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append((relative_path, content))
            except Exception:
                continue
    except Exception:
        pass

    return results


def read_jsonl_entries(base_path: str, jsonl_path: str) -> list[tuple[str, str]]:
    """
    Read all file/directory contents referenced in jsonl file

    Schema:
        {"file": "path/to/file.md", "reason": "..."}
        {"file": "path/to/dir/", "type": "directory", "reason": "..."}

    Returns:
        [(path, content), ...]
    """
    full_path = os.path.join(base_path, jsonl_path)
    if not os.path.exists(full_path):
        return []

    results = []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    file_path = item.get("file") or item.get("path")
                    entry_type = item.get("type", "file")

                    if not file_path:
                        continue

                    if entry_type == "directory":
                        # Read all .md files in directory
                        dir_contents = read_directory_contents(base_path, file_path)
                        results.extend(dir_contents)
                    else:
                        # Read single file
                        content = read_file_content(base_path, file_path)
                        if content:
                            results.append((file_path, content))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return results


def get_agent_context(repo_root: str, task_dir: str, agent_type: str) -> str:
    """
    Get complete context for specified agent

    Prioritize agent-specific jsonl, fallback to spec.jsonl if not exists
    """
    context_parts = []

    # 1. Try agent-specific jsonl
    agent_jsonl = f"{task_dir}/{agent_type}.jsonl"
    agent_entries = read_jsonl_entries(repo_root, agent_jsonl)

    # 2. If agent-specific jsonl doesn't exist or empty, fallback to spec.jsonl
    if not agent_entries:
        agent_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")

    # 3. Add all files from jsonl
    for file_path, content in agent_entries:
        context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def get_implement_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Implement Agent

    Read order:
    1. All files in implement.jsonl (dev specs)
    2. prd.md (requirements)
    3. info.md (technical design)
    """
    context_parts = []

    # 1. Read implement.jsonl (or fallback to spec.jsonl)
    base_context = get_agent_context(repo_root, task_dir, "implement")
    if base_context:
        context_parts.append(base_context)

    # 2. Requirements document
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(f"=== {task_dir}/prd.md (Requirements) ===\n{prd_content}")

    # 3. Technical design
    info_content = read_file_content(repo_root, f"{task_dir}/info.md")
    if info_content:
        context_parts.append(
            f"=== {task_dir}/info.md (Technical Design) ===\n{info_content}"
        )

    return "\n\n".join(context_parts)


def get_check_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Check Agent

    Read order:
    1. All files in check.jsonl (check specs + dev specs)
    2. prd.md (for understanding task intent)
    """
    context_parts = []

    # 1. Read check.jsonl (or fallback to spec.jsonl + hardcoded check files)
    check_entries = read_jsonl_entries(repo_root, f"{task_dir}/check.jsonl")

    if check_entries:
        for file_path, content in check_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use hardcoded check files + spec.jsonl
        check_files = [
            (".claude/commands/trellis/finish-work.md", "Finish work checklist"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
            (".claude/commands/trellis/check-backend.md", "Backend check spec"),
            (".claude/commands/trellis/check-frontend.md", "Frontend check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

        # Add spec.jsonl
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

    # 2. Requirements document (for understanding task intent)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - for understanding intent) ===\n{prd_content}"
        )

    return "\n\n".join(context_parts)


def get_finish_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Finish phase (final check before PR)

    Read order:
    1. All files in finish.jsonl (if exists)
    2. Fallback to finish-work.md only (lightweight final check)
    3. update-spec.md (for active spec sync)
    4. prd.md (for verifying requirements are met)
    """
    context_parts = []

    # 1. Try finish.jsonl first
    finish_entries = read_jsonl_entries(repo_root, f"{task_dir}/finish.jsonl")

    if finish_entries:
        for file_path, content in finish_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: only finish-work.md (lightweight)
        finish_work = read_file_content(
            repo_root, ".claude/commands/trellis/finish-work.md"
        )
        if finish_work:
            context_parts.append(
                f"=== .claude/commands/trellis/finish-work.md (Finish checklist) ===\n{finish_work}"
            )

    # 2. Spec update process (for active spec sync)
    update_spec = read_file_content(
        repo_root, ".claude/commands/trellis/update-spec.md"
    )
    if update_spec:
        context_parts.append(
            f"=== .claude/commands/trellis/update-spec.md (Spec update process) ===\n{update_spec}"
        )

    # 3. Requirements document (for verifying requirements are met)
    prd_content = read_file_content(repo_root, f"{task_dir}/prd.md")
    if prd_content:
        context_parts.append(
            f"=== {task_dir}/prd.md (Requirements - verify all met) ===\n{prd_content}"
        )

    return "\n\n".join(context_parts)


def get_debug_context(repo_root: str, task_dir: str) -> str:
    """
    Complete context for Debug Agent

    Read order:
    1. All files in debug.jsonl (specs needed for fixing)
    2. codex-review-output.txt (Codex Review results)
    """
    context_parts = []

    # 1. Read debug.jsonl (or fallback to spec.jsonl + hardcoded check files)
    debug_entries = read_jsonl_entries(repo_root, f"{task_dir}/debug.jsonl")

    if debug_entries:
        for file_path, content in debug_entries:
            context_parts.append(f"=== {file_path} ===\n{content}")
    else:
        # Fallback: use spec.jsonl + hardcoded check files
        spec_entries = read_jsonl_entries(repo_root, f"{task_dir}/spec.jsonl")
        for file_path, content in spec_entries:
            context_parts.append(f"=== {file_path} (Dev spec) ===\n{content}")

        check_files = [
            (".claude/commands/trellis/check-backend.md", "Backend check spec"),
            (".claude/commands/trellis/check-frontend.md", "Frontend check spec"),
            (".claude/commands/trellis/check-cross-layer.md", "Cross-layer check spec"),
        ]
        for file_path, description in check_files:
            content = read_file_content(repo_root, file_path)
            if content:
                context_parts.append(f"=== {file_path} ({description}) ===\n{content}")

    # 2. Codex review output (if exists)
    codex_output = read_file_content(repo_root, f"{task_dir}/codex-review-output.txt")
    if codex_output:
        context_parts.append(
            f"=== {task_dir}/codex-review-output.txt (Codex Review Results) ===\n{codex_output}"
        )

    return "\n\n".join(context_parts)


def build_implement_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Implement"""
    return f"""# Implement Agent Task

You are the Implement Agent in the Multi-Agent Pipeline.

## Your Context

All the information you need has been prepared for you:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand specs** - All dev specs are injected above, understand them
2. **Understand requirements** - Read requirements document and technical design
3. **Implement feature** - Implement following specs and design
4. **Self-check** - Ensure code quality against check specs

## Important Constraints

- Do NOT execute git commit, only code modifications
- Follow all dev specs injected above
- Report list of modified/created files when done"""


def build_check_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Check"""
    return f"""# Check Agent Task

You are the Check Agent in the Multi-Agent Pipeline (code and cross-layer checker).

## Your Context

All check specs and dev specs you need:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Get changes** - Run `git diff --name-only` and `git diff` to get code changes
2. **Check against specs** - Check item by item against specs above
3. **Self-fix** - Fix issues directly, don't just report
4. **Run verification** - Run project's lint and typecheck commands

## Important Constraints

- Fix issues yourself, don't just report
- Must execute complete checklist in check specs
- Pay special attention to impact radius analysis (L1-L5)"""


def build_finish_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Finish (final check before PR)"""
    return f"""# Finish Agent Task

You are performing the final check before creating a PR.

## Your Context

Finish checklist and requirements:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Review changes** - Run `git diff --name-only` to see all changed files
2. **Verify requirements** - Check each requirement in prd.md is implemented
3. **Spec sync** - Analyze whether changes introduce new patterns, contracts, or conventions
   - If new pattern/convention found: read target spec file → update it → update index.md if needed
   - If infra/cross-layer change: follow the 7-section mandatory template from update-spec.md
   - If pure code fix with no new patterns: skip this step
4. **Run final checks** - Execute lint and typecheck
5. **Confirm ready** - Ensure code is ready for PR

## Important Constraints

- You MAY update spec files when gaps are detected (use update-spec.md as guide)
- MUST read the target spec file BEFORE editing (avoid duplicating existing content)
- Do NOT update specs for trivial changes (typos, formatting, obvious fixes)
- If critical CODE issues found, report them clearly (fix specs, not code)
- Verify all acceptance criteria in prd.md are met"""


def build_debug_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Debug"""
    return f"""# Debug Agent Task

You are the Debug Agent in the Multi-Agent Pipeline (issue fixer).

## Your Context

Dev specs and Codex Review results:

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand issues** - Analyze issues pointed out in Codex Review
2. **Locate code** - Find positions that need fixing
3. **Fix against specs** - Fix issues following dev specs
4. **Verify fixes** - Run typecheck to ensure no new issues

## Important Constraints

- Do NOT execute git commit, only code modifications
- Run typecheck after each fix to verify
- Report which issues were fixed and which files were modified"""


def get_research_context(repo_root: str, task_dir: str | None) -> str:
    """
    Context for Research Agent

    Research doesn't need much preset context, only needs:
    1. Project structure overview (where spec directories are)
    2. Optional research.jsonl (if there are specific search needs)
    """
    context_parts = []

    # 1. Project structure overview (uses constants for paths)
    spec_path = f"{DIR_WORKFLOW}/{DIR_SPEC}"
    project_structure = f"""## Project Spec Directory Structure

```
{spec_path}/
├── shared/      # Cross-project common specs (TypeScript, code quality, git)
├── frontend/    # Frontend standards
├── backend/     # Backend standards
└── guides/      # Thinking guides (cross-layer, code reuse, etc.)

{DIR_WORKFLOW}/big-question/  # Known issues and pitfalls
```

## Search Tips

- Spec files: `{spec_path}/**/*.md`
- Known issues: `{DIR_WORKFLOW}/big-question/`
- Code search: Use Glob and Grep tools
- Tech solutions: Use mcp__exa__web_search_exa or mcp__exa__get_code_context_exa"""

    context_parts.append(project_structure)

    # 2. If task directory exists, try reading research.jsonl (optional)
    if task_dir:
        research_entries = read_jsonl_entries(repo_root, f"{task_dir}/research.jsonl")
        if research_entries:
            context_parts.append(
                "\n## Additional Search Context (from research.jsonl)\n"
            )
            for file_path, content in research_entries:
                context_parts.append(f"=== {file_path} ===\n{content}")

    return "\n\n".join(context_parts)


def build_research_prompt(original_prompt: str, context: str) -> str:
    """Build complete prompt for Research"""
    return f"""# Research Agent Task

You are the Research Agent in the Multi-Agent Pipeline (search researcher).

## Core Principle

**You do one thing: find and explain information.**

You are a documenter, not a reviewer.

## Project Info

{context}

---

## Your Task

{original_prompt}

---

## Workflow

1. **Understand query** - Determine search type (internal/external) and scope
2. **Plan search** - List search steps for complex queries
3. **Execute search** - Execute multiple independent searches in parallel
4. **Organize results** - Output structured report

## Search Tools

| Tool | Purpose |
|------|---------|
| Glob | Search by filename pattern |
| Grep | Search by content |
| Read | Read file content |
| mcp__exa__web_search_exa | External web search |
| mcp__exa__get_code_context_exa | External code/doc search |

## Strict Boundaries

**Only allowed**: Describe what exists, where it is, how it works

**Forbidden** (unless explicitly asked):
- Suggest improvements
- Criticize implementation
- Recommend refactoring
- Modify any files

## Report Format

Provide structured search results including:
- List of files found (with paths)
- Code pattern analysis (if applicable)
- Related spec documents
- External references (if any)"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    if tool_name not in ("Task", "Agent"):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    original_prompt = tool_input.get("prompt", "")
    cwd = input_data.get("cwd", os.getcwd())

    # Only handle subagent types we care about
    if subagent_type not in AGENTS_ALL:
        sys.exit(0)

    # Find repo root
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # Get current task directory (research doesn't require it)
    task_dir = get_current_task(repo_root)

    # implement/check/debug need task directory
    if subagent_type in AGENTS_REQUIRE_TASK:
        if not task_dir:
            sys.exit(0)
        # Check if task directory exists
        task_dir_full = os.path.join(repo_root, task_dir)
        if not os.path.exists(task_dir_full):
            sys.exit(0)

        # Update current_phase in task.json (system-level enforcement)
        update_current_phase(repo_root, task_dir, subagent_type)

    # Check for [finish] marker in prompt (check agent with finish context)
    is_finish_phase = "[finish]" in original_prompt.lower()

    # Get context and build prompt based on subagent type
    if subagent_type == AGENT_IMPLEMENT:
        assert task_dir is not None  # validated above
        context = get_implement_context(repo_root, task_dir)
        new_prompt = build_implement_prompt(original_prompt, context)
    elif subagent_type == AGENT_CHECK:
        assert task_dir is not None  # validated above
        if is_finish_phase:
            # Finish phase: use finish context (lighter, focused on final verification)
            context = get_finish_context(repo_root, task_dir)
            new_prompt = build_finish_prompt(original_prompt, context)
        else:
            # Regular check phase: use check context (full specs for self-fix loop)
            context = get_check_context(repo_root, task_dir)
            new_prompt = build_check_prompt(original_prompt, context)
    elif subagent_type == AGENT_DEBUG:
        assert task_dir is not None  # validated above
        context = get_debug_context(repo_root, task_dir)
        new_prompt = build_debug_prompt(original_prompt, context)
    elif subagent_type == AGENT_RESEARCH:
        # Research can work without task directory
        context = get_research_context(repo_root, task_dir)
        new_prompt = build_research_prompt(original_prompt, context)
    else:
        sys.exit(0)

    if not context:
        sys.exit(0)

    # Return updated input with correct Claude Code PreToolUse format
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "prompt": new_prompt},
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
