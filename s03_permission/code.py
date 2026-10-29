#!/usr/bin/env python3
"""
s03_permission.py - Permission System

Three gates inserted before tool execution:

    Gate 1: Hard deny list (rm -rf /, sudo, ...)
    Gate 2: Rule matching (write outside workspace? destructive cmd?)
    Gate 3: User approval (pause and wait for confirmation)

    +----------+      +-------+      +--------------+      +---------------+
    |   User   | ---> |  LLM  | ---> | Permission   | ---> | Tool Dispatch |
    |  prompt  |      |       |      | 1. deny list |      | execute       |
    +----------+      +---+---+      | 2. rules     |      +-------+-------+
                          ^          | 3. approval  |              |
                          |          +------+-------+              |
                          |                 | deny                 |
                          |                 v                      v
                          |          +-------------------------------+
                          +----------+ tool_result: denied or output |
                                     +-------------------------------+

Only one line added to the agent loop:

    if not check_permission(block):
        continue

Builds on s02 (multi-tool). Usage:

    python s03_permission/code.py
    Needs: pip install anthropic python-dotenv + ANTHROPIC_API_KEY in .env
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
    "Use tools to solve tasks. Do not ask for approval yourself. "
    "For destructive operations, still request the tool call; "
    "the harness will approve or deny before execution."
)


# -- From s02: tool implementations --

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


# -- From s02 (unchanged): tool definitions and dispatch --

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


# -- New in s03: three-gate permission pipeline --

# Gate 1: Hard deny list - always forbidden
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



PERMISSION_RULES = [
    {"tools": ["read_file", "write_file", "edit_file"],
     "check": lambda args: not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR),
     "message": "Writing outside workspace"},
    {"tools": ["bash"],
     "check": lambda args: contains_destructive_command(args.get("command", "")),
     "message": "Potentially destructive command"},
]

def check_rules(tool_name: str, args: dict) -> str | None:
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None


# Gate 3: User approval - wait for confirmation after rule match
def ask_user(tool_name: str, args: dict, reason: str) -> str:
    print(f"\n\033[33m[permission] {reason}\033[0m")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"


# Pipeline: all three gates chained
def check_permission(block) -> bool:
    if block.name == "bash":
        reason = check_deny_list(block.input.get("command", ""))
        if reason:
            print(f"\n\033[31m[blocked] {reason}\033[0m")
            return False
    reason = check_rules(block.name, block.input)
    if reason:
        decision = ask_user(block.name, block.input, reason)
        if decision == "deny":
            return False
    return True


# -- Agent loop: same as s02, with check_permission() inserted --

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
            return

        results = []
        for block in tool_calls:
            print(f"\033[36m> {block.name}\033[0m")

            # s03 change: run through permission pipeline before executing
            if not check_permission(block):
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": "Permission denied."})
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"
            print(str(output)[:200])
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s03: Permission")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            # \001/\002 tell Readline the ANSI escapes have zero display width.
            query = input("\001\033[36m\002s03 >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if not query.strip():
            continue
        if query.strip().lower() in ("q", "exit"):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()
