#!/usr/bin/env python3
# Harness（执行框架）: time（时间）——智能体可安排未来工作。
"""
s14_cron_scheduler.py - Cron / Scheduled Tasks（定时任务）

智能体可通过标准 cron 表达式安排未来执行的提示。
当计划命中当前时间，会把通知回注到主对话循环。

    Cron expression（cron 表达式）: 5 fields（5 个字段）
    +-------+-------+-------+-------+-------+
    | min（分） | hour（时） | dom（日） | month（月） | dow（周） |
    | 0-59  | 0-23  | 1-31  | 1-12  | 0-6   |
    +-------+-------+-------+-------+-------+
    示例（Examples）：
      "*/5 * * * *"   -> 每 5 分钟触发
      "0 9 * * 1"     -> 每周一 09:00 触发
      "30 14 * * *"   -> 每天 14:30 触发

    两种持久化模式（Two persistence modes）：
    +--------------------+-------------------------------+
    | session-only       | 仅内存列表，退出即丢失          |
    | durable            | 持久化到 .claude/scheduled_tasks.json |
    +--------------------+-------------------------------+

    两种触发模式（Two trigger modes）：
    +--------------------+-------------------------------+
    | recurring          | 重复触发，直到删除或 7 天自动过期 |
    | one-shot           | 仅触发一次，随后自动删除         |
    +--------------------+-------------------------------+

    Jitter（抖动）说明：recurring 任务可避开整分钟边界，减少同点拥堵。

    架构（Architecture）：
    +-------------------------------+
    |  后台线程（Background thread） |
    |  （每 1 秒检查一次）            |
    |                               |
    |  对每个任务执行：               |
    |    if cron_matches(now):      |
    |      enqueue notification（入队通知） |
    +-------------------------------+
              |
              v
    [notification_queue]
              |
         （在 agent_loop 顶部 drain）
              |
              v
    [在 LLM 调用前注入为 user 消息]

核心观点：调度系统负责记住未来工作，并在到点后把它交回同一主循环。
"""

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty

try:
    from agents.llm_client import create_client
except ModuleNotFoundError:
    from llm_client import create_client
from dotenv import load_dotenv

load_dotenv(override=True)


WORKDIR = Path.cwd()
client = create_client()
MODEL = os.environ["MODEL_ID"]

SCHEDULED_TASKS_FILE = WORKDIR / ".claude" / "scheduled_tasks.json"
CRON_LOCK_FILE = WORKDIR / ".claude" / "cron.lock"
AUTO_EXPIRY_DAYS = 7
JITTER_MINUTES = [0, 30]  # recurring 任务尽量避开这两个整点分钟位
JITTER_OFFSET_MAX = 4     # 偏移范围（分钟）
# 教学版：在需要时使用 1-4 分钟的简单偏移。


class CronLock:
    """
    基于 PID 文件的锁，防止多会话重复触发同一 cron 任务。
    """

    def __init__(self, lock_path: Path = None):
        self._lock_path = lock_path or CRON_LOCK_FILE

    def acquire(self) -> bool:
        """
        尝试获取 cron 锁。成功返回 True。

        若锁文件存在，先检查其中 PID 是否仍存活；
        若进程已死，则视为陈旧锁并接管。
        """
        if self._lock_path.exists():
            try:
                stored_pid = int(self._lock_path.read_text().strip())
                # PID 存活探测：发送 signal 0（不实际杀进程）
                os.kill(stored_pid, 0)
                # 进程活跃：锁由其他会话持有
                return False
            except (ValueError, ProcessLookupError, PermissionError, OSError):
                # 陈旧锁（进程死亡或 PID 无法解析）-> 删除
                pass
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path.write_text(str(os.getpid()))
        return True

    def release(self):
        """若锁归当前进程持有，则删除锁文件。"""
        try:
            if self._lock_path.exists():
                stored_pid = int(self._lock_path.read_text().strip())
                if stored_pid == os.getpid():
                    self._lock_path.unlink()
        except (ValueError, OSError):
            pass


def cron_matches(expr: str, dt: datetime) -> bool:
    """
    判断 5 字段 cron 表达式是否匹配给定时间。

    字段顺序：minute hour day-of-month month day-of-week
    支持语法：*（任意）、*/N（每 N）、N（精确）、N-M（范围）、N,M（列表）

    无外部依赖，采用手工匹配逻辑。
    """
    fields = expr.strip().split()
    if len(fields) != 5:
        return False

    values = [dt.minute, dt.hour, dt.day, dt.month, dt.weekday()]
    # Python weekday: 0=Monday；cron: 0=Sunday。需转换。
    cron_dow = (dt.weekday() + 1) % 7
    values[4] = cron_dow
    ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    for field, value, (lo, hi) in zip(fields, values, ranges):
        if not _field_matches(field, value, lo, hi):
            return False
    return True


