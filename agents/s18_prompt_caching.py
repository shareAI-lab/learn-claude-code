#!/usr/bin/env python3
# Harness: prompt caching — reuse expensive context across API calls.
"""
s18_prompt_caching.py - Prompt Caching

Mark messages with cache_control to let the API cache stable context.
Subsequent calls that share the same prefix read from cache instead of
re-processing tokens, saving ~75% on cached input tokens.

    Turn 1 (no cache):
    System (cached) + History (cached) + New message
    = [CREATION]  [CREATION]  [normal]

    Turn 2 (cache hit):
    System (cached) + History (cached) + New message
    = [READ]      [READ]      [normal]

    Cost: cached tokens cost ~25% of uncached tokens.
    Speed: cached tokens skip embedding, saving latency.

    What to cache:
    - System prompt (large, reused every call)
    - Early conversation messages (stable prefix)

    What NOT to cache:
    - Recent messages (change every turn)
    - Tool results (different each time)

Key insight: "Cache the stable prefix; pay full price only for the new delta."
"""

import json
import os
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

# Large system prompt to demonstrate caching impact
# In a real agent, this includes tool definitions, skills, instructions, etc.
SYSTEM_PROMPT_PARTS = []

# Tool definitions (large block — great for caching)
SYSTEM_PROMPT_PARTS.append("""
You have access to the following tools:

## bash
Run a shell command. Dangerous commands are blocked.
Input: {"command": "ls -la"}

## read_file
Read file contents.
Input: {"path": "src/main.py", "limit": 100}

## write_file
Write content to file.
Input: {"path": "output.txt", "content": "hello"}

## edit_file
Replace exact text in file.
Input: {"path": "file.py", "old_text": "old", "new_text": "new"}

## run_tests
Run pytest on specified files.
Input: {"path": "tests/"}

## git_commit
Commit changes with message.
Input: {"message": "fix: description"}

## git_diff
Show current changes.
Input: {"path": "."}

## lint
Run ruff linter.
Input: {"path": "."}

## search_code
Search codebase for patterns.
Input: {"pattern": "def main", "limit": 10}
""")

# Skill definitions (another large block)
SYSTEM_PROMPT_PARTS.append("""
## Available Skills

### code-review
Review code for bugs, style, and security. Returns structured findings
with severity ratings. Use for PR reviews and code quality checks.

### test-engineer
Write and run tests. Strategy: unit tests for logic, integration tests
for API boundaries, E2E tests for user flows. TDD supported.

### debugger
Root-cause analysis. Stack trace analysis, regression isolation,
bisect strategies. Use when something is broken.

### architect
Design discussions, refactoring strategies, API design. High-level
thinking before coding.

### security-review
OWASP Top 10 checks, secrets detection, input validation audit,
dependency vulnerability scanning.

### documentation
Technical writing. API docs, READMEs, inline comments, ADRs.
""" * 2)  # Duplicate to make it larger

# Behavioral guidelines
SYSTEM_PROMPT_PARTS.append(f"""
## Workspace
You are working at: {WORKDIR}

## Guidelines
1. Think before coding — state assumptions, surface trade-offs.
2. Simplicity first — minimum code that solves the problem.
3. Surgical changes — touch only what must change.
4. Goal-driven — define success criteria, verify before declaring done.

## Python Notes
- subprocess.run(shell=True) uses /bin/sh
- All variables are references
- list.append() mutates in place
- Tool results use 'user' role in Anthropic API

## Context Window
- 200K context window total
- max_tokens=8000 per request
- As conversation grows, input approaches limit
- Context compression (s06) trims old tool results
- Caching (this session) reduces cost of repeated context
""")

SYSTEM_PROMPT = "\n".join(SYSTEM_PROMPT_PARTS)


def build_cached_system():
    """Build system prompt with cache_control on the last block.

    Anthropic caches from the cache marker to the end of the block sequence.
    Placing it on the last block caches the entire system prompt.
    """
    try:
        # Build as content blocks for cache_control
        blocks = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        return blocks, True
    except Exception:
        # Fallback: provider doesn't support cache_control
        return SYSTEM_PROMPT, False


