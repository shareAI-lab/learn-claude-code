"""
Tool definitions and implementations.

Tools follow the TOOL.md standard:
    tools/
    └── bash/
        └── TOOL.md    # YAML frontmatter + documentation

TOOL.md Format:
    ---
    name: bash
    description: Run shell command.
    parameters:
      command:
        type: string
        description: The shell command to execute
    required:
      - command
    ---
    # Documentation...

Definitions are loaded from YAML, implementations stay in Python.
"""

import re
import subprocess
from pathlib import Path

from .config import WORKDIR
from .todo import TODO
from .skills import SKILLS


# =============================================================================
# ToolLoader - Load tool definitions from TOOL.md files
# =============================================================================

class ToolLoader:
    """
    Loads tool definitions from TOOL.md files.

    Each tool is a FOLDER containing:
    - TOOL.md (required): YAML frontmatter with schema + markdown docs

    The YAML frontmatter defines the tool schema:
    - name: Tool name
    - description: What the tool does
    - parameters: Parameter definitions
    - required: Required parameter names
    """

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir
        self.tools = {}
        self.load_tools()

    def parse_tool_md(self, path: Path) -> dict:
        """
        Parse a TOOL.md file into tool definition.

        Returns dict with: name, description, parameters, required, body
        Returns None if file doesn't match format.
        """
        content = path.read_text()

        # Match YAML frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter, body = match.groups()

        # Parse YAML-like frontmatter
        metadata = self._parse_yaml(frontmatter)

        # Require name and description
        if "name" not in metadata or "description" not in metadata:
            return None

        return {
            "name": metadata["name"],
            "description": metadata["description"],
            "parameters": metadata.get("parameters", {}),
            "required": metadata.get("required", []),
            "body": body.strip(),
            "path": path,
        }

    def _parse_yaml(self, text: str) -> dict:
        """Simple YAML parser for tool frontmatter."""
        result = {}
        current_key = None
        current_indent = 0
        stack = [result]

        for line in text.split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Count leading spaces
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # Handle list items
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if isinstance(stack[-1], list):
                    stack[-1].append(value)
                continue

            # Handle key: value pairs
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                # Adjust stack based on indent
                while len(stack) > 1 and indent <= current_indent:
                    stack.pop()
                    current_indent -= 2

                if value:
                    # Simple key: value
                    stack[-1][key] = value
                else:
                    # Key with nested content - peek next line to determine type
                    # For now, assume dict unless we see a list marker
                    stack[-1][key] = {}
                    stack.append(stack[-1][key])
                    current_key = key
                    current_indent = indent

        # Post-process: convert 'required' to list if it's a dict
        if "required" in result and isinstance(result["required"], dict):
            result["required"] = list(result["required"].keys())

        # Handle parameters with nested structure
        if "parameters" in result:
            params = result["parameters"]
            for param_name, param_def in list(params.items()):
                if isinstance(param_def, str):
                    # Simple type definition
                    params[param_name] = {"type": param_def}
                elif isinstance(param_def, dict):
                    # Already a dict, ensure it has type
                    if "type" not in param_def:
                        param_def["type"] = "string"

        return result

    def load_tools(self):
        """Scan tools directory and load all valid TOOL.md files."""
        if not self.tools_dir.exists():
            return

        for tool_dir in self.tools_dir.iterdir():
            if not tool_dir.is_dir():
                continue

            tool_md = tool_dir / "TOOL.md"
            if not tool_md.exists():
                continue

            tool = self.parse_tool_md(tool_md)
            if tool:
                self.tools[tool["name"]] = tool

    def get_tool_schema(self, name: str) -> dict:
        """
        Convert tool definition to OpenAI tool schema format.

        Returns:
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        if name not in self.tools:
            return None

        tool = self.tools[name]

        # Build parameters schema
        properties = {}
        for param_name, param_def in tool["parameters"].items():
            prop = {"type": param_def.get("type", "string")}
            if "description" in param_def:
                prop["description"] = param_def["description"]
            if "enum" in param_def:
                prop["enum"] = param_def["enum"]
            if "items" in param_def:
                prop["items"] = param_def["items"]
            properties[param_name] = prop

        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": tool["required"],
                },
            },
        }

    def get_all_schemas(self) -> list:
        """Get OpenAI schemas for all loaded tools."""
        return [self.get_tool_schema(name) for name in self.tools]

    def list_tools(self) -> list:
        """Return list of available tool names."""
        return list(self.tools.keys())


# =============================================================================
# Tool Definitions (fallback if TOOL.md not found)
# =============================================================================

# These are used as fallbacks and for tools with complex schemas
# that are hard to express in simple YAML

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run shell command.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}

READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read file contents.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write to file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"],
        },
    },
}

EDIT_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Replace text in file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}

TODO_WRITE_TOOL = {
    "type": "function",
    "function": {
        "name": "TodoWrite",
        "description": "Update task list.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"]
                            },
                            "activeForm": {"type": "string"},
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                }
            },
            "required": ["items"],
        },
    },
}

SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "Skill",
        "description": f"""Load a skill to gain specialized knowledge for a task.

