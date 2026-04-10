#!/usr/bin/env python3
# Harness（执行框架）: integration（集成）——工具不只存在于本地代码里。
"""
s19_mcp_plugin.py - MCP & Plugin System（插件与外部能力）

本章聚焦最小可用观点：
外部进程可暴露工具，经过少量规范化后，
智能体即可像使用本地工具一样使用它们。

最小路径（Minimal path）：
  1. 启动一个 MCP server（服务器）进程
  2. 查询它暴露了哪些 tools（工具）
  3. 为这些工具加前缀并注册
  4. 将匹配调用路由到该服务器

Plugins（插件）会再增加一层 discovery（发现）。
一个小型 manifest（清单）即可告诉智能体应启动哪个外部服务器。

关键洞察：
"外部工具应进入同一工具管线，而不是形成平行世界。"
实践上这意味着共享权限检查与统一 tool_result 载荷。

建议阅读顺序：
1. CapabilityPermissionGate：外部工具仍走同一控制闸门。
2. MCPClient：单个服务器连接如何暴露 tool spec（工具规格）与工具调用。
3. PluginLoader：manifest 如何声明外部服务器。
4. MCPToolRouter / build_tool_pool：本地与外部工具如何合并成同一工具池。

最常见混淆点：
- plugin manifest（插件清单）不是 MCP server（服务器）
- MCP server 不是单个 MCP tool（工具）
- 外部能力不会绕过本地权限路径

教学边界：
本文件只讲最小可用的 stdio MCP 路径。
Marketplace（市场）细节、auth（鉴权）流程、重连逻辑以及非工具能力层，
刻意留给桥接文档与后续扩展。
"""

import json
import os
import subprocess
import threading
from pathlib import Path

try:
    from agents.llm_client import create_client
except ModuleNotFoundError:
    from llm_client import create_client
from dotenv import load_dotenv

load_dotenv(override=True)


WORKDIR = Path.cwd()
client = create_client()
MODEL = os.environ["MODEL_ID"]
PERMISSION_MODES = ("default", "auto")


class CapabilityPermissionGate:
    """
    本地工具与外部能力共用的权限门控。

    教学目标很简单：MCP 不绕过控制平面。
    本地工具与 MCP 工具都先规范化为 capability intent，
    再走同一 allow/ask 策略。
    """

    READ_PREFIXES = ("read", "list", "get", "show", "search", "query", "inspect")
    HIGH_RISK_PREFIXES = ("delete", "remove", "drop", "shutdown")

    def __init__(self, mode: str = "default"):
        self.mode = mode if mode in PERMISSION_MODES else "default"

    def normalize(self, tool_name: str, tool_input: dict) -> dict:
        if tool_name.startswith("mcp__"):
            _, server_name, actual_tool = tool_name.split("__", 2)
            source = "mcp"
        else:
            server_name = None
            actual_tool = tool_name
            source = "native"

        lowered = actual_tool.lower()
        if actual_tool == "read_file" or lowered.startswith(self.READ_PREFIXES):
            risk = "read"
        elif actual_tool == "bash":
            command = tool_input.get("command", "")
            risk = "high" if any(
                token in command for token in ("rm -rf", "sudo", "shutdown", "reboot")
            ) else "write"
        elif lowered.startswith(self.HIGH_RISK_PREFIXES):
            risk = "high"
        else:
            risk = "write"

        return {
            "source": source,
            "server": server_name,
            "tool": actual_tool,
            "risk": risk,
        }

    def check(self, tool_name: str, tool_input: dict) -> dict:
        intent = self.normalize(tool_name, tool_input)

        if intent["risk"] == "read":
            return {"behavior": "allow", "reason": "只读能力", "intent": intent}

        if self.mode == "auto" and intent["risk"] != "high":
            return {
                "behavior": "allow",
                "reason": "auto 模式下的非高风险能力",
                "intent": intent,
            }

        if intent["risk"] == "high":
            return {
                "behavior": "ask",
                "reason": "高风险能力需要确认",
                "intent": intent,
            }

        return {
            "behavior": "ask",
            "reason": "会改变状态的能力需要确认",
            "intent": intent,
        }

    def ask_user(self, intent: dict, tool_input: dict) -> bool:
        preview = json.dumps(tool_input, ensure_ascii=False)[:200]
        source = (
            f"{intent['source']}:{intent['server']}/{intent['tool']}"
            if intent.get("server")
            else f"{intent['source']}:{intent['tool']}"
        )
        print(f"\n  [Permission] {source} risk={intent['risk']}: {preview}")
        try:
            answer = input("  是否允许？(y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")


permission_gate = CapabilityPermissionGate()


