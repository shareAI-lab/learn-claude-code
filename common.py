"""
common.py — shared foundation for every sNN lesson from s02 onward.

Each lesson's code.py imports its boilerplate and base tools from here, so the
lesson file only shows the NEW mechanism being taught (issue #349).

First-appearance rule: a concept is introduced INLINE in its origin lesson,
then abstracted into a shared module for later lessons. So s01 inlines
``init_env`` + ``run_repl`` (it introduces them); s02+ import them from here.
This file's ``init_env`` / ``run_repl`` mirror s01 — keep them in sync.
``make_base_tools`` mirrors the tool implementations s02 teaches inline.

What lives here:

  - init_env():            readline + .env + Anthropic client + MODEL_ID + WORKDIR
  - make_base_tools(wd):   safe_path / run_bash / run_read / run_write / run_edit /
                           run_glob as closures bound to a workdir (same signatures
                           the lessons always used)
  - BASE_TOOLS:            the 5 base tool schemas (bash/read/write/edit/glob)
  - select_tools(names):   pick a subset of BASE_TOOLS by name
  - run_repl(...):         the standard CLI REPL used by every lesson's __main__

Notes:
  - run_bash uses the utf-8-safe version (from s02) so non-ASCII output works on
    Windows; the dangerous-command check is NOT here (s01 teaches it inline, s03+
    handle it via permission/hooks).
  - Lessons that modify a base tool signature (s13-s16 add run_in_background,
    s18-s19 add cwd) re-define it locally after import and delegate to the base.
"""

import os
import subprocess
from pathlib import Path

# ── readline: UTF-8 backspace fix for macOS libedit; harmless elsewhere ──
try:
    import readline
    readline.parse_and_bind("set bind-tty-special-chars off")
    readline.parse_and_bind("set input-meta on")
    readline.parse_and_bind("set output-meta on")
    readline.parse_and_bind("set convert-meta off")
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv


# ═══════════════════════════════════════════════════════════
#  Environment / client init
# ═══════════════════════════════════════════════════════════

def init_env():
    """Load .env, build the Anthropic client, return (client, MODEL, WORKDIR).

    Replaces the ~15 lines of boilerplate that used to open every lesson.
    """
    load_dotenv(override=True)
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
    MODEL = os.environ["MODEL_ID"]
    WORKDIR = Path.cwd()
    return client, MODEL, WORKDIR


# ═══════════════════════════════════════════════════════════
#  Base tool implementations (canonical s02 versions, as closures over workdir)
# ═══════════════════════════════════════════════════════════

def make_base_tools(workdir: Path):
    """Return (safe_path, run_bash, run_read, run_write, run_edit, run_glob, BASE_TOOLS)
    all bound to *workdir*.

    The closures keep the original signatures (e.g. ``run_bash(command)``) so lesson
    code reads exactly as before — the workdir is captured, not passed in.
    """
    def safe_path(p: str) -> Path:
        path = (workdir / p).resolve()
        if not path.is_relative_to(workdir):
            raise ValueError(f"Path escapes workspace: {p}")
        return path

    def run_bash(command: str) -> str:
        try:
            r = subprocess.run(command, shell=True, cwd=workdir,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (120s)"
        except (FileNotFoundError, OSError) as e:
            return f"Error: {e}"

    def run_read(path: str, limit: int | None = None) -> str:
        try:
            lines = safe_path(path).read_text().splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def run_write(path: str, content: str) -> str:
        try:
            file_path = safe_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error: {e}"

    def run_edit(path: str, old_text: str, new_text: str) -> str:
        try:
            file_path = safe_path(path)
            text = file_path.read_text()
            if old_text not in text:
                return f"Error: text not found in {path}"
            file_path.write_text(text.replace(old_text, new_text, 1))
            return f"Edited {path}"
        except Exception as e:
            return f"Error: {e}"

    def run_glob(pattern: str) -> str:
        import glob as g
        try:
            results = []
            for match in g.glob(pattern, root_dir=workdir):
                if (workdir / match).resolve().is_relative_to(workdir):
                    results.append(match)
            return "\n".join(results) if results else "(no matches)"
        except Exception as e:
            return f"Error: {e}"

    return safe_path, run_bash, run_read, run_write, run_edit, run_glob


# ═══════════════════════════════════════════════════════════
#  Base tool schemas
# ═══════════════════════════════════════════════════════════

BASE_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "limit": {"type": "integer"}},
                      "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "old_text": {"type": "string"},
                                     "new_text": {"type": "string"}},
                      "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object",
                      "properties": {"pattern": {"type": "string"}},
                      "required": ["pattern"]}},
]

_TOOLS_BY_NAME = {t["name"]: t for t in BASE_TOOLS}


def select_tools(names):
    """Return the BASE_TOOLS entries matching *names*, in the order given."""
    return [_TOOLS_BY_NAME[n] for n in names]


# ═══════════════════════════════════════════════════════════
#  Standard REPL (replaces the __main__ block every lesson duplicated)
# ═══════════════════════════════════════════════════════════

def run_repl(prompt: str, banner: str, turn, context=None, on_submit=None,
             hint: str = "输入问题，回车发送。输入 q 退出。\n"):
    """Run the lesson's CLI REPL.

    Args:
        prompt:   the input() prompt, e.g. "\\033[36ms02 >> \\033[0m".
        banner:   title line printed once at startup.
        turn:     callable(history, context) -> optional new context. Called each
                  user turn to run the agent. Return None to keep context unchanged.
        context:  optional initial context passed to turn().
        on_submit: optional callable(query) invoked before the user message is
                  appended (s04-s07 use it to fire UserPromptSubmit hooks).
        hint:     instruction line printed after the banner.
    """
    print(banner)
    print(hint)
    history = []
    while True:
        try:
            query = input(prompt)
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if on_submit is not None:
            on_submit(query)
        history.append({"role": "user", "content": query})
        new_ctx = turn(history, context)
        if new_ctx is not None:
            context = new_ctx
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()