Available skills:
{SKILLS.get_descriptions()}

When to use:
- IMMEDIATELY when user task matches a skill description
- Before attempting domain-specific work (PDF, MCP, etc.)

The skill content will be injected into the conversation, giving you
detailed instructions and access to resources.""",
        "parameters": {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "Name of the skill to load"
                }
            },
            "required": ["skill"],
        },
    },
}


# =============================================================================
# Initialize Tool Loader
# =============================================================================

TOOLS_DIR = WORKDIR / "tools"
TOOL_LOADER = ToolLoader(TOOLS_DIR)

# Base tools - use loaded schemas or fallbacks
BASE_TOOLS = [
    TOOL_LOADER.get_tool_schema("bash") or BASH_TOOL,
    TOOL_LOADER.get_tool_schema("read_file") or READ_FILE_TOOL,
    TOOL_LOADER.get_tool_schema("write_file") or WRITE_FILE_TOOL,
    TOOL_LOADER.get_tool_schema("edit_file") or EDIT_FILE_TOOL,
    TOOL_LOADER.get_tool_schema("TodoWrite") or TODO_WRITE_TOOL,
]


# =============================================================================
# Tool Implementations
# =============================================================================

def safe_path(p: str) -> Path:
    """Ensure path stays within workspace."""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(cmd: str) -> str:
    """Execute shell command."""
    if any(d in cmd for d in ["rm -rf /", "sudo", "shutdown"]):
        return "Error: Dangerous command"
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=60
        )
        return ((r.stdout + r.stderr).strip() or "(no output)")[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    """Read file contents."""
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit:
            lines = lines[:limit]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """Write content to file."""
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in file."""
    try:
        fp = safe_path(path)
        text = fp.read_text()
        if old_text not in text:
            return f"Error: Text not found in {path}"
        fp.write_text(text.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_todo(items: list) -> str:
    """Update the todo list."""
    try:
        return TODO.update(items)
    except Exception as e:
        return f"Error: {e}"


def run_skill(skill_name: str) -> str:
    """Load a skill and inject it into the conversation."""
    content = SKILLS.get_skill_content(skill_name)

    if content is None:
        available = ", ".join(SKILLS.list_skills()) or "none"
        return f"Error: Unknown skill '{skill_name}'. Available: {available}"

    return f"""<skill-loaded name="{skill_name}">
{content}
</skill-loaded>

Follow the instructions in the skill above to complete the user's task."""


# =============================================================================
# Tool Dispatcher
# =============================================================================

# Registry for dynamically registered tools (like Task)
_dynamic_tools = {}


def register_tool(name: str, handler):
    """Register a dynamic tool handler."""
    _dynamic_tools[name] = handler


def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool call to implementation."""
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write(args["path"], args["content"])
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    if name == "TodoWrite":
        return run_todo(args["items"])
    if name == "Skill":
        return run_skill(args["skill"])

    # Check dynamic tools (Task is registered by agents.py)
    if name in _dynamic_tools:
        return _dynamic_tools[name](args)

    return f"Unknown tool: {name}"


# Full tool list (Task tool added by agents.py)
TOOLS = BASE_TOOLS + [SKILL_TOOL]
