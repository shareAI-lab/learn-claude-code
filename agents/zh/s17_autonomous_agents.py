#!/usr/bin/env python3
# Harness（执行框架）: autonomy（自主性）——模型无需等待指派也能发现工作。
"""
s17_autonomous_agents.py - Autonomous Agents（自主智能体）

通过 idle 循环轮询任务板、自动认领未归属任务，并在上下文压缩后重注入身份信息。
本章建立在此前的任务板、团队邮箱与协议机制之上。

    Teammate lifecycle（队友生命周期）：
    +-------+
    | spawn（创建） |
    +---+---+
        |
        v
    +-------+  tool_use（工具调用） +-------+
    | WORK（工作） | <----------- |  LLM  |
    +---+---+              +-------+
        |
        | stop_reason != tool_use（未触发工具调用）
        v
    +--------+
    | IDLE   | 每 5s 轮询一次，最长 60s
    +---+----+
        |
        +---> check inbox（检查收件箱）-> 有消息? -> resume WORK
        |
        +---> scan .tasks/（扫描任务板）-> 有未认领? -> claim -> resume WORK
        |
        +---> timeout（60s）-> shutdown（关停）

    Identity re-injection after compression（压缩后身份重注入）：
    messages = [identity_block（身份块）, ...remaining（其余消息）...]
    "You are 'coder', role: backend, team: my-team"（你是 coder，角色 backend，团队 my-team）

核心观点：处于 idle 的队友可安全认领可执行任务，
而不是每次都等待 lead（负责人）指派。
这里的 teammate（队友）是长生命周期 worker（执行者），不是一次性 subagent（子智能体）。
"""

import json
import os
import subprocess
import threading
import time
import uuid
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
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"
REQUESTS_DIR = TEAM_DIR / "requests"
CLAIM_EVENTS_PATH = TASKS_DIR / "claim_events.jsonl"

POLL_INTERVAL = 5
IDLE_TIMEOUT = 60

SYSTEM = f"你是位于 {WORKDIR} 的 team lead（团队负责人），队友具备自主性，会自行发现工作。"

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval",
    "plan_approval_response",
}

_claim_lock = threading.Lock()


# -- MessageBus：每位队友一个 JSONL 收件箱 --
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Error: Invalid type '{msg_type}'. Valid: {VALID_MSG_TYPES}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text().strip().splitlines():
            if line:
                messages.append(json.loads(line))
        inbox_path.write_text("")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"Broadcast to {count} teammates"


BUS = MessageBus(INBOX_DIR)