def build_cached_messages(messages: list, cache_up_to: int = 0):
    """
    Add cache_control to stable message prefix.

    Messages before cache_up_to index are cached.
    Messages after are not (they change every turn).
    """
    try:
        cached = []
        for i, msg in enumerate(messages):
            new_msg = {"role": msg["role"]}
            content = msg.get("content", "")
            if isinstance(content, str):
                if i < cache_up_to:
                    new_msg["content"] = [
                        {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
                    ]
                else:
                    new_msg["content"] = content
            else:
                new_msg["content"] = content
            cached.append(new_msg)
        return cached, True
    except Exception:
        return messages, False


# -- Usage tracking --
class CacheStats:
    def __init__(self):
        self.creation_tokens = 0
        self.read_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def record(self, response):
        self.calls += 1
        usage = response.usage
        if hasattr(usage, "cache_creation_input_tokens"):
            created = usage.cache_creation_input_tokens or 0
            read = usage.cache_read_input_tokens or 0
            self.creation_tokens += created
            self.read_tokens += read
            self.input_tokens += usage.input_tokens
            self.output_tokens += usage.output_tokens

    def summary(self) -> str:
        lines = [f"Calls: {self.calls}"]
        if self.creation_tokens:
            pct = self.read_tokens / max(self.read_tokens + self.creation_tokens, 1) * 100
            lines.append(f"  Cache creation: {self.creation_tokens} tokens")
            lines.append(f"  Cache read:     {self.read_tokens} tokens ({pct:.0f}% of cached)")
            lines.append(f"  Non-cached input: {self.input_tokens - self.creation_tokens - self.read_tokens} tokens")
        else:
            lines.append(f"  Input:    {self.input_tokens} tokens (no caching available)")
        lines.append(f"  Output:   {self.output_tokens} tokens")
        return "\n".join(lines)


stats = CacheStats()
CACHING_ENABLED = False  # Will be set after first call


# -- Base tools --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash":      lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
]


def agent_loop(messages: list):
    """Agent loop with caching support."""
    global CACHING_ENABLED

    # Build messages with cache_control on stable prefix
    # Cache up to the first 3 messages (system context injection)
    cache_boundary = min(3, len(messages))
    cached_messages, caching_ok = build_cached_messages(messages, cache_boundary)

    # Build system prompt
    system, system_ok = build_cached_system()
    CACHING_ENABLED = caching_ok and system_ok

    if CACHING_ENABLED:
        print("  [cache] enabled — system prompt + early messages cached")
    else:
        print("  [cache] disabled (provider may not support cache_control)")

    while True:
        response = client.messages.create(
            model=MODEL,
            system=system,
            messages=cached_messages,
            tools=TOOLS,
            max_tokens=4000,
        )
        stats.record(response)
        messages.append({"role": "assistant", "content": response.content})
        cached_messages.append({"role": "assistant", "content": response.content})
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
                print(f"> {block.name}: {str(output)[:100]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})
        cached_messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    print(f"Prompt Caching demo")
    print(f"System prompt size: ~{len(SYSTEM_PROMPT)} chars (~{len(SYSTEM_PROMPT)//4} tokens)")
    print(f"Commands: /stats /demo\n")

    while True:
        try:
            query = input("\033[36ms18 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        if query.strip() == "/stats":
            print(stats.summary())
            print()
            continue

        if query.strip() == "/demo":
            print("=== Caching Demo ===")
            print("Running 3 turns with the same large system prompt...\n")

            # Reset for demo
            demo_history = [{"role": "user", "content": "What tools do you have? List them briefly."}]
            stats_demo = CacheStats()

            for i in range(3):
                print(f"--- Turn {i + 1} ---")
                cached_msgs, _ = build_cached_messages(demo_history, min(3, len(demo_history)))
                system, _ = build_cached_system()
                response = client.messages.create(
                    model=MODEL, system=system, messages=cached_msgs, max_tokens=2000,
                )
                stats_demo.record(response)

                usage = response.usage
                if hasattr(usage, "cache_creation_input_tokens"):
                    print(f"  Created: {usage.cache_creation_input_tokens} | "
                          f"Read: {usage.cache_read_input_tokens} | "
                          f"Input: {usage.input_tokens} | Output: {usage.output_tokens}")
                else:
                    print(f"  Input: {usage.input_tokens} | Output: {usage.output_tokens} "
                          f"(no cache support)")

                text = "".join(b.text for b in response.content if hasattr(b, "text"))
                demo_history.append({"role": "assistant", "content": response.content})
                demo_history.append({"role": "user", "content": f"Elaborate on point {i+1}."})
                print(f"  Response: {text[:80]}...\n")

            print(stats_demo.summary())
            print()
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
