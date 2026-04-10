#!/usr/bin/env python3
# Harness（执行框架）: persistence（持久化）——跨会话边界保留记忆。
"""
s09_memory_system.py - Memory System（记忆系统）

本教学版聚焦一个核心观点：
有些信息应该跨会话保留，但并非所有内容都适合进入 memory（记忆）。

建议写入 memory 的内容：
  - user preferences（用户偏好）
  - repeated user feedback（反复出现的用户反馈）
  - project facts that are NOT obvious from the current code（无法直接从当前代码显见的项目事实）
  - pointers to external resources（外部资源指针）

不应写入 memory 的内容：
  - code structure that can be re-read from the repo（可从仓库重新读取的代码结构）
  - temporary task state（临时任务状态）
  - secrets（敏感密钥与口令）

存储结构：
  .memory/
    MEMORY.md
    prefer_tabs.md
    review_style.md
    incident_board.md

每条 memory 是带 frontmatter 的小型 Markdown 文件。
智能体可通过 `save_memory()` 写入记忆，每次写入后会重建 memory 索引。

可选的 “Dream” 流程可在后续执行归并、去重和清理。
它很有用，但不是初学阶段第一优先。

关键洞察：
"Memory 只保存跨会话仍有价值、且不易从当前仓库直接再推导的信息。"
"""

import json
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

MEMORY_DIR = WORKDIR / ".memory"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
MEMORY_TYPES = ("user", "feedback", "project", "reference")
MAX_INDEX_LINES = 200


class MemoryManager:
    """
    跨会话加载、构建并保存持久记忆。

    教学版采用显式结构：
    每条记忆一个 Markdown 文件，外加一个紧凑索引文件。
    """

    def __init__(self, memory_dir: Path = None):
        self.memory_dir = memory_dir or MEMORY_DIR
        self.memories = {}  # name（名称）-> {description, type, content}

    def load_all(self):
        """加载 MEMORY.md 索引及全部记忆文件。"""
        self.memories = {}
        if not self.memory_dir.exists():
            return

        # 扫描除 MEMORY.md 外的所有 .md 文件
        for md_file in sorted(self.memory_dir.glob("*.md")):
            if md_file.name == "MEMORY.md":
                continue
            parsed = self._parse_frontmatter(md_file.read_text())
            if parsed:
                name = parsed.get("name", md_file.stem)
                self.memories[name] = {
                    "description": parsed.get("description", ""),
                    "type": parsed.get("type", "project"),
                    "content": parsed.get("content", ""),
                    "file": md_file.name,
                }

        count = len(self.memories)
        if count > 0:
            print(f"[Memory loaded: {count} memories from {self.memory_dir}]")

    def load_memory_prompt(self) -> str:
        """构建用于注入 system prompt 的 memory 区段。"""
        if not self.memories:
            return ""

        sections = []
        sections.append("# 记忆（跨会话持久化）")
        sections.append("")

        # 按类型分组，提升可读性
        for mem_type in MEMORY_TYPES:
            typed = {k: v for k, v in self.memories.items() if v["type"] == mem_type}
            if not typed:
                continue
            sections.append(f"## [{mem_type}]")
            for name, mem in typed.items():
                sections.append(f"### {name}: {mem['description']}")
                if mem["content"].strip():
                    sections.append(mem["content"].strip())
                sections.append("")

        return "\n".join(sections)

    def save_memory(self, name: str, description: str, mem_type: str, content: str) -> str:
        """
        将记忆写入磁盘并更新索引。

        返回状态文本。
        """
        if mem_type not in MEMORY_TYPES:
            return f"Error: type 必须是 {MEMORY_TYPES} 之一"

        # 文件名安全化
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())
        if not safe_name:
            return "Error: memory 名称无效"

        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 写入单条记忆文件（frontmatter + 正文）
        frontmatter = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"type: {mem_type}\n"
            f"---\n"
            f"{content}\n"
        )
        file_name = f"{safe_name}.md"
        file_path = self.memory_dir / file_name
        file_path.write_text(frontmatter)

        # 更新内存态
        self.memories[name] = {
            "description": description,
            "type": mem_type,
            "content": content,
            "file": file_name,
        }

        # 重建 MEMORY.md 索引
        self._rebuild_index()

        return f"Saved memory '{name}' [{mem_type}] to {file_path.relative_to(WORKDIR)}"

    def _rebuild_index(self):
        """根据当前内存态重建 MEMORY.md，并限制在 200 行内。"""
        lines = ["# Memory Index", ""]
        for name, mem in self.memories.items():
            lines.append(f"- {name}: {mem['description']} [{mem['type']}]")
            if len(lines) >= MAX_INDEX_LINES:
                lines.append(f"... (truncated at {MAX_INDEX_LINES} lines)")
                break
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        MEMORY_INDEX.write_text("\n".join(lines) + "\n")

    def _parse_frontmatter(self, text: str) -> dict | None:
        """解析 `---` 分隔的 frontmatter 与正文内容。"""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            return None
        header, body = match.group(1), match.group(2)
        result = {"content": body.strip()}
        for line in header.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
        return result


