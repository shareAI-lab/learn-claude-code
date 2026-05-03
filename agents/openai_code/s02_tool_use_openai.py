#!/usr/bin/env python3
# Harness: tool dispatch -- expanding what the model can reach.
"""
s02_tool_use.py - Tools (OpenAI 版本)

将 Anthropic 接口转换为 OpenAI 接口，支持多工具调用。
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 在文件开头设置
os.environ['PYTHONPATH'] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")

# 工作目录
WORKDIR = Path.cwd()

# 初始化 OpenAI 客户端（兼容阿里云百炼）
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)
MODEL = os.getenv("OPENAI_MODEL_ID")

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


def safe_path(p: str) -> Path:
    """确保路径在安全工作目录内"""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    """执行 shell 命令"""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"

    try:
        if sys.platform == "win32":
            r = subprocess.run(
                command, shell=True, cwd=WORKDIR,
                capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace'
            )
        else:
            r = subprocess.run(
                command, shell=True, cwd=WORKDIR,
                capture_output=True, text=True, timeout=120,
                executable='/bin/bash'
            )

        stdout = r.stdout if r.stdout is not None else ""
        stderr = r.stderr if r.stderr is not None else ""
        out = (stdout + stderr).strip()
        return out[:50000] if out else "(no output)"

    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    """读取文件内容"""
    try:
        text = safe_path(path).read_text(encoding='utf-8', errors='replace')
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """写入文件"""
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding='utf-8')
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """编辑文件（替换文本）"""
    try:
        fp = safe_path(path)
        content = fp.read_text(encoding='utf-8')
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1), encoding='utf-8')
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# -- 工具处理函数映射 --
TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

# -- OpenAI function calling 格式的工具定义 --
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "limit": {"type": "integer", "description": "Maximum number of lines to read"}
                },
                "required": ["path"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "old_text": {"type": "string", "description": "Text to replace"},
                    "new_text": {"type": "string", "description": "New text to insert"}
                },
                "required": ["path", "old_text", "new_text"],
            },
        }
    },
]





def agent_loop(messages: List[Dict[str, Any]]):
    """
    Agent 主循环：调用模型，执行工具，直到模型不再请求工具
    """
    while True:
        # 调用 OpenAI API
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )

        # 获取 assistant 的回复
        assistant_message = response.choices[0].message

        # 将 assistant 消息添加到历史
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": assistant_message.tool_calls
        })

        # 如果没有工具调用，结束循环
        if not assistant_message.tool_calls:
            return

        # 执行每个工具调用
        results = []
        for tool_call in assistant_message.tool_calls:
            # 获取工具名称和参数
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # 查找并执行对应的处理函数
            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                print(f"> {tool_name}:")
                output = handler(**arguments)
                print(output[:200])
            else:
                output = f"Unknown tool: {tool_name}"
                print(f"> {tool_name}: Unknown tool")

            # 添加工具结果
            results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output
            })

        # 将所有工具结果添加到消息历史
        messages.extend(results)


def print_response(messages: List[Dict[str, Any]]):
    """打印最终回复内容"""
    if not messages:
        return

    last_message = messages[-1]
    if last_message.get("role") == "assistant":
        content = last_message.get("content")
        if content:
            print(content)
    elif last_message.get("role") == "tool":
        # 如果最后一个是工具结果，打印前一条 assistant 消息
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                print(msg["content"])
                break


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        # 添加用户消息
        history.append({"role": "user", "content": query})

        # 运行 agent 循环
        agent_loop(history)

        # 打印回复
        print_response(history)
        print()