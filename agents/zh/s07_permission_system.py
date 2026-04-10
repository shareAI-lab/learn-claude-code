#!/usr/bin/env python3
# Harness（执行框架）: safety（安全）——连接“意图”和“执行”的权限管线。
"""
s07_permission_system.py - Permission System（权限系统）

每一次工具调用在执行前都必须经过权限管线（permission pipeline）。

教学版管线：
  1. deny rules（拒绝规则）
  2. mode check（模式检查）
  3. allow rules（放行规则）
  4. ask user（询问用户）

本版本先聚焦三种模式：
  - default（默认）
  - plan（规划）
  - auto（自动）

这已足够搭建可用且可理解的权限系统，不会在起步阶段被复杂策略分支淹没。

关键洞察：
"安全是管线，不是布尔开关。"
"""

import json
import os
import re
import subprocess
from fnmatch import fnmatch
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

# -- 权限模式（permission modes） --
# 教学版先从三个清晰模式入手。
MODES = ("default", "plan", "auto")

READ_ONLY_TOOLS = {"read_file", "bash_readonly"}

# 具有状态副作用的工具
WRITE_TOOLS = {"write_file", "edit_file", "bash"}


# -- Bash 安全校验 --
class BashSecurityValidator:
    """
    校验 bash 命令中明显危险的模式。

    教学版刻意保持规则小而清晰：
    先识别高风险模式，再由权限管线决定“拒绝”或“询问用户”。
    """

    VALIDATORS = [
        ("shell_metachar", r"[;&|`$]"),       # shell 元字符
        ("sudo", r"\bsudo\b"),                 # 提权
        ("rm_rf", r"\brm\s+(-[a-zA-Z]*)?r"),  # 递归删除
        ("cmd_substitution", r"\$\("),          # 命令替换
        ("ifs_injection", r"\bIFS\s*="),        # IFS 注入
    ]

    def validate(self, command: str) -> list:
        """
        使用全部校验器检查 bash 命令。

        返回失败列表：`(validator_name, matched_pattern)` 元组。
        返回空列表表示全部通过。
        """
        failures = []
        for name, pattern in self.VALIDATORS:
            if re.search(pattern, command):
                failures.append((name, pattern))
        return failures

    def is_safe(self, command: str) -> bool:
        """便捷接口：仅当无命中规则时返回 True。"""
        return len(self.validate(command)) == 0

    def describe_failures(self, command: str) -> str:
        """输出可读的校验失败摘要。"""
        failures = self.validate(command)
        if not failures:
            return "未发现安全问题"
        parts = [f"{name} (pattern: {pattern})" for name, pattern in failures]
        return "安全标记： " + ", ".join(parts)


# -- Workspace 信任状态 --
def is_workspace_trusted(workspace: Path = None) -> bool:
    """
    检查工作区是否被显式标记为 trusted（可信）。

    教学版使用简单标记文件。生产系统可在同一思路上叠加更丰富的信任流程。
    """
    ws = workspace or WORKDIR
    trust_marker = ws / ".claude" / ".claude_trusted"
    return trust_marker.exists()


# 权限管线复用的单例校验器
bash_validator = BashSecurityValidator()


# -- 权限规则 --
# 规则按顺序匹配：first match wins（首条命中生效）。
# 结构：{"tool": "<tool_name_or_*>", "path": "<glob_or_*>", "behavior": "allow|deny|ask"}
DEFAULT_RULES = [
    # 永久拒绝高危模式
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},
    {"tool": "bash", "content": "sudo *", "behavior": "deny"},
    # 允许任意读取
    {"tool": "read_file", "path": "*", "behavior": "allow"},
]


