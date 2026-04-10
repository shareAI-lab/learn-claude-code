#!/usr/bin/env python3
# Harness（执行框架）: extensibility（可扩展性）——不改主循环即可注入行为。
"""
s08_hook_system.py - Hook System（钩子系统）

Hook（钩子）是主循环周边的扩展点。
它允许在不重写循环的前提下增量添加行为。

教学版包含：
  - SessionStart（会话开始）
  - PreToolUse（工具调用前）
  - PostToolUse（工具调用后）

教学版退出码约定：
  - 0 -> continue（继续）
  - 1 -> block（阻断）
  - 2 -> inject a message（注入消息）

这里刻意简化于生产系统，先把扩展模式讲清楚，再进入事件级边界细节。

关键洞察：
"不改主循环，也能扩展智能体。"
"""

import json
import os
import subprocess
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

# 教学版仅保留最清晰的三个事件；完整系统可继续扩展事件面。

HOOK_EVENTS = ("PreToolUse", "PostToolUse", "SessionStart")
HOOK_TIMEOUT = 30  # 秒
# 真实 Claude Code 的超时配置：
#   TOOL_HOOK_EXECUTION_TIMEOUT_MS = 600000（工具 hook 10 分钟）
#   SESSION_END_HOOK_TIMEOUT_MS = 1500（SessionEnd hook 1.5 秒）

# 工作区信任标记。仅在该文件存在（或 SDK 模式）时运行 hooks。
TRUST_MARKER = WORKDIR / ".claude" / ".claude_trusted"


class HookManager:
    """
    从 `.hooks.json` 加载并执行 hooks。

    hook 管理器的三个核心职责：
    - 加载 hook 定义
    - 按事件执行匹配命令
    - 聚合 block/message 结果供调用方处理
    """

    def __init__(self, config_path: Path = None, sdk_mode: bool = False):
        self.hooks = {"PreToolUse": [], "PostToolUse": [], "SessionStart": []}
        self._sdk_mode = sdk_mode
        config_path = config_path or (WORKDIR / ".hooks.json")
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                for event in HOOK_EVENTS:
                    self.hooks[event] = config.get("hooks", {}).get(event, [])
                print(f"[Hooks loaded from {config_path}]")
            except Exception as e:
                print(f"[Hook config error: {e}]")

    def _check_workspace_trust(self) -> bool:
        """
        检查当前工作区是否 trusted（可信）。

        教学版使用简单信任标记文件；
        SDK 模式下默认视为可信。
        """
        if self._sdk_mode:
            return True
        return TRUST_MARKER.exists()

    def run_hooks(self, event: str, context: dict = None) -> dict:
        """
        执行某事件对应的所有 hooks。

        返回：{"blocked": bool, "messages": list[str]}
          - blocked: 任一 hook 返回退出码 1 时为 True
          - messages: 收集退出码 2 的 stderr 内容（可注入会话）
        """
        result = {"blocked": False, "messages": []}

        # 信任门控：不可信工作区不执行 hooks
        if not self._check_workspace_trust():
            return result

        hooks = self.hooks.get(event, [])

        for hook_def in hooks:
            # 检查 matcher（主要用于 PreToolUse/PostToolUse 的工具名过滤）
            matcher = hook_def.get("matcher")
            if matcher and context:
                tool_name = context.get("tool_name", "")
                if matcher != "*" and matcher != tool_name:
                    continue

            command = hook_def.get("command", "")
            if not command:
                continue

            # 构建 hook 执行环境变量
            env = dict(os.environ)
            if context:
                env["HOOK_EVENT"] = event
                env["HOOK_TOOL_NAME"] = context.get("tool_name", "")
                env["HOOK_TOOL_INPUT"] = json.dumps(
                    context.get("tool_input", {}), ensure_ascii=False)[:10000]
                if "tool_output" in context:
                    env["HOOK_TOOL_OUTPUT"] = str(
                        context["tool_output"])[:10000]

            try:
                r = subprocess.run(
                    command, shell=True, cwd=WORKDIR, env=env,
                    capture_output=True, text=True, timeout=HOOK_TIMEOUT,
                )

                if r.returncode == 0:
                    # 正常继续
                    if r.stdout.strip():
                        print(f"  [hook:{event}] {r.stdout.strip()[:100]}")

                    # 可选结构化 stdout：在保持教学契约简洁的前提下提供扩展点。
                    try:
                        hook_output = json.loads(r.stdout)
                        if "updatedInput" in hook_output and context:
                            context["tool_input"] = hook_output["updatedInput"]
                        if "additionalContext" in hook_output:
                            result["messages"].append(
                                hook_output["additionalContext"])
                        if "permissionDecision" in hook_output:
                            result["permission_override"] = (
                                hook_output["permissionDecision"])
                    except (json.JSONDecodeError, TypeError):
                        pass  # stdout 非 JSON，属于常见简化 hook 形态

                elif r.returncode == 1:
                    # 阻断执行
                    result["blocked"] = True
                    reason = r.stderr.strip() or "Blocked by hook"
                    result["block_reason"] = reason
                    print(f"  [hook:{event}] BLOCKED: {reason[:200]}")

                elif r.returncode == 2:
                    # 注入消息
                    msg = r.stderr.strip()
                    if msg:
                        result["messages"].append(msg)
                        print(f"  [hook:{event}] INJECT: {msg[:200]}")

            except subprocess.TimeoutExpired:
                print(f"  [hook:{event}] Timeout ({HOOK_TIMEOUT}s)")
            except Exception as e:
                print(f"  [hook:{event}] Error: {e}")

        return result


# -- 工具实现（与 s02 相同） --
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

SYSTEM = f"你是位于 {WORKDIR} 的 coding agent（编码智能体），请使用工具解决任务。"


def agent_loop(messages: list, hooks: HookManager):
    """
    带 hook 感知的智能体循环。

    教学版只保留最清晰的接入点：
    SessionStart、PreToolUse、工具执行、PostToolUse。
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

            tool_input = dict(block.input or {})
            ctx = {"tool_name": block.name, "tool_input": tool_input}

            # -- PreToolUse hooks（前置工具 hook） --
            pre_result = hooks.run_hooks("PreToolUse", ctx)

            # 将 hook 消息注入 tool_result
            for msg in pre_result.get("messages", []):
                results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": f"[Hook 消息]: {msg}",
                })

            if pre_result.get("blocked"):
                reason = pre_result.get("block_reason", "被 hook 拦截")
                output = f"工具被 PreToolUse hook 拦截：{reason}"
                results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": output,
                })
                continue

            # -- 执行工具 --
            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**tool_input) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            print(f"> {block.name}: {str(output)[:200]}")

            # -- PostToolUse hooks（后置工具 hook） --
            ctx["tool_output"] = output
            post_result = hooks.run_hooks("PostToolUse", ctx)

            # 注入 post-hook 消息
            for msg in post_result.get("messages", []):
                output += f"\n[Hook note]: {msg}"

            results.append({
                "type": "tool_result", "tool_use_id": block.id,
                "content": str(output),
            })

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    hooks = HookManager()

    # 触发 SessionStart hooks
    hooks.run_hooks("SessionStart", {"tool_name": "", "tool_input": {}})

    history = []
    while True:
        try:
            query = input("\033[36ms08 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history, hooks)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
