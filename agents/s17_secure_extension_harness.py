#!/usr/bin/env python3
# Harness: secure extension -- five layers of defense, one loop.
"""
s17_secure_extension_harness.py - Secure Extension Harness

s13-s16 each run as a standalone agent. Real systems need all layers
working together inside a single execution pipeline.

    LLM calls tool
         |
         v
    +---------------------+
    | [1] Pre-tool Hook   | --block--> return error
    +----------+----------+
               v
    +---------------------+
    | [2] Classifier      | --deny---> return error
    +----------+----------+
               v
    +---------------------+
    | [3] Permission      | --deny---> return error
    |                     | --ask---> user confirm?
    +----------+----------+
               v
    +---------------------+
    | [4] Execute         |  built-in handler or MCP
    +----------+----------+
               v
    +---------------------+
    | [5] Post-tool Hook  |  observe / log
    +----------+----------+
               |
               v
         return result

Key insight: "Production harnesses aren't about more features -- they're
about clear responsibilities at every layer."
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use tools to solve tasks. The harness enforces security:
dangerous commands are blocked, some require your confirmation.
MCP tools extend your reach beyond built-in tools. Act, don't explain."""


# === SECTION: security_classifier (s14) ===

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
Context: {context}"""


class SecurityClassifier:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def quick_scan(self, command: str) -> tuple[str, str] | None:
        for pat, reason in DANGEROUS_PATTERNS:
            if pat.search(command):
                return ("dangerous", reason)
        return None

    def llm_classify(self, command: str, context: str = "") -> str:
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
        quick = self.quick_scan(command)
        if quick:
            level, reason = quick
            return {"level": level, "mode": "deny", "reason": reason, "source": "pattern"}
        base = command.split()[0] if command.split() else ""
        has_compound = bool(re.search(r'[;&|`]|\$\(', command))
        if base in SAFE_COMMANDS and not has_compound:
            return {"level": "safe", "mode": "allow", "reason": "", "source": "whitelist"}
        level = self.llm_classify(command, context)
        mode = {"safe": "allow", "moderate": "ask", "dangerous": "deny"}[level]
        return {"level": level, "mode": mode, "reason": f"LLM: {level}", "source": "llm"}


# === SECTION: permission_guard (s13) ===

class PermissionGuard:
    def __init__(self, classifier: SecurityClassifier):
        self.classifier = classifier

    def check(self, command: str, context: str = "") -> tuple[bool, str, str]:
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


# === SECTION: hooks (s15) ===

HOOK_EVENTS = (
    "PreToolUse", "PostToolUse", "PreBash", "PostBash",
    "AgentStart", "AgentStop", "OnError", "OnCompact",
)
HOOKS_DIR = WORKDIR / ".hooks"


class HookManager:
    def __init__(self):
        self._hooks: dict[str, list] = {e: [] for e in HOOK_EVENTS}
        HOOKS_DIR.mkdir(exist_ok=True)
        self._load_defaults()

    def _load_defaults(self):
        self.register("PreBash", "observe", self._audit_log,
                      "bash_audit_log", "Log all bash commands")
        self.register("PostToolUse", "observe", self._auto_git_add,
                      "auto_git_add", "Auto git add after write/edit",
                      tool_filter="write_file")

    def register(self, event: str, mode: str, handler, name: str,
                 description: str = "", tool_filter: str = None):
        self._hooks[event].append({
            "event": event, "mode": mode, "handler": handler,
            "name": name, "description": description, "tool_filter": tool_filter,
        })

    def fire(self, event: str, context: dict) -> dict | None:
        for hook in self._hooks.get(event, []):
            if hook["tool_filter"] and context.get("tool") != hook["tool_filter"]:
                continue
            result = hook["handler"](context)
            if result is None:
                continue
            if isinstance(result, str):
                return {"action": "block", "reason": result, "hook": hook["name"]}
            if isinstance(result, dict) and result.get("action") == "block":
                return result
        return None

    def list_hooks(self) -> str:
        lines = []
        for event in HOOK_EVENTS:
            for h in self._hooks[event]:
                lines.append(f"  {event:15} [{h['mode']:7}] {h['name']}: {h['description']}")
        return "\n".join(lines)

    def _audit_log(self, context: dict):
        log_file = HOOKS_DIR / "audit.jsonl"
        entry = {"timestamp": time.time(),
                 "tool": context.get("tool"),
                 "command": context.get("input", {}).get("command")}
        with log_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _auto_git_add(self, context: dict):
        path = context.get("input", {}).get("path", "")
        if path:
            subprocess.run(["git", "add", path], cwd=WORKDIR,
                           capture_output=True, text=True)


# === SECTION: mcp (s16) ===

MCP_CONFIG_PATH = WORKDIR / ".mcp" / "config.json"
MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPServerConfig:
    def __init__(self, name: str, transport: str, command: str = "",
                 url: str = "", args: list = None, env: dict = None):
        self.name = name
        self.transport = transport
        self.command = command
        self.url = url
        self.args = args or []
        self.env = env or {}


class MCPClient:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process = None
        self._id = 0

    def start(self):
        if self.config.transport == "stdio" and self.config.command:
            cmd = [self.config.command] + self.config.args
            env = {**os.environ, **self.config.env} if self.config.env else None
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=WORKDIR, env=env,
            )

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send_rpc(self, method: str, params: dict = None) -> dict:
        request = {"jsonrpc": "2.0", "method": method, "id": self._next_id()}
        if params:
            request["params"] = params
        self.process.stdin.write((json.dumps(request) + "\n").encode())
        self.process.stdin.flush()
        line = self.process.stdout.readline().decode().strip()
        return json.loads(line).get("result", {}) if line else {}

    def discover_tools(self) -> list:
        result = self._send_rpc("tools/list")
        return result.get("tools", [])

    def call(self, tool_name: str, arguments: dict) -> str:
        result = self._send_rpc("tools/call", {"name": tool_name, "arguments": arguments})
        contents = result.get("content", [])
        return "\n".join(c.get("text", "") for c in contents if c.get("type") == "text")

    def shutdown(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


class MCPManager:
    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        self._tools: dict[str, tuple[str, dict]] = {}

    def load_config(self) -> list[MCPServerConfig]:
        if not MCP_CONFIG_PATH.exists():
            return []
        data = json.loads(MCP_CONFIG_PATH.read_text())
        servers = data.get("mcpServers", {})
        return [MCPServerConfig(name=k, **v) for k, v in servers.items()]

    def connect_all(self) -> list[dict]:
        discovered = []
        for config in self.load_config():
            try:
                c = MCPClient(config)
                c.start()
                tools = c.discover_tools()
                self._clients[config.name] = c
                for tool in tools:
                    self._tools[tool["name"]] = (config.name, tool)
                    discovered.append(tool)
            except Exception as e:
                print(f"[mcp] Failed to connect {config.name}: {e}")
        return discovered

    def call(self, tool_name: str, arguments: dict) -> str:
        if tool_name not in self._tools:
            return f"Unknown MCP tool: {tool_name}"
        server_name, _ = self._tools[tool_name]
        return self._clients[server_name].call(tool_name, arguments)

    def shutdown_all(self):
        for c in self._clients.values():
            c.shutdown()

    def list_servers(self) -> str:
        lines = []
        for name, c in self._clients.items():
            tools = [t for t, (s, _) in self._tools.items() if s == name]
            lines.append(f"  {name} ({c.config.transport}): {len(tools)} tools")
        return "\n".join(lines) if lines else "  (no MCP servers connected)"


# === SECTION: initialize all managers ===

CLASSIFIER = SecurityClassifier(client, MODEL)
GUARD = PermissionGuard(classifier=CLASSIFIER)
HOOKS = HookManager()
MCP = MCPManager()


# === SECTION: base tools ===

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
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


# === SECTION: hook & mcp management tools ===

def hook_register(event: str, mode: str, name: str,
                  description: str = "", tool_filter: str = None) -> str:
    if event not in HOOK_EVENTS:
        return f"Unknown event: {event}. Available: {', '.join(HOOK_EVENTS)}"
    if mode not in ("observe", "modify", "block"):
        return f"Unknown mode: {mode}. Available: observe, modify, block"
    # For observe and block, register a simple handler
    if mode == "observe":
        def handler(ctx): pass
    elif mode == "block":
        def handler(ctx): return f"Blocked by user hook: {name}"
    else:
        def handler(ctx): pass
    HOOKS.register(event, mode, handler, name, description, tool_filter)
    return f"Registered hook '{name}' on {event} ({mode})"


def mcp_discover() -> str:
    tools = MCP.connect_all()
    # Register discovered MCP tools into TOOL_HANDLERS and TOOLS
    for tool_schema in tools:
        tname = tool_schema["name"]
        TOOL_HANDLERS[tname] = (lambda n: lambda **kw: MCP.call(n, kw))(tname)
        TOOLS.append(tool_schema)
    return f"Discovered {len(tools)} MCP tools"


TOOL_HANDLERS = {
    "bash":             lambda **kw: run_bash(kw["command"]),
    "read_file":        lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":       lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":        lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "hook_register":    lambda **kw: hook_register(kw["event"], kw["mode"], kw["name"],
                                                    kw.get("description", ""), kw.get("tool_filter")),
    "hook_list":        lambda **kw: HOOKS.list_hooks(),
    "mcp_list_servers": lambda **kw: MCP.list_servers(),
    "mcp_discover":     lambda **kw: mcp_discover(),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command. Routed through security pipeline: hook -> classifier -> permission -> execute -> hook.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "hook_register", "description": "Register a hook to intercept tool calls. Events: PreToolUse, PostToolUse, PreBash, PostBash, AgentStart, AgentStop. Modes: observe, modify, block.",
     "input_schema": {"type": "object", "properties": {"event": {"type": "string"}, "mode": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "tool_filter": {"type": "string"}}, "required": ["event", "mode", "name"]}},
    {"name": "hook_list", "description": "List all registered hooks.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "mcp_list_servers", "description": "List connected MCP servers and their tools.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "mcp_discover", "description": "Re-scan and register MCP tools from all configured servers.",
     "input_schema": {"type": "object", "properties": {}}},
]


# === SECTION: pipeline ===

def execute_tool(tool_name: str, tool_input: dict, context: dict) -> str:
    # Layer 1: Pre-tool hook
    hook_ctx = {"tool": tool_name, "input": tool_input}
    pre = HOOKS.fire("PreToolUse", hook_ctx)
    if pre and pre.get("action") == "block":
        return f"Blocked by hook: {pre['reason']}"

    # Layer 1b: Pre-bash hook (finer-grained, logs audit trail)
    if tool_name == "bash":
        pre_bash = HOOKS.fire("PreBash", hook_ctx)
        if pre_bash and pre_bash.get("action") == "block":
            return f"Blocked by bash hook: {pre_bash['reason']}"

    # Layer 2: Classifier + Layer 3: Permission (bash only)
    if tool_name == "bash":
        cmd = tool_input.get("command", "")
        allowed, cmd_to_run, reason = GUARD.check(cmd, context.get("recent_text", ""))
        if not allowed:
            return f"Security denied: {reason}"
        tool_input = {**tool_input, "command": cmd_to_run}

    # Layer 4: Execute
    handler = TOOL_HANDLERS.get(tool_name)
    if handler:
        try:
            output = handler(**tool_input)
        except Exception as e:
            HOOKS.fire("OnError", {"tool": tool_name, "error": str(e)})
            output = f"Error: {e}"
    elif tool_name in MCP._tools:
        output = MCP.call(tool_name, tool_input)
    else:
        output = f"Unknown tool: {tool_name}"

    # Layer 5: Post-tool hook
    HOOKS.fire("PostToolUse", {"tool": tool_name, "output": output})
    if tool_name == "bash":
        HOOKS.fire("PostBash", {"tool": tool_name, "output": output})

    return output


# === SECTION: agent_loop ===

def agent_loop(messages: list):
    HOOKS.fire("AgentStart", {"messages": messages})
    try:
        while True:
            response = client.messages.create(
                model=MODEL, system=SYSTEM, messages=messages,
                tools=TOOLS, max_tokens=8000,
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return
            results = []
            recent_text = ""
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    recent_text += block.text[-200:]
            for block in response.content:
                if block.type == "tool_use":
                    output = execute_tool(block.name, block.input,
                                          {"recent_text": recent_text})
                    print(f"> {block.name}:")
                    print(str(output)[:200])
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": str(output)})
            messages.append({"role": "user", "content": results})
    finally:
        HOOKS.fire("AgentStop", {})


# === SECTION: repl ===
if __name__ == "__main__":
    # Connect MCP servers at startup
    print("[mcp] Connecting servers...")
    print(mcp_discover())

    history = []
    while True:
        try:
            query = input("\033[36ms17 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        # REPL commands
        if query.strip() == "/security":
            print(f"Classifier: active ({len(DANGEROUS_PATTERNS)} patterns + LLM)")
            print(f"Permission: deny/ask/allow")
            continue
        if query.strip() == "/hooks":
            print(HOOKS.list_hooks())
            continue
        if query.strip() == "/mcp":
            print(MCP.list_servers())
            continue
        if query.strip() == "/audit":
            log = HOOKS_DIR / "audit.jsonl"
            if log.exists():
                print(log.read_text()[-2000:])
            else:
                print("  (no audit log)")
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
    MCP.shutdown_all()
