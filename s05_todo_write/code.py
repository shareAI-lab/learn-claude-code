#!/usr/bin/env python3
"""
s05_todo_write.py - TodoWrite

The model tracks its progress through a TodoManager. After three rounds
without an update, the harness adds a reminder alongside the tool results.

    +----------+      +-------+      +--------------+
    |   User   | ---> |  LLM  | ---> | Tools        |
    |  prompt  |      |       |      | + todo_write |
    +----------+      +---^---+      +------+-------+
                          |                 | update
                          |          +------v----------+
                          |          | TodoManager     |
                          |          | [ ] pending     |
                          |          | [>] in progress |
                          |          | [x] completed   |
                          |          +------+----------+
                          | tool_result     |
                          +-----------------+

              rounds_since_todo >= 3 -> add <reminder>
"""

import ast
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# s05 change: SYSTEM prompt adds planning guidance
ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, not Unix "
    "Bash or PowerShell syntax, and prefer dedicated file tools for file operations"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. Environment: {ENVIRONMENT_PROMPT}. "
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go."
)


# -- Tool implementations from s02-s04 --

def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, errors="replace", timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = (WORKDIR / path).resolve().read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        file_path = (WORKDIR / path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = (WORKDIR / path).resolve()
        text = file_path.read_text(encoding="utf-8")
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

def run_glob(pattern: str) -> str:
    import glob as g
    try:
        matches = sorted({
            match for match in g.glob(
                pattern, root_dir=WORKDIR, recursive=True)
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR)
        })
        shown = matches[:200]
        if len(matches) > 200:
            shown.append("... (more matches omitted; narrow the pattern)")
        return "\n".join(shown) if shown else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


# -- New in s05: structured state the model updates --

class TodoManager:
    def __init__(self):
        self.items: list[dict] = []

    def update(self, todos: list | str) -> str:
        if isinstance(todos, str):
            try:
                todos = json.loads(todos)
            except json.JSONDecodeError:
                try:
                    todos = ast.literal_eval(todos)
                except (SyntaxError, ValueError) as e:
                    raise ValueError("todos must be a list or JSON array string") from e

        if not isinstance(todos, list):
            raise ValueError("todos must be a list")
        if len(todos) > 20:
            raise ValueError("Max 20 todos allowed")

        validated = []
        in_progress_count = 0
        for index, todo in enumerate(todos):
            if not isinstance(todo, dict):
                raise ValueError(f"todos[{index}] must be an object")

            content = str(todo.get("content", "")).strip()
            status = str(todo.get("status", "pending")).lower()
            if not content:
                raise ValueError(f"todos[{index}] requires content")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"todos[{index}] has invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"content": content, "status": status})

        if in_progress_count > 1:
            raise ValueError("Only one todo can be in_progress at a time")

        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."

        lines = []
        for todo in self.items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[x]",
            }[todo["status"]]
            lines.append(f"{marker} {todo['content']}")

        done = sum(todo["status"] == "completed" for todo in self.items)
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


def run_todo_write(todos: list | str) -> str:
    try:
        output = TODO.update(todos)
    except ValueError as e:
        return f"Error: {e}"
    print(f"\n\033[33m## Current Tasks\033[0m\n{output}")
    return output

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern; ** matches recursively.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    # s05: new tool
    {"name": "todo_write", "description": "Create and manage a task list for your current coding session.",
     "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "maxItems": 20, "items": {"type": "object", "properties": {"content": {"type": "string", "minLength": 1}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]}},
]

TOOL_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob, "todo_write": run_todo_write,
}


# -- Hook system from s04 --

HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}

def register_hook(event: str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None

# -- Hardened permission gate: parse into shell words before matching --
# The previous gate matched raw substrings, so quote splicing (`r''m`),
# `${IFS}`, `$'...'`, backslash escapes, `find -delete`, and pipe-to-shell all
# slipped past the deny list and the destructive-command rule and executed for
# real. The helpers below tokenize the command into shell words and inspect the
# resolved argv segments, so those obfuscations are normalised before matching.

DENY_LIST = ["sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda"]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]

_OPERATORS = {";", ";;", "&&", "||", "|", "&", "(", ")", "<", ">", ">>", "<<", "<&", ">&"}
_REDIRECT_OPERATORS = {">", ">>", ">&", "<&"}
_INLINE_FLAGS = {"-c", "--eval", "-command", "/c"}
_SHELL_INTERPRETERS = {
    "sh", "bash", "dash", "zsh", "ksh", "csh", "tcsh", "fish",
    "python", "python2", "python3", "perl", "ruby", "node", "nodejs",
    "php", "lua", "osascript", "powershell", "pwsh", "cmd",
}
_DELEGATING_COMMANDS = {"xargs", "env", "nice", "nohup", "time", "command", "exec", "stdbuf", "setsid"}
_DESTRUCTIVE_COMMANDS = {"rm", "del", "rmdir", "shred", "unlink", "truncate", "dd", "tee"}
_SENSITIVE_PREFIXES = ("/etc/", "/dev/", "/boot/", "/sys/", "/proc/", "/usr/", "/bin/", "/sbin/", "/lib/")