class RequestStore:
    """
    协议请求的持久化记录。

    s17 不应从 s16 退回内存态追踪。
    这些请求文件允许自主队友在后续检查或恢复协议状态。
    """

    def __init__(self, base_dir: Path):
        self.dir = base_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, request_id: str) -> Path:
        return self.dir / f"{request_id}.json"

    def create(self, record: dict) -> dict:
        request_id = record["request_id"]
        with self._lock:
            self._path(request_id).write_text(json.dumps(record, indent=2))
        return record

    def get(self, request_id: str) -> dict | None:
        path = self._path(request_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def update(self, request_id: str, **changes) -> dict | None:
        with self._lock:
            record = self.get(request_id)
            if not record:
                return None
            record.update(changes)
            record["updated_at"] = time.time()
            self._path(request_id).write_text(json.dumps(record, indent=2))
        return record


REQUEST_STORE = RequestStore(REQUESTS_DIR)


# -- 任务板扫描 --
def _append_claim_event(payload: dict):
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    with CLAIM_EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def _task_allows_role(task: dict, role: str | None) -> bool:
    required_role = task.get("claim_role") or task.get("required_role") or ""
    if not required_role:
        return True
    return bool(role) and role == required_role


def is_claimable_task(task: dict, role: str | None = None) -> bool:
    return (
        task.get("status") == "pending"
        and not task.get("owner")
        and not task.get("blockedBy")
        and _task_allows_role(task, role)
    )


def scan_unclaimed_tasks(role: str | None = None) -> list:
    TASKS_DIR.mkdir(exist_ok=True)
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if is_claimable_task(task, role):
            unclaimed.append(task)
    return unclaimed


def claim_task(
    task_id: int,
    owner: str,
    role: str | None = None,
    source: str = "manual",
) -> str:
    with _claim_lock:
        path = TASKS_DIR / f"task_{task_id}.json"
        if not path.exists():
            return f"Error: Task {task_id} not found"
        task = json.loads(path.read_text())
        if not is_claimable_task(task, role):
            return f"Error: 任务 {task_id} 对 role={role or '(any)'} 不可认领"
        task["owner"] = owner
        task["status"] = "in_progress"
        task["claimed_at"] = time.time()
        task["claim_source"] = source
        path.write_text(json.dumps(task, indent=2))
    _append_claim_event({
        "event": "task.claimed",
        "task_id": task_id,
        "owner": owner,
        "role": role,
        "source": source,
        "ts": time.time(),
    })
    return f"Claimed task #{task_id} for {owner} via {source}"


# -- 压缩后的身份重注入 --
def make_identity_block(name: str, role: str, team_name: str) -> dict:
    return {
        "role": "user",
        "content": f"<identity>你是 '{name}'，角色 {role}，团队 {team_name}。请继续当前工作。</identity>",
    }


def ensure_identity_context(messages: list, name: str, role: str, team_name: str):
    if messages and "<identity>" in str(messages[0].get("content", "")):
        return
    messages.insert(0, make_identity_block(name, role, team_name))
    messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})