class DreamConsolidator:
    """
    会话间记忆自动归并（Dream）。

    这是可选的后续能力，用于防止 memory 仓库长期膨胀成噪声集合：
    通过合并、去重、清理维持记忆质量。
    """

    COOLDOWN_SECONDS = 86400       # 归并之间至少间隔 24 小时
    SCAN_THROTTLE_SECONDS = 600    # 扫描尝试之间至少间隔 10 分钟
    MIN_SESSION_COUNT = 5          # 至少积累足够会话数据再归并
    LOCK_STALE_SECONDS = 3600      # PID 锁超过 1 小时视为陈旧

    PHASES = [
        "Orient（定向）: 扫描 MEMORY.md 索引，识别结构与分类",
        "Gather（采集）: 读取各记忆文件，获取完整内容",
        "Consolidate（归并）: 合并相关记忆并移除过期条目",
        "Prune（裁剪）: 将 MEMORY.md 索引控制在 200 行以内",
    ]

    def __init__(self, memory_dir: Path = None):
        self.memory_dir = memory_dir or MEMORY_DIR
        self.lock_file = self.memory_dir / ".dream_lock"
        self.enabled = True
        self.mode = "default"
        self.last_consolidation_time = 0.0
        self.last_scan_time = 0.0
        self.session_count = 0

    def should_consolidate(self) -> tuple[bool, str]:
        """
        顺序检查 7 个 gate（闸门），全部通过才允许执行。
        返回 `(can_run, reason)`，reason 表示首个未通过闸门。
        """
        import time

        now = time.time()

        # Gate 1: enabled 开关
        if not self.enabled:
            return False, "Gate 1: consolidation（归并）已禁用"

        # Gate 2: memory 目录存在且包含记忆文件
        if not self.memory_dir.exists():
            return False, "Gate 2: memory 目录不存在"
        memory_files = list(self.memory_dir.glob("*.md"))
        # 统计时排除 MEMORY.md 本身
        memory_files = [f for f in memory_files if f.name != "MEMORY.md"]
        if not memory_files:
            return False, "Gate 2: 未找到 memory 文件"

        # Gate 3: 非 plan 模式（仅在活跃模式允许归并）
        if self.mode == "plan":
            return False, "Gate 3: plan 模式不允许归并"

        # Gate 4: 距离上次归并满足 24 小时冷却
        time_since_last = now - self.last_consolidation_time
        if time_since_last < self.COOLDOWN_SECONDS:
            remaining = int(self.COOLDOWN_SECONDS - time_since_last)
            return False, f"Gate 4: cooldown active, {remaining}s remaining"

        # Gate 5: 距离上次扫描满足 10 分钟节流
        time_since_scan = now - self.last_scan_time
        if time_since_scan < self.SCAN_THROTTLE_SECONDS:
            remaining = int(self.SCAN_THROTTLE_SECONDS - time_since_scan)
            return False, f"Gate 5: 扫描节流生效，还需等待 {remaining}s"

        # Gate 6: 至少需要 5 个会话的数据积累
        if self.session_count < self.MIN_SESSION_COUNT:
            return False, f"Gate 6: only {self.session_count} sessions, need {self.MIN_SESSION_COUNT}"

        # Gate 7: 无活跃锁文件（并检查 PID 锁是否过期）
        if not self._acquire_lock():
            return False, "Gate 7: 锁被其他进程持有"

        return True, "All 7 gates passed"

    def consolidate(self) -> list[str]:
        """
        执行 4 阶段归并流程。

        教学版直接返回阶段说明，用于可视化流程，
        无需额外 LLM 归并调用。
        """
        import time

        can_run, reason = self.should_consolidate()
        if not can_run:
            print(f"[Dream] 无法归并：{reason}")
            return []

        print("[Dream] 开始执行归并...")
        self.last_scan_time = time.time()

        completed_phases = []
        for i, phase in enumerate(self.PHASES, 1):
            print(f"[Dream] Phase {i}/4: {phase}")
            completed_phases.append(phase)

        self.last_consolidation_time = time.time()
        self._release_lock()
        print(f"[Dream] 归并完成：共执行 {len(completed_phases)} 个阶段")
        return completed_phases

    def _acquire_lock(self) -> bool:
        """
        申请基于 PID 的锁文件。
        若被其他活跃进程持有则返回 False。
        过期锁（超过 LOCK_STALE_SECONDS）会被清除。
        """
        import time

        if self.lock_file.exists():
            try:
                lock_data = self.lock_file.read_text().strip()
                pid_str, timestamp_str = lock_data.split(":", 1)
                pid = int(pid_str)
                lock_time = float(timestamp_str)

                # 检查锁是否过期
                if (time.time() - lock_time) > self.LOCK_STALE_SECONDS:
                    print(f"[Dream] 正在移除 PID {pid} 的陈旧锁")
                    self.lock_file.unlink()
                else:
                    # 检查持锁进程是否仍存活
                    try:
                        os.kill(pid, 0)
                        return False  # 进程仍存活，锁有效
                    except OSError:
                        print(f"[Dream] 正在移除已退出 PID {pid} 的锁")
                        self.lock_file.unlink()
            except (ValueError, OSError):
                # 锁文件损坏，直接删除
                self.lock_file.unlink(missing_ok=True)

        # 写入新锁
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            self.lock_file.write_text(f"{os.getpid()}:{time.time()}")
            return True
        except OSError:
            return False

    def _release_lock(self):
        """若锁归当前进程持有，则释放锁文件。"""
        try:
            if self.lock_file.exists():
                lock_data = self.lock_file.read_text().strip()
                pid_str = lock_data.split(":")[0]
                if int(pid_str) == os.getpid():
                    self.lock_file.unlink()
        except (ValueError, OSError):
            pass


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


