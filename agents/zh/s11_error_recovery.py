#!/usr/bin/env python3
# Harness（执行框架）: resilience（韧性）——稳健智能体应恢复而非崩溃。
"""
s11_error_recovery.py - Error Recovery（错误恢复）

教学版展示三条恢复路径：

- 输出被截断时继续（continue when output is truncated）
- 上下文过大时压缩（compact when context grows too large）
- 传输层临时错误时退避重试（back off when transport errors are temporary）

    LLM 响应（response）
         |
         v
    [检查 stop_reason]
         |
         +-- "max_tokens" ----> [策略 1：max_output_tokens 恢复]
         |                       注入续写消息：
         |                       "Output limit hit. Continue directly."（达到输出上限，请直接续写）
         |                       最多重试 MAX_RECOVERY_ATTEMPTS（3）次
         |                       计数器：max_output_recovery_count
         |
         +-- API error -------> [检查错误类型]
         |                       |
         |                       +-- prompt_too_long --> [策略 2：压缩后重试]
         |                       |   触发 auto_compact（LLM 摘要）
         |                       |   用摘要替换历史
         |                       |   重试当前轮
         |                       |
         |                       +-- connection/rate --> [策略 3：退避重试]
         |                           指数退避：base * 2^attempt + jitter
         |                           最多重试 3 次
         |
         +-- "end_turn" -----> [正常结束]

    恢复优先级（first match wins，首条命中）：
    1. max_tokens -> 注入续写消息并重试
    2. prompt_too_long -> 压缩并重试
    3. connection error -> 退避并重试
    4. 全部重试耗尽 -> 优雅失败
"""

import json
import os
import random
import subprocess
import time
from pathlib import Path

try:
    from agents.llm_client import APIError, create_client
except ModuleNotFoundError:
    from llm_client import APIError, create_client
from dotenv import load_dotenv

load_dotenv(override=True)


WORKDIR = Path.cwd()
client = create_client()
MODEL = os.environ["MODEL_ID"]

# 恢复相关常量
MAX_RECOVERY_ATTEMPTS = 3
BACKOFF_BASE_DELAY = 1.0  # 秒
BACKOFF_MAX_DELAY = 30.0  # 秒
TOKEN_THRESHOLD = 50000   # chars（字符）/4 ≈ tokens（token），用于压缩触发

CONTINUATION_MESSAGE = (
    "输出达到上限，请从中断处直接继续。"
    "不要复述，不要重复，必要时可从句中继续。"
)


def estimate_tokens(messages: list) -> int:
    """粗略估算 token：约 4 个字符 ≈ 1 token。"""
    return len(json.dumps(messages, default=str)) // 4


def auto_compact(messages: list) -> list:
    """
    将会话历史压缩为可续写的短摘要。
    """
    conversation_text = json.dumps(messages, default=str)[:80000]
    prompt = (
        "请为延续执行总结这段会话，包含：\n"
        "1) 任务概览与成功标准\n"
        "2) 当前状态：已完成工作、涉及文件\n"
        "3) 关键决策与失败尝试\n"
        "4) 剩余下一步\n"
        "请保持简洁但保留关键细节。\n\n"
        + conversation_text
    )
    try:
        response = client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        summary = response.content[0].text
    except Exception as e:
        summary = f"（compact 失败：{e}）。此前上下文已丢失。"

    continuation = (
        "当前会话承接自已 compact 的历史会话。"
        f"先前上下文摘要如下：\n\n{summary}\n\n"
        "请直接从中断点继续，不要重复向用户提问。"
    )
    return [{"role": "user", "content": continuation}]


def backoff_delay(attempt: int) -> float:
    """指数退避 + 抖动：base * 2^attempt + random(0, 1)。"""
    delay = min(BACKOFF_BASE_DELAY * (2 ** attempt), BACKOFF_MAX_DELAY)
    jitter = random.uniform(0, 1)
    return delay + jitter


