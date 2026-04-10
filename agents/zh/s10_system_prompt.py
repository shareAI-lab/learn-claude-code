#!/usr/bin/env python3
# Harness（执行框架）: assembly（组装）——system prompt 是管线，不是单一字符串。
"""
s10_system_prompt.py - System Prompt（系统提示）构建

本章核心观点：
system prompt 应由清晰分段组装，而不是写成一整块硬编码大文本。

教学版构建管线：
  1. core instructions（核心指令）
  2. tool listing（工具清单）
  3. skill metadata（技能元数据）
  4. memory section（记忆区段）
  5. CLAUDE.md chain（CLAUDE 指令链）
  6. dynamic context（动态上下文）

构建器会把稳定信息与高频变化信息分离，
并用 `DYNAMIC_BOUNDARY` 标记显式展示边界。

逐轮 reminder（提醒）更动态，适合用单独 user-role 的 system reminder 注入，
而不是直接混入稳定提示体。

关键洞察：
"提示词构建是有边界的管线，不是一坨大字符串。"
"""

import datetime
import json
import os
import platform
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

DYNAMIC_BOUNDARY = "=== DYNAMIC_BOUNDARY ==="


class SystemPromptBuilder:
    """
    按独立区段组装 system prompt。

    教学目标是清晰性：
    每个区段只对应一个来源、一个职责。

    这样更易推理、测试，也更易随能力增长演进。
    """

    def __init__(self, workdir: Path = None, tools: list = None):
        self.workdir = workdir or WORKDIR
        self.tools = tools or []
        self.skills_dir = self.workdir / "skills"
        self.memory_dir = self.workdir / ".memory"

    # -- Section 1: Core instructions（核心指令） --
    def _build_core(self) -> str:
        return (
            f"你是运行在 {self.workdir} 的 coding agent（编码智能体）。\n"
            "请使用提供的工具进行探索、读取、写入与编辑文件。\n"
            "先验证再假设；优先读文件，不要凭空猜测。"
        )

    # -- Section 2: Tool listings（工具清单） --
    def _build_tool_listing(self) -> str:
        if not self.tools:
            return ""
        lines = ["# 可用工具"]
        for tool in self.tools:
            props = tool.get("input_schema", {}).get("properties", {})
            params = ", ".join(props.keys())
            lines.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(lines)

    # -- Section 3: Skill metadata（技能元数据，s05 的第 1 层） --
    def _build_skill_listing(self) -> str:
        if not self.skills_dir.exists():
            return ""
        skills = []
        for skill_dir in sorted(self.skills_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            text = skill_md.read_text()
            # 解析 frontmatter：name + description
            match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not match:
                continue
            meta = {}
            for line in match.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            name = meta.get("name", skill_dir.name)
            desc = meta.get("description", "")
            skills.append(f"- {name}: {desc}")
        if not skills:
            return ""
        return "# 可用技能\n" + "\n".join(skills)

    # -- Section 4: Memory content（记忆内容） --
    def _build_memory_section(self) -> str:
        if not self.memory_dir.exists():
            return ""
        memories = []
        for md_file in sorted(self.memory_dir.glob("*.md")):
            if md_file.name == "MEMORY.md":
                continue
            text = md_file.read_text()
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
            if not match:
                continue
            header, body = match.group(1), match.group(2).strip()
            meta = {}
            for line in header.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            name = meta.get("name", md_file.stem)
            mem_type = meta.get("type", "project")
            desc = meta.get("description", "")
            memories.append(f"[{mem_type}] {name}: {desc}\n{body}")
        if not memories:
            return ""
        return "# 记忆（持久化）\n\n" + "\n\n".join(memories)

    # -- Section 5: CLAUDE.md chain（链式指令） --
    def _build_claude_md(self) -> str:
        """
        按优先级加载 CLAUDE.md（全部纳入）：
        1. ~/.claude/CLAUDE.md（用户全局指令）
        2. <project-root>/CLAUDE.md（项目指令）
        3. <current-subdir>/CLAUDE.md（目录特定指令）
        """
        sources = []

        # 用户全局
        user_claude = Path.home() / ".claude" / "CLAUDE.md"
        if user_claude.exists():
            sources.append(("用户全局（~/.claude/CLAUDE.md）", user_claude.read_text()))

        # 项目根目录
        project_claude = self.workdir / "CLAUDE.md"
        if project_claude.exists():
            sources.append(("项目根目录（project root / CLAUDE.md）", project_claude.read_text()))

        # 子目录：真实 CC 会从 cwd 向上遍历到项目根；
        # 教学版简化为仅在 cwd != workdir 时检查一次。
        cwd = Path.cwd()
        if cwd != self.workdir:
            subdir_claude = cwd / "CLAUDE.md"
            if subdir_claude.exists():
                sources.append((f"子目录（subdir / {cwd.name}/CLAUDE.md）", subdir_claude.read_text()))

        if not sources:
            return ""
        parts = ["# CLAUDE.md 指令"]
        for label, content in sources:
            parts.append(f"## 来源: {label}")
            parts.append(content.strip())
        return "\n\n".join(parts)

    # -- Section 6: Dynamic context（动态上下文） --
    def _build_dynamic_context(self) -> str:
        lines = [
            f"当前日期: {datetime.date.today().isoformat()}",
            f"工作目录: {self.workdir}",
            f"模型（Model）: {MODEL}",
            f"平台（Platform）: {platform.system()}",
        ]
        return "# 动态上下文\n" + "\n".join(lines)

    # -- Assemble all sections（组装全部区段） --
    def build(self) -> str:
        """
        从全部区段组装完整 system prompt。

        静态区段（1-5）与动态区段（6）由 `DYNAMIC_BOUNDARY` 分隔。
        在真实 CC 中，静态前缀可跨轮缓存以节省 token。
        """
        sections = []

        core = self._build_core()
        if core:
            sections.append(core)

        tools = self._build_tool_listing()
        if tools:
            sections.append(tools)

        skills = self._build_skill_listing()
        if skills:
            sections.append(skills)

        memory = self._build_memory_section()
        if memory:
            sections.append(memory)

        claude_md = self._build_claude_md()
        if claude_md:
            sections.append(claude_md)

        # 静态/动态边界
        sections.append(DYNAMIC_BOUNDARY)

        dynamic = self._build_dynamic_context()
        if dynamic:
            sections.append(dynamic)

        return "\n\n".join(sections)


def build_system_reminder(extra: str = None) -> dict:
    """
    为逐轮动态内容构建 system-reminder 用户消息。

    教学版将 reminder 放在稳定 system prompt 之外，
    避免短时上下文污染长期指令。
    """
    parts = []
    if extra:
        parts.append(extra)
    if not parts:
        return None
    content = "<system-reminder>\n" + "\n".join(parts) + "\n</system-reminder>"
    return {"role": "user", "content": content}


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

# 全局 prompt 构建器
prompt_builder = SystemPromptBuilder(workdir=WORKDIR, tools=TOOLS)


def agent_loop(messages: list):
    """
    使用组装式 system prompt 的智能体循环。

    每轮都会重建 system prompt。真实 CC 中静态前缀会被缓存，
    每轮只更新动态后缀。
    """
    while True:
        system = prompt_builder.build()
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

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


if __name__ == "__main__":
    # 启动时展示组装后的 prompt（教学可视化）
    full_prompt = prompt_builder.build()
    section_count = full_prompt.count("\n# ")
    print(f"[System prompt 已组装: {len(full_prompt)} 字符，约 {section_count} 个区段]")

    # /prompt 命令：查看完整组装结果
    history = []
    while True:
        try:
            query = input("\033[36ms10 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        if query.strip() == "/prompt":
            print("--- System Prompt（系统提示）---")
            print(prompt_builder.build())
            print("--- 结束 ---")
            continue

        if query.strip() == "/sections":
            prompt = prompt_builder.build()
            for line in prompt.splitlines():
                if line.startswith("# ") or line == DYNAMIC_BOUNDARY:
                    print(f"  {line}")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
