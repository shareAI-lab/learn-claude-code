#!/usr/bin/env python3
# Harness: security classifier -- let the model judge its own commands.
"""
s14_security_classifier.py - Security Classifier

Regex patterns from s13 match shapes, not intent. rm -rf build/ and
rm -rf / look identical to a regex. The LLM can judge context.

    Command
       |
       v
    +--------------------+
    | Layer 1: Quick Scan|   regex patterns (zero cost)
    +--------+-----------+
             |
        matched? --yes--> deny/ask
             |
            no
             v
    +--------------------+
    | Layer 2: LLM Class |   ~10 tokens per call
    +--------+-----------+
             |
      safe / moderate / dangerous
             |
        allow / ask / deny

Key insight: "Regex sees patterns; the LLM sees intent."
"""

import os
import re
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


# -- Layer 1: regex quick-scan patterns --
DANGEROUS_PATTERNS = [
    (re.compile(r"rm\s+-rf\s+/(?!\w)"), "Root recursive delete"),
    (re.compile(r"sudo\s+"), "Elevated privileges"),
    (re.compile(r">\s*/etc/"), "Overwrite system config"),
    (re.compile(r"curl.*\|\s*(ba)?sh"), "Remote code execution"),
    (re.compile(r"wget.*\|\s*(ba)?sh"), "Remote code execution"),
    (re.compile(r"chmod\s+-R\s+777\s+/"), "Recursive 777"),
    (re.compile(r"dd\s+.*of=/dev/"), "Raw device write"),
    (re.compile(r"mkfs\."), "Filesystem format"),
    (re.compile(r":\(\)\{.*:\|:&\}"), "Fork bomb"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"), "System shutdown"),
    (re.compile(r"crontab\s+-r"), "Delete crontab"),
    (re.compile(r"git\s+push\s+--force"), "Force push"),
    (re.compile(r"git\s+reset\s+--hard"), "Hard reset"),
    (re.compile(r"npm\s+publish"), "Publish package"),
    (re.compile(r">\s*/dev/sd"), "Write to raw disk"),
]

SAFE_COMMANDS = {
    "ls", "cat", "pwd", "echo", "head", "tail", "wc", "sort",
    "grep", "find", "git", "which", "type", "file", "diff",
    "python", "python3", "node", "npm", "pip", "tree", "du",
    "stat", "date", "whoami", "hostname", "uname", "true", "false",
}

CLASSIFIER_PROMPT = """Classify this shell command's danger level.
Reply with EXACTLY one word: safe, moderate, or dangerous.

- safe: read-only or non-destructive (ls, cat, git status)
- moderate: writes files but recoverable (rm single file, pip install)
- dangerous: irreversible or system-wide (rm -rf /, sudo, force push)

Command: {command}
Context (last task): {context}"""


# -- SecurityClassifier --
class SecurityClassifier:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        # Note: s13 had an "edit" mode that rewrites commands (e.g. rm -rf -> rm -r).
        # s14 replaces this with LLM classification: the model judges intent instead
        # of mechanically rewriting patterns.  "moderate" -> ask the user.

    def quick_scan(self, command: str) -> tuple[str, str] | None:
        """Layer 1: regex quick-scan. Return (level, reason) or None."""
        for pat, reason in DANGEROUS_PATTERNS:
            if pat.search(command):
                return ("dangerous", reason)
        return None

    def llm_classify(self, command: str, context: str = "") -> str:
        """Layer 2: LLM classification. Return safe/moderate/dangerous."""
        prompt = CLASSIFIER_PROMPT.format(command=command, context=context[-300:])
        try:
            resp = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            answer = resp.content[0].text.strip().lower()
            for level in ("safe", "moderate", "dangerous"):
                if level in answer:
                    return level
        except Exception as e:
            print(f"[classifier:llm] fallback to moderate: {e}")
        return "moderate"

    def classify(self, command: str, context: str = "") -> dict:
        """Full two-layer pipeline."""
        # Layer 1
        quick = self.quick_scan(command)
        if quick:
            level, reason = quick
            return {"level": level, "mode": "deny", "reason": reason, "source": "pattern"}
        # Whitelist
        base = command.split()[0] if command.split() else ""
        has_compound = bool(re.search(r'[;&|`]|\$\(', command))
        if base in SAFE_COMMANDS and not has_compound:
            return {"level": "safe", "mode": "allow", "reason": "", "source": "whitelist"}
        # Layer 2
        level = self.llm_classify(command, context)
        mode = {"safe": "allow", "moderate": "ask", "dangerous": "deny"}[level]
        return {"level": level, "mode": mode, "reason": f"LLM: {level}", "source": "llm"}


# -- PermissionGuard (upgraded with classifier) --
class PermissionGuard:
    def __init__(self, classifier: SecurityClassifier = None):
        self.classifier = classifier

    def check(self, command: str, context: str = "") -> tuple[bool, str, str]:
        """Return (allowed, command_to_run, reason)."""
        result = self.classifier.classify(command, context)
        mode = result["mode"]
        if mode == "deny":
            return (False, command, result["reason"])
        elif mode == "ask":
            approved = self._prompt_user(command, result["reason"])
            return (approved, command, result["reason"])
        else:
            return (True, command, "")

    def _prompt_user(self, command: str, reason: str) -> bool:
        print(f"\033[33m[security:{reason}]\033[0m")
        print(f"\033[33m  Command: {command}\033[0m")
        ans = input("\033[33m  Allow? (y/n) \033[0m").strip().lower()
        return ans == "y"


CLASSIFIER = SecurityClassifier(client, MODEL)
GUARD = PermissionGuard(classifier=CLASSIFIER)


# -- Tool implementations --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    allowed, cmd, reason = GUARD.check(command)
    if not allowed:
        return f"Security denied: {reason}"
    try:
        r = subprocess.run(cmd, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command. Two-layer security: regex quick-scan + LLM intent classification.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms14 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