# -- 工具实现 --
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


def agent_loop(messages: list):
    """
    带三类恢复路径的智能体循环：

    1. max_tokens 后续写恢复
    2. prompt 过长后 compact 恢复
    3. 瞬时传输故障后退避重试
    """
    max_output_recovery_count = 0

    while True:
        # -- 尝试 API 调用（含连接重试） --
        response = None
        for attempt in range(MAX_RECOVERY_ATTEMPTS + 1):
            try:
                response = client.messages.create(
                    model=MODEL, system=SYSTEM, messages=messages,
                    tools=TOOLS, max_tokens=8000,
                )
                break  # success（成功）

            except APIError as e:
                error_body = str(e).lower()

                # 策略 2：prompt_too_long -> compact 后重试
                if "overlong_prompt" in error_body or ("prompt" in error_body and "long" in error_body):
                    print(f"[Recovery] 提示词过长，正在压缩...（第 {attempt + 1} 次）")
                    messages[:] = auto_compact(messages)
                    continue

                # 策略 3：连接/限流错误 -> 退避重试
                if attempt < MAX_RECOVERY_ATTEMPTS:
                    delay = backoff_delay(attempt)
                    print(f"[Recovery] API 错误：{e}。"
                          f"将在 {delay:.1f}s 后重试（第 {attempt + 1}/{MAX_RECOVERY_ATTEMPTS} 次）")
                    time.sleep(delay)
                    continue

                # 重试耗尽
                print(f"[Error] API 调用在重试 {MAX_RECOVERY_ATTEMPTS} 次后仍失败：{e}")
                return

            except (ConnectionError, TimeoutError, OSError) as e:
                # 策略 3：网络层错误 -> 退避重试
                if attempt < MAX_RECOVERY_ATTEMPTS:
                    delay = backoff_delay(attempt)
                    print(f"[Recovery] 连接错误：{e}。"
                          f"将在 {delay:.1f}s 后重试（第 {attempt + 1}/{MAX_RECOVERY_ATTEMPTS} 次）")
                    time.sleep(delay)
                    continue

                print(f"[Error] 连接在重试 {MAX_RECOVERY_ATTEMPTS} 次后仍失败：{e}")
                return

        if response is None:
            print("[Error] 未收到响应。")
            return

        messages.append({"role": "assistant", "content": response.content})

        # -- 策略 1：max_tokens 恢复 --
        if response.stop_reason == "max_tokens":
            max_output_recovery_count += 1
            if max_output_recovery_count <= MAX_RECOVERY_ATTEMPTS:
                print(f"[Recovery] 触发 max_tokens "
                      f"({max_output_recovery_count}/{MAX_RECOVERY_ATTEMPTS}). "
                      "注入 continuation 消息并重试...")
                messages.append({"role": "user", "content": CONTINUATION_MESSAGE})
                continue  # 继续循环重试
            else:
                print(f"[Error] max_tokens recovery exhausted "
                      f"（已尝试 {MAX_RECOVERY_ATTEMPTS} 次）。停止重试。")
                return

        # 非 max_tokens 成功返回后重置计数
        max_output_recovery_count = 0

        # -- 正常 end_turn：未请求工具调用 --
        if response.stop_reason != "tool_use":
            return

        # -- 处理工具调用 --
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**(block.input or {})) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            print(f"> {block.name}: {str(output)[:200]}")
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output),
            })

        messages.append({"role": "user", "content": results})

        # 主动检查是否需要 auto-compact（而非仅被动触发）
        if estimate_tokens(messages) > TOKEN_THRESHOLD:
            print("[Recovery] Token 估算超出阈值，正在自动压缩...")
            messages[:] = auto_compact(messages)


if __name__ == "__main__":
    print("[已启用错误恢复：max_tokens / prompt_too_long / connection backoff]")
    history = []
    while True:
        try:
            query = input("\033[36ms11 >> \033[0m")
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