class MCPClient:
    """
    基于 stdio 的最小 MCP 客户端。

    该实现足以讲清核心架构，
    无需提前卷入传输层、鉴权流和市场细节。
    """

    def __init__(self, server_name: str, command: str, args: list = None, env: dict = None):
        self.server_name = server_name
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self.process = None
        self._request_id = 0
        self._tools = []  # 已缓存工具列表

    def connect(self):
        """启动 MCP server 进程。"""
        try:
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
            )
            # 发送 initialize 请求
            self._send({"method": "initialize", "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "teaching-agent", "version": "1.0"},
            }})
            response = self._recv()
            if response and "result" in response:
                # 发送 initialized 通知
                self._send({"method": "notifications/initialized"})
                return True
        except FileNotFoundError:
            print(f"[MCP] 未找到服务器命令：{self.command}")
        except Exception as e:
            print(f"[MCP] Connection failed: {e}")
        return False

    def list_tools(self) -> list:
        """从 server 拉取可用工具列表。"""
        self._send({"method": "tools/list", "params": {}})
        response = self._recv()
        if response and "result" in response:
            self._tools = response["result"].get("tools", [])
        return self._tools

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """在 server 端执行工具。"""
        self._send({"method": "tools/call", "params": {
            "name": tool_name,
            "arguments": arguments,
        }})
        response = self._recv()
        if response and "result" in response:
            content = response["result"].get("content", [])
            return "\n".join(c.get("text", str(c)) for c in content)
        if response and "error" in response:
            return f"MCP Error: {response['error'].get('message', 'unknown')}"
        return "MCP Error: no response"

    def get_agent_tools(self) -> list:
        """
        将 MCP 工具转换为 agent 工具格式。

        教学版沿用简单前缀方案：
        mcp__{server_name}__{tool_name}
        """
        agent_tools = []
        for tool in self._tools:
            prefixed_name = f"mcp__{self.server_name}__{tool['name']}"
            agent_tools.append({
                "name": prefixed_name,
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}}),
                "_mcp_server": self.server_name,
                "_mcp_tool": tool["name"],
            })
        return agent_tools

    def disconnect(self):
        """关闭 server 进程。"""
        if self.process:
            try:
                self._send({"method": "shutdown"})
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None

    def _send(self, message: dict):
        if not self.process or self.process.poll() is not None:
            return
        self._request_id += 1
        envelope = {"jsonrpc": "2.0", "id": self._request_id, **message}
        line = json.dumps(envelope) + "\n"
        try:
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def _recv(self) -> dict | None:
        if not self.process or self.process.poll() is not None:
            return None
        try:
            line = self.process.stdout.readline()
            if line:
                return json.loads(line)
        except (json.JSONDecodeError, OSError):
            pass
        return None


class PluginLoader:
    """
    从 `.claude-plugin/` 目录加载插件。

    教学版仅实现最小插件流程：
    读取 manifest，发现 MCP server 配置并注册。
    """

    def __init__(self, search_dirs: list = None):
        self.search_dirs = search_dirs or [WORKDIR]
        self.plugins = {}  # name -> manifest（清单）

    def scan(self) -> list:
        """扫描目录，查找 `.claude-plugin/plugin.json` 清单文件。"""
        found = []
        for search_dir in self.search_dirs:
            plugin_dir = Path(search_dir) / ".claude-plugin"
            manifest_path = plugin_dir / "plugin.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                    name = manifest.get("name", plugin_dir.parent.name)
                    self.plugins[name] = manifest
                    found.append(name)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"[Plugin] Failed to load {manifest_path}: {e}")
        return found

    def get_mcp_servers(self) -> dict:
        """
        从已加载插件中提取 MCP server 配置。
        返回 {server_name: {command, args, env}}。
        """
        servers = {}
        for plugin_name, manifest in self.plugins.items():
            for server_name, config in manifest.get("mcpServers", {}).items():
                servers[f"{plugin_name}__{server_name}"] = config
        return servers


class MCPToolRouter:
    """
    将工具调用路由到正确的 MCP server。

    MCP 工具命名为 `mcp__{server}__{tool}`，
    与本地工具共存于同一工具池。
    Router 负责拆前缀并分发到目标 MCPClient。
    """

    def __init__(self):
        self.clients = {}  # server_name（服务名）-> MCPClient

    def register_client(self, client: MCPClient):
        self.clients[client.server_name] = client

    def is_mcp_tool(self, tool_name: str) -> bool:
        return tool_name.startswith("mcp__")

    def call(self, tool_name: str, arguments: dict) -> str:
        """将 MCP 工具调用路由到正确 server。"""
        parts = tool_name.split("__", 2)
        if len(parts) != 3:
            return f"Error: 非法的 MCP 工具名：{tool_name}"
        _, server_name, actual_tool = parts
        client = self.clients.get(server_name)
        if not client:
            return f"Error: 未找到 MCP server：{server_name}"
        return client.call_tool(actual_tool, arguments)

    def get_all_tools(self) -> list:
        """汇总所有已连接 MCP server 的工具。"""
        tools = []
        for client in self.clients.values():
            tools.extend(client.get_agent_tools())
        return tools