# -- 自主版 TeammateManager --
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save_config(self):
        self.config_path.write_text(json.dumps(self.config, indent=2))

    def _find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def _set_status(self, name: str, status: str):
        member = self._find_member(name)
        if member:
            member["status"] = status
            self._save_config()

    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()
        thread = threading.Thread(
            target=self._loop,
            args=(name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def _loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        sys_prompt = (
            f"你是 '{name}'，角色 {role}，团队 {team_name}，工作目录位于 {WORKDIR}。"
            f"当当前工作完成后请调用 idle；系统会自动认领新任务。"
        )
        messages = [{"role": "user", "content": prompt}]
        tools = self._teammate_tools()

        while True:
            # -- WORK PHASE（工作阶段）：标准智能体循环 --
            for _ in range(50):
                inbox = BUS.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                try:
                    response = client.messages.create(
                        model=MODEL,
                        system=sys_prompt,
                        messages=messages,
                        tools=tools,
                        max_tokens=8000,
                    )
                except Exception:
                    self._set_status(name, "idle")
                    return
                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = []
                idle_requested = False
                for block in response.content:
                    if block.type == "tool_use":
                        if block.name == "idle":
                            idle_requested = True
                            output = "进入 idle（空闲）阶段，将轮询新任务。"
                        else:
                            output = self._exec(name, block.name, block.input)
                        print(f"  [{name}] {block.name}: {str(output)[:120]}")
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(output),
                        })
                messages.append({"role": "user", "content": results})
                if idle_requested:
                    break

            # -- IDLE PHASE（空闲阶段）：轮询收件箱与未认领任务 --
            self._set_status(name, "idle")
            resume = False
            polls = IDLE_TIMEOUT // max(POLL_INTERVAL, 1)
            for _ in range(polls):
                time.sleep(POLL_INTERVAL)
                inbox = BUS.read_inbox(name)
                if inbox:
                    ensure_identity_context(messages, name, role, team_name)
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = scan_unclaimed_tasks(role)
                if unclaimed:
                    task = unclaimed[0]
                    claim_result = claim_task(
                        task["id"], name, role=role, source="auto"
                    )
                    if claim_result.startswith("Error:"):
                        continue
                    task_prompt = (
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                        f"{task.get('description', '')}</auto-claimed>"
                    )
                    ensure_identity_context(messages, name, role, team_name)
                    messages.append({"role": "user", "content": task_prompt})
                    messages.append({"role": "assistant", "content": f"{claim_result}. Working on it."})
                    resume = True
                    break

            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
        # 这些基础工具与 s02 保持一致
        if tool_name == "bash":
            return _run_bash(args["command"])
        if tool_name == "read_file":
            return _run_read(args["path"])
        if tool_name == "write_file":
            return _run_write(args["path"], args["content"])
        if tool_name == "edit_file":
            return _run_edit(args["path"], args["old_text"], args["new_text"])
        if tool_name == "send_message":
            return BUS.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return json.dumps(BUS.read_inbox(sender), indent=2)
        if tool_name == "shutdown_response":
            req_id = args["request_id"]
            updated = REQUEST_STORE.update(
                req_id,
                status="approved" if args["approve"] else "rejected",
                resolved_by=sender,
                resolved_at=time.time(),
                response={"approve": args["approve"], "reason": args.get("reason", "")},
            )
            if not updated:
                return f"Error: 未知的 shutdown request {req_id}"
            BUS.send(
                sender, "lead", args.get("reason", ""),
                "shutdown_response", {"request_id": req_id, "approve": args["approve"]},
            )
            return f"Shutdown {'approved' if args['approve'] else 'rejected'}"
        if tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            req_id = str(uuid.uuid4())[:8]
            REQUEST_STORE.create({
                "request_id": req_id,
                "kind": "plan_approval",
                "from": sender,
                "to": "lead",
                "status": "pending",
                "plan": plan_text,
                "created_at": time.time(),
                "updated_at": time.time(),
            })
            BUS.send(
                sender, "lead", plan_text, "plan_approval",
                {"request_id": req_id, "plan": plan_text},
            )
            return f"计划已提交（request_id={req_id}）。等待审批。"
        if tool_name == "claim_task":
            return claim_task(
                args["task_id"],
                sender,
                role=self._find_member(sender).get("role") if self._find_member(sender) else None,
                source="manual",
            )
        return f"Unknown tool: {tool_name}"

    def _teammate_tools(self) -> list:
        # 这些基础工具与 s02 保持一致
        return [
            {"name": "bash", "description": "执行 shell 命令。",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
            {"name": "read_file", "description": "读取文件内容。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "write_file", "description": "向文件写入内容。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "edit_file", "description": "在文件中替换精确文本。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
            {"name": "send_message", "description": "向队友发送消息。",
             "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)}}, "required": ["to", "content"]}},
            {"name": "read_inbox", "description": "读取并清空自己的收件箱。",
             "input_schema": {"type": "object", "properties": {}}},
            {"name": "shutdown_response", "description": "响应 shutdown 请求。",
             "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "reason": {"type": "string"}}, "required": ["request_id", "approve"]}},
            {"name": "plan_approval", "description": "提交计划给 lead 审批。",
             "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}, "required": ["plan"]}},
            {"name": "idle", "description": "声明当前无可执行工作，进入 idle 轮询阶段。",
             "input_schema": {"type": "object", "properties": {}}},
            {"name": "claim_task", "description": "按 ID 从任务板认领任务。",
             "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
        ]

    def list_all(self) -> str:
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]


TEAM = TeammateManager(TEAM_DIR)


# -- 基础工具实现（与 s02 保持一致） --
def _safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def _run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "Error: 危险命令已拦截"
    try:
        r = subprocess.run(
            command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def _run_read(path: str, limit: int = None) -> str:
    try:
        lines = _safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def _run_write(path: str, content: str) -> str:
    try:
        fp = _safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"


def _run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = _safe_path(path)
        c = fp.read_text()
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# -- Lead（主控）侧协议处理器 --
def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    REQUEST_STORE.create({
        "request_id": req_id,
        "kind": "shutdown",
        "from": "lead",
        "to": teammate,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
    })
    BUS.send(
        "lead", teammate, "请平滑关停。",
        "shutdown_request", {"request_id": req_id},
    )
    return f"Shutdown request {req_id} sent to '{teammate}'"


def handle_plan_review(request_id: str, approve: bool, feedback: str = "") -> str:
    req = REQUEST_STORE.get(request_id)
    if not req:
        return f"Error: 未知的 plan request_id '{request_id}'"
    REQUEST_STORE.update(
        request_id,
        status="approved" if approve else "rejected",
        reviewed_by="lead",
        resolved_at=time.time(),
        feedback=feedback,
    )
    BUS.send(
        "lead", req["from"], feedback, "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"Plan {'approved' if approve else 'rejected'} for '{req['from']}'"


def _check_shutdown_status(request_id: str) -> str:
    return json.dumps(REQUEST_STORE.get(request_id) or {"error": "not found"})


# -- Lead（主控）工具分发（14 个工具） --
TOOL_HANDLERS = {
    "bash":              lambda **kw: _run_bash(kw["command"]),
    "read_file":         lambda **kw: _run_read(kw["path"], kw.get("limit")),
    "write_file":        lambda **kw: _run_write(kw["path"], kw["content"]),
    "edit_file":         lambda **kw: _run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "spawn_teammate":    lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates":    lambda **kw: TEAM.list_all(),
    "send_message":      lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":        lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2),
    "broadcast":         lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request":  lambda **kw: handle_shutdown_request(kw["teammate"]),
    "shutdown_response": lambda **kw: _check_shutdown_status(kw.get("request_id", "")),
    "plan_approval":     lambda **kw: handle_plan_review(kw["request_id"], kw["approve"], kw.get("feedback", "")),
    "idle":              lambda **kw: "Lead does not idle.",
    "claim_task":        lambda **kw: claim_task(kw["task_id"], "lead"),
}

# 这些基础工具与 s02 保持一致
TOOLS = [
    {"name": "bash", "description": "执行 shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "向文件写入内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中替换精确文本。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "spawn_teammate", "description": "创建自主队友。",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["name", "role", "prompt"]}},
    {"name": "list_teammates", "description": "列出全部队友。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "send_message", "description": "向队友发送消息。",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)}}, "required": ["to", "content"]}},
    {"name": "read_inbox", "description": "读取并清空 lead 收件箱。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "broadcast", "description": "向全体队友广播消息。",
     "input_schema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}},
    {"name": "shutdown_request", "description": "请求队友执行关停。",
     "input_schema": {"type": "object", "properties": {"teammate": {"type": "string"}}, "required": ["teammate"]}},
    {"name": "shutdown_response", "description": "查询 shutdown 请求状态。",
     "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}}, "required": ["request_id"]}},
    {"name": "plan_approval", "description": "审批队友计划（通过/拒绝）。",
     "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "feedback": {"type": "string"}}, "required": ["request_id", "approve"]}},
    {"name": "idle", "description": "进入 idle 状态（lead 侧很少使用）。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "claim_task", "description": "按 ID 从任务板认领任务。",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
]


def agent_loop(messages: list):
    while True:
        inbox = BUS.read_inbox("lead")
        if inbox:
            messages.append({
                "role": "user",
                "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>",
            })
            messages.append({
                "role": "assistant",
                "content": "Noted inbox messages.",
            })
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
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
    history = []
    while True:
        try:
            query = input("\033[36ms17 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            print(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(BUS.read_inbox("lead"), indent=2))
            continue
        if query.strip() == "/tasks":
            TASKS_DIR.mkdir(exist_ok=True)
            for f in sorted(TASKS_DIR.glob("task_*.json")):
                t = json.loads(f.read_text())
                marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
                owner = f" @{t['owner']}" if t.get("owner") else ""
                print(f"  {marker} #{t['id']}: {t['subject']}{owner}")
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
