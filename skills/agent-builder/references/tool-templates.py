"""
Tool Templates - Copy and customize these for your agent.

Each tool needs:
1. Definition (JSON schema for the model)
2. Implementation (Python function)
"""

from pathlib import Path
import subprocess

WORKDIR = Path.cwd()


# =============================================================================
# TOOL DEFINITIONS (for TOOLS list)
# =============================================================================

BASH_TOOL = {
    "name": "bash",
    "description": "Run a shell command. Use for: ls, find, grep, git, npm, python, etc.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute"
            }
        },
        "required": ["command"],
    },
}

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read file contents. Returns UTF-8 text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file"
            },
            "limit": {
                "type": "integer",
                "description": "Max lines to read (default: all)"
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "Write content to a file. Creates parent directories if needed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path for the file"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            },
        },
        "required": ["path", "content"],
    },
}

EDIT_FILE_TOOL = {
    "name": "edit_file",
    "description": "Replace exact text in a file. Use for surgical edits.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file"
            },
            "old_text": {
                "type": "string",
                "description": "Exact text to find (must match precisely)"
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text"
            },
        },
        "required": ["path", "old_text", "new_text"],
    },
}

TODO_WRITE_TOOL = {
    "name": "TodoWrite",
    "description": "Update the task list. Use to plan and track progress.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "Complete list of tasks",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Task description"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        "activeForm": {"type": "string", "description": "Present tense, e.g. 'Reading files'"},
                    },
                    "required": ["content", "status", "activeForm"],
                },
            }
        },
        "required": ["items"],
    },
}

TASK_TOOL_TEMPLATE = """
# Generate dynamically with agent types
TASK_TOOL = {
    "name": "Task",
    "description": f"Spawn a subagent for a focused subtask.\\n\\nAgent types:\\n{get_agent_descriptions()}",
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Short task name (3-5 words)"},
            "prompt": {"type": "string", "description": "Detailed instructions"},
            "agent_type": {"type": "string", "enum": list(AGENT_TYPES.keys())},
        },
        "required": ["description", "prompt", "agent_type"],
    },
}
"""


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def safe_path(p: str) -> Path:
    """
    Security: Ensure path stays within workspace.
    Prevents ../../../etc/passwd attacks.
    """
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    """
    Execute shell command with safety checks.

    Safety features:
    - Blocks obviously dangerous commands
    - 60 second timeout
    - Output truncated to 50KB
    """
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s)"
    except Exception as e:
        return f"Error: {e}"


def run_read_file(path: str, limit: int = None) -> str:
    """
    Read file contents with optional line limit.

    Features:
    - Safe path resolution
    - Optional line limit for large files
    - Output truncated to 50KB
    """
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()

        if limit and limit < len(lines):
            lines = lines[:limit]
            lines.append(f"... ({len(text.splitlines()) - limit} more lines)")

        return "\n".join(lines)[:50000]

    except Exception as e:
        return f"Error: {e}"


def run_write_file(path: str, content: str) -> str:
    """
    Write content to file, creating parent directories if needed.

    Features:
    - Safe path resolution
    - Auto-creates parent directories
    - Returns byte count for confirmation
    """
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"

    except Exception as e:
        return f"Error: {e}"


def run_edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Replace exact text in a file (surgical edit).

    Features:
    - Exact string matching (not regex)
    - Only replaces first occurrence (safety)
    - Clear error if text not found
    """
    try:
        fp = safe_path(path)
        content = fp.read_text()

        if old_text not in content:
            return f"Error: Text not found in {path}"

        new_content = content.replace(old_text, new_text, 1)
        fp.write_text(new_content)
        return f"Edited {path}"

    except Exception as e:
        return f"Error: {e}"


# =============================================================================
# DISPATCHER PATTERN
# =============================================================================

def execute_tool(name: str, args: dict) -> str:
    """
    Dispatch tool call to implementation.

    This pattern makes it easy to add new tools:
    1. Add definition to TOOLS list
    2. Add implementation function
    3. Add case to this dispatcher
    """
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read_file(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write_file(args["path"], args["content"])
    if name == "edit_file":
        return run_edit_file(args["path"], args["old_text"], args["new_text"])
    # Add more tools here...
    return f"Unknown tool: {name}"
