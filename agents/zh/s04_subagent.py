#!/usr/bin/env python3
# Harness（执行框架）: context isolation（上下文隔离）——保护模型思路清晰度。
"""
s04_subagent.py - Subagent（子智能体）

通过 fresh `messages=[]` 启动 child agent（子智能体）。
子智能体在独立上下文中工作、共享同一文件系统，最后只把摘要返回给父智能体。

    父智能体（Parent agent）              子智能体（Subagent）
    +------------------+             +------------------+
    | messages=[...]   |             | messages=[]      |  <-- fresh（新上下文）
    |                  | dispatch（派发）|                |
    | 工具: task        | ---------->| while tool_use（工具调用）: |
    | prompt="..."     |            |   call tools（调用工具）     |
    | description=""   |            |   append results（追加结果） |
    |                  | summary（汇总） |                |
    | result = "..."   | <--------- | return last text（返回摘要） |
    +------------------+             +------------------+
              |
    父上下文保持干净，子上下文任务结束后丢弃。

关键洞察：
"fresh messages=[] 就是上下文隔离，父上下文不会被污染。"

注意：真实 Claude Code 也使用 in-process isolation（进程内隔离），
并非操作系统级 fork。子智能体与父智能体在同一进程中运行，
但拥有新的消息数组和隔离的工具上下文，这与本教学实现一致。

    与真实 Claude Code 的对比：
    +-------------------+----------------------+---------------------------------------------+
    | 维度（Aspect）     | 教学实现（This demo） | 真实 Claude Code（Real Claude Code）          |
    +-------------------+----------------------+---------------------------------------------+
    | 后端（Backend）    | 仅 in-process         | 5 种后端：in-process、tmux、iTerm2、fork、remote |
    | 上下文隔离         | fresh messages=[]     | createSubagentContext() 隔离约 20 个字段（tools、 |
    | （Context isolation）|                      | permissions、cwd、env、hooks 等）             |
    | 工具过滤           | 手工挑选               | resolveAgentTools() 从父工具池过滤；allowedTools |
    | （Tool filtering） |                      | 可替代所有 allow 规则                        |
    | 智能体定义         | 代码内硬编码 prompt    | `.claude/agents/*.md` + YAML frontmatter      |
    | （Agent definition）|                     | （模板 AgentTemplate）                        |
    +-------------------+----------------------+---------------------------------------------+
"""

import os
import re
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

SYSTEM = (
    f"你是位于 {WORKDIR} 的 coding agent（编码智能体）。"
    "使用 task 工具委派探索或子任务。"
)
SUBAGENT_SYSTEM = (
    f"你是位于 {WORKDIR} 的 coding subagent（子智能体）。"
    "完成给定任务后，返回清晰摘要。"
)


class AgentTemplate:
    """
    从 markdown frontmatter 解析 agent 定义。

    真实 Claude Code 会从 `.claude/agents/*.md` 读取 agent 定义。
    frontmatter 字段包括：name、tools、disallowedTools、skills、hooks、
    model（模型）、effort（推理力度）、permissionMode（权限模式）、maxTurns（轮次上限）、
    memory（记忆）、isolation（隔离）、color（颜色）、background（后台）、
    initialPrompt（初始提示）、mcpServers（MCP 服务配置）。
    来源通常有三类：built-in、custom（`.claude/agents/`）、plugin-provided。
    """
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.stem
        self.config = {}
        self.system_prompt = ""
        self._parse()

    def _parse(self):
        text = self.path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            self.system_prompt = text
            return
        for line in match.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                self.config[k.strip()] = v.strip()
        self.system_prompt = match.group(2).strip()
        self.name = self.config.get("name", self.name)


# -- 父子共用工具实现 --
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
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

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

# 子智能体使用基础工具，但不含 task（禁止递归再派生）。
CHILD_TOOLS = [
    {"name": "bash", "description": "执行 shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "向文件写入内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中替换精确文本。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
]


# -- 子智能体：新上下文、过滤工具、仅返回摘要 --
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]  # fresh context（新上下文）
    for _ in range(30):  # safety limit（安全轮次上限）
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM, messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    # 仅把最终文本回传父智能体，子上下文整体丢弃。
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no summary)"


# -- 父智能体工具：基础工具 + task 分发器 --
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task", "description": "创建具有新上下文的子智能体。共享文件系统，但不共享会话历史。",
     "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}, "description": {"type": "string", "description": "任务的简短说明"}}, "required": ["prompt"]}},
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=PARENT_TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "task":
                    desc = block.input.get("description", "subtask")
                    prompt = block.input.get("prompt", "")
                    print(f"> task ({desc}): {prompt[:80]}")
                    output = run_subagent(prompt)
                else:
                    handler = TOOL_HANDLERS.get(block.name)
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                print(f"  {str(output)[:200]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
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