# -- 原生工具实现（与 s02 保持一致） --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: 危险命令已拦截"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str) -> str:
    try:
        return safe_path(path).read_text()[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
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


NATIVE_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"]),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

NATIVE_TOOLS = [
    {"name": "bash", "description": "执行 shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "向文件写入内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中替换精确文本。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
]


# -- MCP 工具路由器（全局实例） --
mcp_router = MCPToolRouter()
plugin_loader = PluginLoader()


def build_tool_pool() -> list:
    """
    组装完整工具池：native（原生）+ MCP 工具。

    当名称冲突时，native 工具优先，确保引入外部工具后
    本地核心能力仍保持可预测。
    """
    all_tools = list(NATIVE_TOOLS)
    mcp_tools = mcp_router.get_all_tools()

    native_names = {t["name"] for t in all_tools}
    for tool in mcp_tools:
        if tool["name"] not in native_names:
            all_tools.append(tool)

    return all_tools


def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """分发到 native 处理器或 MCP 路由器。"""
    if mcp_router.is_mcp_tool(tool_name):
        return mcp_router.call(tool_name, tool_input)
    handler = NATIVE_HANDLERS.get(tool_name)
    if handler:
        return handler(**tool_input)
    return f"Unknown tool: {tool_name}"


def normalize_tool_result(tool_name: str, output: str, intent: dict | None = None) -> str:
    intent = intent or permission_gate.normalize(tool_name, {})
    status = "error" if "Error:" in output or "MCP Error:" in output else "ok"
    payload = {
        "source": intent["source"],
        "server": intent.get("server"),
        "tool": intent["tool"],
        "risk": intent["risk"],
        "status": status,
        "preview": output[:500],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def agent_loop(messages: list):
    """统一使用 native + MCP 工具池的智能体主循环。"""
    tools = build_tool_pool()

    while True:
        system = (
            f"你是位于 {WORKDIR} 的 coding agent（编码智能体），请使用工具解决任务。\n"
            "你可同时使用 native tools（本地工具）与 MCP tools（外部工具）。\n"
            "MCP 工具采用前缀 mcp__{server}__{tool}。\n"
            "所有能力在执行前都必须经过同一权限门控。"
        )
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=tools, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            decision = permission_gate.check(block.name, block.input or {})
            try:
                if decision["behavior"] == "deny":
                    output = f"Permission denied: {decision['reason']}"
                elif decision["behavior"] == "ask" and not permission_gate.ask_user(
                    decision["intent"], block.input or {}
                ):
                    output = f"用户拒绝执行：{decision['reason']}"
                else:
                    output = handle_tool_call(block.name, block.input or {})
            except Exception as e:
                output = f"Error: {e}"
            print(f"> {block.name}: {str(output)[:200]}")
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": normalize_tool_result(
                    block.name,
                    str(output),
                    decision.get("intent"),
                ),
            })

        messages.append({"role": "user", "content": results})


# 你可在后续继续扩展：
# - 更多 transport（传输层）类型
# - auth / approval（鉴权与审批）流程
# - server 重连与生命周期管理
# - 模型可见前的外部工具过滤
# - 更丰富的插件安装与更新处理


if __name__ == "__main__":
# 扫描并加载插件
    found = plugin_loader.scan()
    if found:
        print(f"[Plugins loaded: {', '.join(found)}]")
        for server_name, config in plugin_loader.get_mcp_servers().items():
            mcp_client = MCPClient(server_name, config.get("command", ""), config.get("args", []))
            if mcp_client.connect():
                mcp_client.list_tools()
                mcp_router.register_client(mcp_client)
                print(f"[MCP] Connected to {server_name}")

    tool_count = len(build_tool_pool())
    mcp_count = len(mcp_router.get_all_tools())
    print(f"[Tool pool: {tool_count} tools ({mcp_count} from MCP)]")

    history = []
    while True:
        try:
            query = input("\033[36ms19 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        if query.strip() == "/tools":
            for tool in build_tool_pool():
                prefix = "[MCP] " if tool["name"].startswith("mcp__") else "       "
                print(f"  {prefix}{tool['name']}: {tool.get('description', '')[:60]}")
            continue

        if query.strip() == "/mcp":
            if mcp_router.clients:
                for name, c in mcp_router.clients.items():
                    tools = c.get_agent_tools()
                    print(f"  {name}: {len(tools)} tools")
            else:
                print("  （未连接任何 MCP 服务器）")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()

# 清理 MCP 连接
    for c in mcp_router.clients.values():
        c.disconnect()