class PermissionManager:
    """
    管理工具调用的权限决策。

    决策管线：deny_rules -> mode_check -> allow_rules -> ask_user

    教学版故意保持路径精简，便于读者先自行实现，再叠加进阶策略层。
    """

    def __init__(self, mode: str = "default", rules: list = None):
        if mode not in MODES:
            raise ValueError(f"未知模式: {mode}。可选值：{MODES}")
        self.mode = mode
        self.rules = rules or list(DEFAULT_RULES)
        # 连续拒绝计数可暴露“模型持续请求被禁止动作”的状态。
        self.consecutive_denials = 0
        self.max_consecutive_denials = 3

    def check(self, tool_name: str, tool_input: dict) -> dict:
        """
        返回：{"behavior": "allow"|"deny"|"ask", "reason": str}
        """
        # Step 0: Bash 安全校验（先于 deny 规则）
        # 教学版前置校验，保证流程可读性。
        if tool_name == "bash":
            command = tool_input.get("command", "")
            failures = bash_validator.validate(command)
            if failures:
                # 严重模式（sudo, rm_rf）立即拒绝
                severe = {"sudo", "rm_rf"}
                severe_hits = [f for f in failures if f[0] in severe]
                if severe_hits:
                    desc = bash_validator.describe_failures(command)
                    return {"behavior": "deny",
                            "reason": f"Bash 校验器: {desc}"}
                # 其他模式升级为 ask（仍允许用户批准）
                desc = bash_validator.describe_failures(command)
                return {"behavior": "ask",
                        "reason": f"Bash 校验命中：{desc}"}

        # Step 1: Deny 规则（不可绕过，永远最先检查）
        for rule in self.rules:
            if rule["behavior"] != "deny":
                continue
            if self._matches(rule, tool_name, tool_input):
                return {"behavior": "deny",
                        "reason": f"命中 deny 规则并被拦截：{rule}"}

        # Step 2: 基于 mode 的决策
        if self.mode == "plan":
            # Plan 模式：拒绝写操作，仅允许读取
            if tool_name in WRITE_TOOLS:
                return {"behavior": "deny",
                        "reason": "Plan 模式：写操作被阻止"}
            return {"behavior": "allow", "reason": "Plan 模式：允许只读操作"}

        if self.mode == "auto":
            # Auto 模式：只读自动放行，写入请求走询问
            if tool_name in READ_ONLY_TOOLS or tool_name == "read_file":
                return {"behavior": "allow",
                        "reason": "Auto 模式：只读工具自动批准"}
            # 教学版：继续走 allow 规则，最后再 ask
            pass

        # Step 3: Allow 规则
        for rule in self.rules:
            if rule["behavior"] != "allow":
                continue
            if self._matches(rule, tool_name, tool_input):
                self.consecutive_denials = 0
                return {"behavior": "allow",
                        "reason": f"命中 allow 规则：{rule}"}

        # Step 4: Ask user（未命中规则时的默认行为）
        return {"behavior": "ask",
                "reason": f"{tool_name} 未命中任何规则，转为询问用户"}

    def ask_user(self, tool_name: str, tool_input: dict) -> bool:
        """交互式批准流程：用户批准返回 True。"""
        preview = json.dumps(tool_input, ensure_ascii=False)[:200]
        print(f"\n  [Permission] {tool_name}: {preview}")
        try:
            answer = input("  是否允许？(y/n/always): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if answer == "always":
            # 为该工具添加持久 allow 规则
            self.rules.append({"tool": tool_name, "path": "*", "behavior": "allow"})
            self.consecutive_denials = 0
            return True
        if answer in ("y", "yes"):
            self.consecutive_denials = 0
            return True

        # 连续拒绝计数（可视作简化断路器）
        self.consecutive_denials += 1
        if self.consecutive_denials >= self.max_consecutive_denials:
            print(f"  [{self.consecutive_denials} consecutive denials -- "
                  "建议切换到 plan 模式]")
        return False

    def _matches(self, rule: dict, tool_name: str, tool_input: dict) -> bool:
        """检查规则是否匹配当前工具调用。"""
        # 工具名匹配
        if rule.get("tool") and rule["tool"] != "*":
            if rule["tool"] != tool_name:
                return False
        # 路径匹配
        if "path" in rule and rule["path"] != "*":
            path = tool_input.get("path", "")
            if not fnmatch(path, rule["path"]):
                return False
        # 内容匹配（主要用于 bash 命令）
        if "content" in rule:
            command = tool_input.get("command", "")
            if not fnmatch(command, rule["content"]):
                return False
        return True


# -- 工具实现 --
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
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
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


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

TOOLS = [
    {"name": "bash", "description": "执行 shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "向文件写入内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中替换精确文本。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
]

SYSTEM = f"""你是位于 {WORKDIR} 的 coding agent（编码智能体），请使用工具解决任务。
权限由用户控制，部分工具调用可能会被拒绝。"""


def agent_loop(messages: list, perms: PermissionManager):
    """
    带权限感知的智能体循环。

    每次工具调用都遵循：
      1. LLM 发起 tool_use（工具调用）请求；
      2. 权限管线检查：deny_rules -> mode -> allow_rules -> ask；
      3. 若允许：执行工具并返回结果；
      4. 若拒绝：向 LLM 返回拒绝信息。
    """
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
            if block.type != "tool_use":
                continue

            # -- 权限检查 --
            decision = perms.check(block.name, block.input or {})

            if decision["behavior"] == "deny":
                output = f"Permission denied: {decision['reason']}"
                print(f"  [DENIED] {block.name}: {decision['reason']}")

            elif decision["behavior"] == "ask":
                if perms.ask_user(block.name, block.input or {}):
                    handler = TOOL_HANDLERS.get(block.name)
                    output = handler(**(block.input or {})) if handler else f"Unknown: {block.name}"
                    print(f"> {block.name}: {str(output)[:200]}")
                else:
                    output = f"用户拒绝了工具：{block.name}"
                    print(f"  [USER DENIED] {block.name}")

            else:  # allow（允许执行）
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**(block.input or {})) if handler else f"Unknown: {block.name}"
                print(f"> {block.name}: {str(output)[:200]}")

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output),
            })

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    # 启动时选择权限模式
    print("权限模式：default, plan, auto")
    mode_input = input("模式（默认 default）: ").strip().lower() or "default"
    if mode_input not in MODES:
        mode_input = "default"

    perms = PermissionManager(mode=mode_input)
    print(f"[当前权限模式: {mode_input}]")

    history = []
    while True:
        try:
            query = input("\033[36ms07 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        # /mode 命令：运行中切换模式
        if query.startswith("/mode"):
            parts = query.split()
            if len(parts) == 2 and parts[1] in MODES:
                perms.mode = parts[1]
                print(f"[已切换到 {parts[1]} 模式]")
            else:
                print(f"用法: /mode <{'|'.join(MODES)}>")
            continue

        # /rules 命令：查看当前规则
        if query.strip() == "/rules":
            for i, rule in enumerate(perms.rules):
                print(f"  {i}: {rule}")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history, perms)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
