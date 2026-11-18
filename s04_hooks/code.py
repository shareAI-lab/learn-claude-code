#!/usr/bin/env python3
"""
s04_hooks.py - Hooks

Hooks run callbacks at fixed points in the agent loop:

    User prompt
         |
         v
    UserPromptSubmit
         |
         v
    +----------+      +-------+      +------------+      +-------+
    | messages | ---> |  LLM  | ---> | PreToolUse | ---> | Tool  |
    +----------+      +---+---+      | permission |      +---+---+
         ^                | stop     | log        |          |
         |                v          +------------+          v
         |            Stop hook                         PostToolUse
         |                                               |
         +---------------- tool_result ------------------+
"""

import os
import re
import shlex
import subprocess
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
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

ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, not Unix "
    "Bash or PowerShell syntax, and prefer dedicated file tools for file operations"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. Environment: {ENVIRONMENT_PROMPT}. "
    "Use tools to solve tasks. Act, don't explain."
)


# -- From s02-s03: tool implementations --

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
        file_path = (WORKDIR / path).resolve()
        lines = file_path.read_text(encoding="utf-8").splitlines()
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
]

TOOL_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob,
}


# -- New in s04: hook system (s03 permission logic now uses hooks) --

HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}

def register_hook(event: str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:  # A hook result blocks this tool call.
            return result
    return None


# s03 permission check logic, now wrapped as a hook
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
    """PreToolUse: s03 check_permission() logic moved here."""
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

# UserPromptSubmit hook: log user input before it reaches the LLM
def context_inject_hook(query: str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None

# Stop hook: print summary when loop is about to exit
def summary_hook(messages: list):
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


# -- Agent loop: same structure as s03, but no hard-coded check --
# s03: if not check_permission(block): ...
# s04: if trigger_hooks("PreToolUse", block): ...

def agent_loop(messages: list):
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
        for block in tool_calls:
            # s04 change: hook replaces hard-coded check_permission()
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            trigger_hooks("PostToolUse", block, output)  # s04: post hook

            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s04: Hooks - extension logic on hooks, loop stays clean")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            # \001/\002 tell Readline the ANSI escapes have zero display width.
            query = input("\001\033[36m\002s04 >> \001\033[0m\002")
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
