#!/usr/bin/env python3
# Harness: the loop -- the model's first connection to the real world.
"""
s01_agent_loop.py - The Agent Loop

"""

import os
import subprocess
import json
import sys

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
    readline.parse_and_bind('set enable-meta-keybindings on')
except ImportError:
    pass

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# 在文件开头设置
os.environ['PYTHONPATH'] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")


# 初始化 OpenAI 客户端（兼容阿里云百炼）
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)
MODEL = os.getenv("OPENAI_MODEL_ID")

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# 转换工具格式为 OpenAI function calling 格式
TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"],
        },
    }
}]


def run_bash(command: str) -> str:
    # 这里可以加强，一些字符绕过检测后可能仍然危险，实际使用中请务必谨慎
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:

        # Windows 下使用 cmd，其他系统使用 bash
        if sys.platform == "win32":
            # Windows 系统
            r = subprocess.run(
                command,
                shell=True,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',  # 明确指定编码
                errors='replace'   # 遇到无法解码的字符时替换
            )
        else:
            # Linux/Mac 系统
            r = subprocess.run(
                command,
                shell=True,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=120,
                executable='/bin/bash'
            )

        # 安全地获取输出，处理 None 的情况
        stdout = r.stdout if r.stdout is not None else ""
        stderr = r.stderr if r.stderr is not None else ""
        out = (stdout + stderr).strip()

        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def agent_loop(messages: list):
    while True:
        # 调用阿里云百炼 API
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                *messages
            ],
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )

        # 获取 assistant 的回复
        assistant_message = response.choices[0].message
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": assistant_message.tool_calls
        })

        # 如果没有 tool_calls，结束循环
        if not assistant_message.tool_calls:
            return
        # 执行每个 tool call
        for tool_call in assistant_message.tool_calls:
            if tool_call.function.name == "bash":
                # 解析命令
                try:
                    command_args = json.loads(tool_call.function.arguments)
                    command = command_args.get("command", "")

                    if not command:
                        output = "Error: No command provided"
                    else:
                        print(f"\033[33m$ {command}\033[0m")
                        output = run_bash(command)
                        print(output[:200])

                    # 添加 tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": output
                    })
                except json.JSONDecodeError as e:
                    error_msg = f"Error parsing command arguments: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_msg
                    })


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        agent_loop(history)

        # 打印最终回复（跳过 tool 消息）
        if history and history[-1]["role"] == "assistant":
            if history[-1]["content"]:
                print(history[-1]["content"])

        print()