def _field_matches(field: str, value: int, lo: int, hi: int) -> bool:
    """匹配单个 cron 字段。"""
    if field == "*":
        return True

    for part in field.split(","):
        # 处理步长：*/N 或 N-M/S
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            step = int(step_str)

        if part == "*":
            # */N：检查 value 是否落在步长网格上
            if (value - lo) % step == 0:
                return True
        elif "-" in part:
            # 范围：N-M
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            if start <= value <= end and (value - start) % step == 0:
                return True
        else:
            # 精确值
            if int(part) == value:
                return True

    return False


class CronScheduler:
    """
    管理定时任务与后台检查线程。

    教学版仅保留核心组件：计划记录、分钟级检查、可选持久化、通知队列。
    """

    def __init__(self):
        self.tasks = []        # 任务字典列表
        self.queue = Queue()   # 通知队列
        self._stop_event = threading.Event()
        self._thread = None
        self._last_check_minute = -1  # 避免同一分钟内重复触发

    def start(self):
        """加载持久任务并启动后台检查线程。"""
        self._load_durable()
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        count = len(self.tasks)
        if count:
            print(f"[Cron] Loaded {count} scheduled tasks")

    def stop(self):
        """停止后台线程。"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def create(self, cron_expr: str, prompt: str,
               recurring: bool = True, durable: bool = False) -> str:
        """创建定时任务并返回 task ID。"""
        task_id = str(uuid.uuid4())[:8]
        now = time.time()

        task = {
            "id": task_id,
            "cron": cron_expr,
            "prompt": prompt,
            "recurring": recurring,
            "durable": durable,
            "createdAt": now,
        }

        # recurring 任务启用 jitter：在 :00 / :30 触发点做轻微偏移
        if recurring:
            task["jitter_offset"] = self._compute_jitter(cron_expr)

        self.tasks.append(task)
        if durable:
            self._save_durable()

        mode = "recurring" if recurring else "one-shot"
        store = "durable" if durable else "session-only"
        return f"Created task {task_id} ({mode}, {store}): cron={cron_expr}"

    def delete(self, task_id: str) -> str:
        """按 ID 删除定时任务。"""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if len(self.tasks) < before:
            self._save_durable()
            return f"Deleted task {task_id}"
        return f"Task {task_id} not found"

    def list_tasks(self) -> str:
        """列出全部定时任务。"""
        if not self.tasks:
            return "No scheduled tasks."
        lines = []
        for t in self.tasks:
            mode = "recurring" if t["recurring"] else "one-shot"
            store = "durable" if t["durable"] else "session"
            age_hours = (time.time() - t["createdAt"]) / 3600
            lines.append(
                f"  {t['id']}  {t['cron']}  [{mode}/{store}] "
                f"({age_hours:.1f}h old): {t['prompt'][:60]}"
            )
        return "\n".join(lines)

    def drain_notifications(self) -> list[str]:
        """从通知队列中取出并清空当前所有待投递通知。"""
        notifications = []
        while True:
            try:
                notifications.append(self.queue.get_nowait())
            except Empty:
                break
        return notifications

    def _compute_jitter(self, cron_expr: str) -> int:
        """若 cron 命中 :00 或 :30，则返回 1-4 分钟的小偏移量。"""
        fields = cron_expr.strip().split()
        if len(fields) < 1:
            return 0
        minute_field = fields[0]
        try:
            minute_val = int(minute_field)
            if minute_val in JITTER_MINUTES:
        # 基于表达式哈希的确定性 jitter
                return (hash(cron_expr) % JITTER_OFFSET_MAX) + 1
        except ValueError:
            pass
        return 0

    def _check_loop(self):
        """后台线程：每秒检查一次是否有任务到期。"""
        while not self._stop_event.is_set():
            now = datetime.now()
            current_minute = now.hour * 60 + now.minute

        # 每分钟仅检查一次，避免重复触发
            if current_minute != self._last_check_minute:
                self._last_check_minute = current_minute
                self._check_tasks(now)

            self._stop_event.wait(timeout=1)

    def _check_tasks(self, now: datetime):
        """用当前时间匹配全部任务，并触发命中的任务。"""
        expired = []
        fired_oneshots = []

        for task in self.tasks:
            # 自动过期：recurring 任务超过 7 天即过期
            age_days = (time.time() - task["createdAt"]) / 86400
            if task["recurring"] and age_days > AUTO_EXPIRY_DAYS:
                expired.append(task["id"])
                continue

            # 匹配检查时应用 jitter 偏移
            check_time = now
            jitter = task.get("jitter_offset", 0)
            if jitter:
                check_time = now - timedelta(minutes=jitter)

            if cron_matches(task["cron"], check_time):
                notification = (
                    f"[Scheduled task {task['id']}]: {task['prompt']}"
                )
                self.queue.put(notification)
                task["last_fired"] = time.time()
                print(f"[Cron] Fired: {task['id']}")

                if not task["recurring"]:
                    fired_oneshots.append(task["id"])

            # 清理过期任务与 one-shot 任务
        if expired or fired_oneshots:
            remove_ids = set(expired) | set(fired_oneshots)
            self.tasks = [t for t in self.tasks if t["id"] not in remove_ids]
            for tid in expired:
                print(f"[Cron] 已自动过期：{tid}（超过 {AUTO_EXPIRY_DAYS} 天）")
            for tid in fired_oneshots:
                print(f"[Cron] one-shot 任务已完成并移除：{tid}")
            self._save_durable()

    def _load_durable(self):
        """从 `.claude/scheduled_tasks.json` 加载持久化任务。"""
        if not SCHEDULED_TASKS_FILE.exists():
            return
        try:
            data = json.loads(SCHEDULED_TASKS_FILE.read_text())
        # 仅加载 durable（持久化）任务
            self.tasks = [t for t in data if t.get("durable")]
        except Exception as e:
            print(f"[Cron] 加载任务失败：{e}")

    def detect_missed_tasks(self) -> list[dict]:
        """
        启动时检查每个持久任务的 `last_fired` 时间。

        若任务在会话关闭期间本应触发（即 last_fired 到 now 区间内
        至少存在一次 cron 命中），则将其标记为漏触发。调用方可再让
        用户决定是执行还是丢弃这些漏触发任务。

        """
        now = datetime.now()
        missed = []
        for task in self.tasks:
            last_fired = task.get("last_fired")
            if last_fired is None:
                continue
            last_dt = datetime.fromtimestamp(last_fired)
        # 从 last_fired 到 now 逐分钟推进检查（最多追溯 24 小时）
            check = last_dt + timedelta(minutes=1)
            cap = min(now, last_dt + timedelta(hours=24))
            while check <= cap:
                if cron_matches(task["cron"], check):
                    missed.append({
                        "id": task["id"],
                        "cron": task["cron"],
                        "prompt": task["prompt"],
                        "missed_at": check.isoformat(),
                    })
                    break  # 命中一次漏触发即可标记
                check += timedelta(minutes=1)
        return missed

    def _save_durable(self):
        """将持久任务写回磁盘。"""
        durable = [t for t in self.tasks if t.get("durable")]
        SCHEDULED_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULED_TASKS_FILE.write_text(
            json.dumps(durable, indent=2) + "\n"
        )


# 全局调度器
scheduler = CronScheduler()


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
    "bash":        lambda **kw: run_bash(kw["command"]),
    "read_file":   lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":  lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":   lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "cron_create": lambda **kw: scheduler.create(
        kw["cron"], kw["prompt"], kw.get("recurring", True), kw.get("durable", False)),
    "cron_delete": lambda **kw: scheduler.delete(kw["id"]),
    "cron_list":   lambda **kw: scheduler.list_tasks(),
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
    {"name": "cron_create", "description": "使用 cron 表达式创建 recurring 或 one-shot 定时任务。",
     "input_schema": {"type": "object", "properties": {
            "cron": {"type": "string", "description": "5 字段 cron 表达式：'min hour dom month dow'"},
            "prompt": {"type": "string", "description": "任务触发时注入会话的提示内容"},
            "recurring": {"type": "boolean", "description": "true=重复触发，false=触发一次后删除；默认 true"},
            "durable": {"type": "boolean", "description": "true=落盘持久化，false=仅当前会话；默认 false"},
     }, "required": ["cron", "prompt"]}},
    {"name": "cron_delete", "description": "按 ID 删除定时任务。",
     "input_schema": {"type": "object", "properties": {
            "id": {"type": "string", "description": "要删除的任务 ID"},
     }, "required": ["id"]}},
    {"name": "cron_list", "description": "列出全部定时任务。",
     "input_schema": {"type": "object", "properties": {}}},
]

SYSTEM = (
    f"你是位于 {WORKDIR} 的 coding agent（编码智能体），请使用工具解决任务。\n\n"
    "你可以通过 cron_create 调度未来工作。任务触发后会自动把提示注入当前会话。"
)


def agent_loop(messages: list):
    """
    带 cron 调度感知的智能体主循环。

    每次调用 LLM 前，先清空通知队列，并将已触发任务的提示词
    注入为 user 消息。这样智能体就能“唤醒”并处理计划任务。
    """
    while True:
        # 清空并处理定时任务通知
        notifications = scheduler.drain_notifications()
        for note in notifications:
            print(f"[Cron notification] {note[:100]}")
            messages.append({"role": "user", "content": note})

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
    scheduler.start()
    print("[Cron 调度器已启动，后台每秒检查一次。]")
    print("[命令：/cron 查看任务，/test 触发一条测试通知]")

    history = []
    while True:
        try:
            query = input("\033[36ms14 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            scheduler.stop()
            break
        if query.strip().lower() in ("q", "exit", ""):
            scheduler.stop()
            break

        if query.strip() == "/cron":
            print(scheduler.list_tasks())
            continue

        if query.strip() == "/test":
        # 演示用途：手动插入一条测试通知
            scheduler.queue.put("[计划任务 test-0000]：这是一条测试通知。")
            print("[测试通知已入队，将在你下一条消息前注入。]")
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