def _normalize_shell_command(command: str) -> str:
    """Collapse the shell-level obfuscations a substring gate misses."""
    text = command.replace("${IFS}", " ").replace("$IFS", " ")
    text = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", r"\1", text)
    text = re.sub(r"\$'", "'", text)
    return re.sub(r"\$([A-Za-z_])", r"\1", text)


def _tokenize_shell_command(command: str) -> list:
    lexer = shlex.shlex(_normalize_shell_command(command), posix=True,
                        punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _command_segments(tokens: list):
    segments, current, redirects, piped = [], [], [], False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _REDIRECT_OPERATORS and index + 1 < len(tokens):
            redirects.append(tokens[index + 1])
            current.extend([token, tokens[index + 1]])
            index += 2
            continue
        if token in _OPERATORS:
            if current:
                segments.append((current, piped, redirects))
                current, redirects = [], []
            piped = token == "|"
        else:
            current.append(token)
        index += 1
    if current:
        segments.append((current, piped, redirects))
    return segments


def _argv_basename(word: str) -> str:
    return os.path.basename(word).lower()


def _is_sensitive_path(path: str) -> bool:
    stripped = path.strip("\"'")
    return stripped == "/" or stripped.startswith(_SENSITIVE_PREFIXES)


def _destructive_argv(argv: list, depth: int = 0) -> bool:
    args = [arg for arg in argv if arg not in _OPERATORS]
    if not args or depth > 6:
        return False
    name = _argv_basename(args[0])
    rest = args[1:]
    if name in DENY_LIST or name.startswith("mkfs"):
        return True
    if name in _DESTRUCTIVE_COMMANDS:
        return True
    if name == "dd":
        return any(arg.startswith(("if=", "of=")) for arg in rest)
    if name == "find":
        return any(arg in ("-delete", "-exec", "-execdir") for arg in rest)
    if name in _SHELL_INTERPRETERS:
        for position, arg in enumerate(rest):
            if arg in _INLINE_FLAGS and position + 1 < len(rest):
                return _destructive_argv(
                    _tokenize_shell_command(rest[position + 1]), depth + 1) or True
        return True
    if name in _DELEGATING_COMMANDS:
        inner = [arg for arg in rest if not arg.startswith("-")]
        return _destructive_argv(inner, depth + 1) if inner else False
    return False


def check_deny_list(command: str) -> str | None:
    if not isinstance(command, str):
        return "Blocked: shell command must be a string"
    try:
        tokens = _tokenize_shell_command(command)
    except ValueError:
        return "Blocked: unparseable shell command"
    for argv, _piped, _redirects in _command_segments(tokens):
        args = [arg for arg in argv if arg not in _OPERATORS]
        if not args:
            continue
        name = _argv_basename(args[0])
        if name in DENY_LIST or name.startswith("mkfs"):
            return f"Blocked: '{name}' is on the deny list"
        if name in {"rm", "rmdir", "del", "shred", "truncate"} and any(
                arg.strip("\"'") == "/" for arg in args[1:]):
            return "Blocked: recursive delete of the filesystem root"
    return None


def contains_destructive_command(command: str) -> bool:
    if not isinstance(command, str):
        return False
    try:
        tokens = _tokenize_shell_command(command)
    except ValueError:
        return True  # unparseable quoting fails closed
    for argv, piped, redirects in _command_segments(tokens):
        if _destructive_argv(argv):
            return True
        if any(_is_sensitive_path(path) for path in redirects):
            return True
        if piped and argv and _argv_basename(argv[0]) in _SHELL_INTERPRETERS:
            return True
    return False



def permission_hook(block):
    """PreToolUse: s03 permission logic, registered as an s04 hook."""
    if block.name == "bash":
        command = block.input.get("command", "")
        reason = check_deny_list(command)
        if reason:
            print(f"\n\033[31m[blocked] {reason}\033[0m")
            return "Permission denied by deny list"
        if contains_destructive_command(command):
            print(f"\n\033[33m[permission] Potentially destructive command\033[0m")
            print(f"   Tool: {block.name}({block.input})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    if block.name in ("read_file", "write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            print(f"\n\033[33m[permission] Access outside workspace\033[0m")
            print(f"   Tool: {block.name}({block.input})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    return None

def log_hook(block):
    """PreToolUse: log every tool call."""
    args_preview = str(list(block.input.values())[:2])[:60]
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block, output):
    """PostToolUse: warn on large output."""
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] Large output from {block.name}: {len(str(output))} chars\033[0m")
    return None

def context_inject_hook(query: str):
    """UserPromptSubmit: log working directory."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None

def summary_hook(messages: list):
    """Stop: print tool call count."""
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)


# -- Agent loop with the reminder counter --

def agent_loop(messages: list):
    rounds_since_todo = 0
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [
            block for block in response.content if block.type == "tool_use"
        ]
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        results = []
        used_todo = False
        for block in tool_calls:
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                continue

            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"

            trigger_hooks("PostToolUse", block, output)

            if block.name == "todo_write":
                used_todo = True

            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": str(output)})

        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            results.append({"type": "text",
                            "text": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s05: TodoWrite - plan before execution")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            # \001/\002 tell Readline the ANSI escapes have zero display width.
            query = input("\001\033[36m\002s05 >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if not query.strip():
            continue
        if query.strip().lower() in ("q", "exit"):
            break
        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()