# 全局 memory 管理器
memory_mgr = MemoryManager()


def run_save_memory(name: str, description: str, mem_type: str, content: str) -> str:
    return memory_mgr.save_memory(name, description, mem_type, content)


TOOL_HANDLERS = {
    "bash":         lambda **kw: run_bash(kw["command"]),
    "read_file":    lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":   lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":    lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "save_memory":  lambda **kw: run_save_memory(kw["name"], kw["description"], kw["type"], kw["content"]),
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
    {"name": "save_memory", "description": "保存可跨会话保留的持久记忆。",
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "短标识（如 prefer_tabs, db_schema）"},
         "description": {"type": "string", "description": "该记忆的单行摘要"},
         "type": {"type": "string", "enum": ["user", "feedback", "project", "reference"],
                  "description": "user=偏好，feedback=纠正，project=不易从代码直接推断的项目约束/决策原因，reference=外部资源指针"},
         "content": {"type": "string", "description": "记忆正文（可多行）"},
     }, "required": ["name", "description", "type", "content"]}},
]

MEMORY_GUIDANCE = """
何时应保存 memory：
- 用户表达偏好（例如“我喜欢 tabs”“总是用 pytest”）-> type: user
- 用户纠正你（例如“不要这样做”“上次错在……”）-> type: feedback
- 你获得了无法仅凭当前代码快速推断的项目事实
  （例如：某规则源于合规要求、某旧模块因业务原因不能动）-> type: project
- 你确认了外部资源入口（工单看板、监控面板、文档 URL）-> type: reference

何时不应保存：
- 能从代码直接推导出的信息（函数签名、目录结构等）
- 临时任务状态（当前分支、临时 PR 编号、当前 TODO）
- 秘密或凭据（API Key、密码）
"""


def build_system_prompt() -> str:
    """组装包含 memory 内容的 system prompt。"""
    parts = [f"你是位于 {WORKDIR} 的 coding agent（编码智能体），请使用工具解决任务。"]

    # 若存在 memory，则注入记忆区段
    memory_section = memory_mgr.load_memory_prompt()
    if memory_section:
        parts.append(memory_section)

    parts.append(MEMORY_GUIDANCE)
    return "\n\n".join(parts)


def agent_loop(messages: list):
    """
    带 memory 感知的智能体循环。

    每轮都会重建 system prompt，
    以便新写入的记忆在同一会话下一轮即可生效。
    """
    while True:
        system = build_system_prompt()
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
    # 会话启动时加载已有记忆
    memory_mgr.load_all()
    mem_count = len(memory_mgr.memories)
    if mem_count:
        print(f"[已将 {mem_count} 条记忆加载到上下文]")
    else:
        print("[当前无记忆。智能体可通过 save_memory 创建。]")

    history = []
    while True:
        try:
            query = input("\033[36ms09 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        # /memories 命令：查看当前记忆
        if query.strip() == "/memories":
            if memory_mgr.memories:
                for name, mem in memory_mgr.memories.items():
                    print(f"  [{mem['type']}] {name}: {mem['description']}")
            else:
                print("  （无记忆）")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
