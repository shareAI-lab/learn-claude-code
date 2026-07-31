import os,json,ast,subprocess,difflib,yaml,time,re,copy,random,threading,uuid,hashlib
from pathlib import Path
from dataclasses import dataclass,asdict,field
from types import SimpleNamespace
from datetime import datetime
from xml.sax.saxutils import escape

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv
from homework.agent_app.core.recovery import (
    PartialStreamError,
    RecoveryState,
    append_unrecoverable_error,
    is_prompt_too_long_error,
    with_retry,
)

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN",None)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKDIR = REPO_ROOT
PRIMARY_MODEL = os.environ["MODEL_ID"]
MODEL = PRIMARY_MODEL
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL_ID")
SKILLS_DIR = WORKDIR / "skills"
MEMORY_DIR = WORKDIR / ".memory"; MEMORY_DIR.mkdir(exist_ok=True)
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
TRANSCRIPTS_DIR = WORKDIR / ".transcripts"

TOOL_RESULT_DIR = WORKDIR / ".task_outputs" / "tool-results"
TOOL_RESULTS_DIR = TOOL_RESULT_DIR
LARGE_OUTPUT_DIR = TOOL_RESULT_DIR

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
CURRENT_TODOS:list[dict] = []

def resolve_tool_cwd(
        cwd: str | Path | None= None
):
    workspace_root = WORKDIR.resolve()
    base = Path(cwd).resolve() if cwd else workspace_root

    if not base.is_relative_to(workspace_root):
        raise ValueError(
            f"Tool cwd escapes workspace: {cwd}"
        )

    if not base.is_dir():
        raise ValueError(f"Tool cwd does not exist: {base}")

    return base

def safe_path(path:str, cwd:str | Path | None = None) -> Path:
    base = resolve_tool_cwd(cwd)
    resolved = (base / path).resolve()

    if not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes working directory: {path}")

    return resolved

#==================== CRON SCHEDULER ====================
DURABLE_PATH = WORKDIR / ".scheduled_tasks.json"

@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool

scheduled_jobs: dict[str, CronJob] = {}
cron_queue: list[CronJob] = []
cron_lock = threading.Lock()
agent_lock = threading.Lock()
_last_fired: dict[str, str] = {}

def _cron_field_matches(field: str, value: int) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(
            _cron_field_matches(f.strip(),value)
            for f in field.split(",")
        )
    if "-" in field:
        lo, hi = field.split("-",1)
        return int(lo) <= value <= int(hi)
    return value == int(field)

def cron_matches(cron_expr: str, dt: datetime) -> bool:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7

    m = _cron_field_matches(minute, dt.minute)
    h = _cron_field_matches(hour, dt.hour)
    dom_ok = _cron_field_matches(dom, dt.day)
    month_ok = _cron_field_matches(month, dt.month)
    dow_ok = _cron_field_matches(dow, dow_val)

    if not (m and h and month_ok):
        return False
    dom_unconstrained = dom == "*"
    dow_unconstrained = dow == "*"
    if dom_unconstrained and dow_unconstrained:
        return True
    if dom_unconstrained:
        return dow_ok
    if dow_unconstrained:
        return dom_ok

    return dom_ok or dow_ok

def _validate_cron_field(field: str, lo: int, hi: int) -> str | None:
    if field == "*":
        return None
    if field.startswith("*/"):
        step_str = field[2:]
        if not step_str.isdigit():
            return f"Invalid step: {field}"
        step = int(step_str)
        if step <= 0:
            return f"Step must be > 0: {field}"
        return None
    if "," in field:
        for part in field.split(","):
            err = _validate_cron_field(part.strip(), lo, hi)
            if err: return err
        return None
    if "-" in field:
        parts = field.split("-", 1)
        if not parts[0].isdigit() or not parts[1].isdigit():
            return f"Invalid range: {field}"
        a, b = int(parts[0]), int(parts[1])
        if a < lo or a > hi or b < lo or b > hi:
            return f"Range {field} out of bounds [{lo}-{hi}]"
        if a > b:
            return f"Range start > end: {field}"
        return None
    if not field.isdigit():
        return f"Invalid field: {field}"
    val = int(field)
    if val < lo or val > hi:
        return f"Value {val} out of bounds [{lo}-{hi}]"
    return None

def validate_cron(cron_expr: str) -> str | None:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return f"Expected 5 fields, got {len(fields)}"
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    names = ["minute", "hour", "day-of-month", "month", "day-of-week"]
    for i, (field, (lo, hi), name) in enumerate(zip(fields, bounds, names)):
        err = _validate_cron_field(field, lo, hi)
        if err:
            return f"{name}: {err}"
    return None

def save_durable_jobs():
    with cron_lock:
        durable = [asdict(j) for j in scheduled_jobs.values() if j.durable]
        temp_path = DURABLE_PATH.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(durable, indent = 2, ensure_ascii = False),
            encoding = 'utf-8'
        )
    temp_path.replace(DURABLE_PATH)

def load_durable_jobs():
    if not DURABLE_PATH.exists():
        return
    try:
        jobs = json.loads(DURABLE_PATH.read_text())
        for j in jobs:
            job = CronJob(**j)
            err = validate_cron(job.cron)
            if err:
                print(f"  \033[31m[cron] skipping invalid job {job.id}: {err}\033[0m")
                continue
            scheduled_jobs[job.id] = job
        valid = [j for j in jobs if j["id"] in scheduled_jobs]
        if valid:
            print(f"  \033[35m[cron] loaded {len(valid)} durable job(s)\033[0m")
    except Exception:
        pass

def schedule_job(cron: str, prompt: str, recurring: bool = True,
                 durable: bool = True) -> CronJob | str:
    err = validate_cron(cron)
    if err:
        return err
    job = CronJob(
        id = f"cron_{random.randint(0,999999):06d}",
        cron = cron,
        prompt = prompt,
        recurring= recurring,
        durable = durable,
    )
    with cron_lock:
        scheduled_jobs[job.id] = job
    if durable:
        save_durable_jobs()
    print(f"  \033[35m[cron register] {job.id} '{cron}' → {prompt[:40]}\033[0m")
    return job

def cancel_job(job_id: str) -> str:
    with cron_lock:
        job = scheduled_jobs.pop(job_id, None)
    if not job:
        return f"Job {job_id} not found"
    if job.durable:
        save_durable_jobs()
    print(f"  \033[31m[cron cancel] {job_id}\033[0m")
    return f"Cancelled {job_id}"

def cron_scheduler_loop(stop_event = None):
    stop_event = stop_event or threading.Event()

    while not stop_event.wait(1):
        now = datetime.now()
        minute_marker = now.strftime("%Y-%m-%d %H:%M")
        durable_changed = False

        with cron_lock:
            for job in list(scheduled_jobs.values()):
                try:
                    if cron_matches(job.cron, now):
                        if _last_fired.get(job.id) != minute_marker:
                            cron_queue.append(job)
                            _last_fired[job.id] = minute_marker
                            print(f"  \033[35m[cron fire] {job.id} → "
                                  f"{job.prompt[:40]}\033[0m")
                        if not job.recurring:
                            scheduled_jobs.pop(job.id, None)
                            _last_fired.pop(job.id, None)
                            durable_changed = durable_changed or job.durable

                except Exception as e:
                    print(f"  \033[31m[cron error] {job.id}: {e}\033[0m")

        if durable_changed:
            save_durable_jobs()

def consume_cron_queue() -> list[CronJob]:
    with cron_lock:
        fired = list(cron_queue)
        cron_queue.clear()
    return fired

def has_cron_queue() -> bool:
    with cron_lock:
        return bool(cron_queue)

#==================== AGENT TEAMS ====================
MAILBOX_DIR = WORKDIR / ".mailboxes"
AGENT_NAME_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_-]{0,31}$"
)

ALLOWED_MESSAGE_TYPES = {
    "message",
    "result",
    "permission_request",
    "permission_response",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_request",
    "plan_approval_response",
}

mailbox_lock = threading.RLock()
team_lock = threading.Lock()
active_teammates: dict[str,dict] = {}

class MessageBus:
    def send(self,from_agent: str, to_agent:str, content:object,
             msg_type:str = "message", metadata: dict = None):
        validate_agent_name(from_agent)
        validate_agent_name(to_agent)

        if msg_type not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(f"Invalid message type: {msg_type}")

        msg = {"from": from_agent, "to": to_agent, 
               "content": content,  "type": msg_type, 
               "ts": time.time(), "metadata": metadata or {}}
        path = mailbox_path(to_agent)

        with mailbox_lock:
            MAILBOX_DIR.mkdir(exist_ok=True)
            with path.open("a", encoding='utf-8') as f:
                f.write(
                    json.dumps(msg, ensure_ascii = False) + "\n"
                )
                f.flush()
        
    def read_inbox(self, agent: str) -> list[dict]:
        path = mailbox_path(agent)

        with mailbox_lock:
            if not path.exists():
                return []
            
            lines = path.read_text(encoding='utf-8').splitlines()

            path.write_text("",encoding='utf-8')

        msgs = []
        for line in lines:
            if not line.strip():
                continue

            try:
                msgs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[mailbox warning] ignored corrupt line: {e}")
        return msgs

BUS = MessageBus()

@dataclass
class ProtocolState:
    request_id: str
    type: str
    sender: str
    target: str
    status: str
    payload: str
    created_at: float = field(default_factory=time.time)

pending_requests: dict[str, ProtocolState] = {}
protocol_lock = threading.RLock()

EXCEPTED_RESPONSE_TYPES = {
    "shutdown": "shutdown_response",
    "plan_approval": "plan_approval_response",
}

def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"

def match_response(response_type: str, request_id: str, approve: bool) -> bool:
    with protocol_lock:
        state = pending_requests.get(request_id)
        if not state:
            print(f"  \033[31m[protocol] unknown request_id: {request_id}\033[0m")
            return False
        
        excepted_type = EXCEPTED_RESPONSE_TYPES.get(state.type)
        if response_type != excepted_type:
            print(f"  \033[31m[protocol] type mismatch: "
                  f"(expected {excepted_type}), got {response_type}\033[0m")
            return False
        
        if state.status != "pending":
            print(f"  \033[33m[protocol] {request_id} already {state.status}, "
                f"ignoring duplicate\033[0m")
            return False
        state.status = "approved" if approve else "rejected"

    icon = "✓" if approve else "✗"
    color = "32" if approve else "31"
    print(f"  \033[{color}m[protocol] {state.type} {icon} "
          f"({request_id}: {state.status})\033[0m")
    return True

#================== AUTONOMOUS AGENT ==========================
IDLE_POLL_INTERVAL = 5
IDLE_TIMEOUT = 60

def scan_unclaimed_tasks() -> list[dict]:
    return [
        asdict(task)
        for task in list_tasks()
        if (
            task.status == "pending"
            and not task.owner
            and can_start(task.id)
        )
    ]

def idle_poll(agent_name: str, messages: list,
              name: str, role: str, worktree_context: dict | None = None) -> str:
    for _ in range(IDLE_TIMEOUT // IDLE_POLL_INTERVAL):
        time.sleep(IDLE_POLL_INTERVAL)

        inbox = BUS.read_inbox(agent_name)
        if inbox:
            for msg in inbox:
                if msg.get("type") == "shutdown_request":
                    req_id = msg.get("metadata", {}).get("request_id", "")
                    BUS.send(name, "lead", "Shutting down gracefully.",
                             "shutdown_response",
                             {"request_id": req_id, "approve": True})
                    print(f"  \033[35m[protocol] {name} approved shutdown "
                                              f"in idle ({req_id})\033[0m")
                    return "shutdown"

            messages.append({
                "role": "user",
                "content": "<inbox>" + json.dumps(inbox) + "</inbox>"
            })
            print(f"  \033[36m[idle] {name} found inbox messages\033[0m")
            return "work"

        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            task = unclaimed[0]
            result = claim_task(task["id"], agent_name)
            if "Claimed" in result:
                worktree_name = task.get("worktree")

                if worktree_context is not None:
                    worktree_context["path"] = (str(WORKTREES_DIR / worktree_name) if worktree_name else None)

                messages.append({
                    "role": "user",
                    "content": f"<auto-claimed>Task {task['id']}: "
                               f"{task['subject']}</auto-claimed>"
                })
                print(f"  \033[32m[idle] {name} auto-claimed: "
                      f"{task['subject']}\033[0m")
                return "work"
            print(f"  \033[33m[idle] {name} claim failed: "
                  f"{result}\033[0m")

    print(f"  \033[31m[idle] {name} timeout ({IDLE_TIMEOUT}s)\033[0m")
    return "timeout"

def validate_agent_name(name: str, *, allow_lead: bool = True) -> str:
    if not isinstance(name, str):
        raise TypeError("Agent name must be a string")
    
    if not AGENT_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid agent name: {name!r}")
    
    if not allow_lead and name == "lead":
        raise ValueError("'lead' is a reversed agent name")
    
    return name

def mailbox_path(agent: str) -> Path:
    validate_agent_name(agent)

    path = (MAILBOX_DIR / f"{agent}.jsonl").resolve()
    root = MAILBOX_DIR.resolve()

    if not path.is_relative_to(root):
        raise ValueError("Mailbox path escapes mailbox directory")
    
    return path

TEAM_GUARDED_TOOLS = {"bash", "write_file"}
PERMISSION_POLL_INTERVAL = 0.5
PERMISSION_TIMEOUT = 300

def wait_for_permission_response(agent: str, request_id: str, deferred_inbox: list[dict]) -> dict:
    deadline = time.time() + PERMISSION_TIMEOUT

    while time.time() < deadline:
        matched = None

        for msg in BUS.read_inbox(agent):
            content = msg.get("content", {})

            if (
                msg.get("type") == "permission_response"
                and msg.get("from") == "lead"
                and isinstance(content, dict)
                and content.get("request_id") == request_id
            ):
                matched = content
            else:
                deferred_inbox.append(msg)
        
        if matched:
            return matched
        
        time.sleep(PERMISSION_POLL_INTERVAL)
    return {
        "request_id": request_id,
        "approved": False,
        "reason": "Permission request timed out"
    }

def run_teammate_guarded_tool(
        agent: str,
        block,
        deferred_inbox: list[dict],
        handler,
        cwd: Path | None
) -> tuple[str, bool]:
    request_id = uuid.uuid4().hex

    BUS.send(
        agent,
        "lead",
        {
            "request_id": request_id,
            "tool_use_id": block.id,
            "tool_name": block.name,
            "tool_input": block.input,
            "cwd": str(cwd) if cwd else None
        },
        msg_type="permission_request"
    )

    response = wait_for_permission_response(agent, request_id, deferred_inbox)

    if not response.get("approved"):
        reason = response.get("reason", "Permission denied")
        return f"Permission denied: {reason}", True

    output = handler(**block.input)
    trigger_hook("PostToolUse", block, output)
    return str(output), False
    

def spawn_teammate_thread(name: str, role:str, prompt: str) -> str:
    try:
        validate_agent_name(name, allow_lead=False)
    except (TypeError, ValueError) as e:
        return f"Invalid teammate: {e}"
    
    if not role.strip():
        return "Invalid teammate: role is required"
    if not prompt.strip():
        return "Invalid teammate: prompt is required"

    with team_lock:
        if name in active_teammates:
            return f"Teammate {name} already exists"
        
        active_teammates[name] = {
            "name": name,
            "role": role,
            "status": "running",
        }
    
    team_tools = [{"name": "bash", "description": "Run a shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "send_message", "description": "Send a message to another agent.", 
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}},
    {"name": "submit_plan",
                  "description": "Submit a plan for Lead approval.",
                  "input_schema": {"type": "object",
                                   "properties": {"plan": {"type": "string"}},
                                   "required": ["plan"]}},
    {"name": "list_tasks",
                 "description": "List all tasks on the board.",
                 "input_schema": {"type": "object", "properties": {},
                                  "required": []}},
    {"name": "claim_task",
        "description": "Claim a pending task.",
        "input_schema": {"type": "object",
                        "properties": {"task_id": {"type": "string"}},
                        "required": ["task_id"]}},
    {"name": "complete_task",
        "description": "Mark an in-progress task as completed.",
        "input_schema": {"type": "object",
                        "properties": {"task_id": {"type": "string"}},
                        "required": ["task_id"]}},
    ]

    team_tool_name = ", ".join(t["name"] for t in team_tools)
        
    system = (f"You are '{name}', role: {role}.\n"
                f"Workspace: {WORKDIR}\n"
                f"Available tools: {team_tool_name}\n"
                "You must send your final result to lead using send_message.\n"
                "Do not create subagents or additional teammates.\n"
                "bash and write_file require permission from Lead. "
                "When permission is approved, you will execute the tool yourself. "
                "Do not claim that a protected operation succeeded until its "
                "tool_result confirms success.")

    protocol_ctx = {"waiting_plan": None}

    def handle_inbox_message(name: str, msg: dict, messages: list) -> bool:
        msg_type = msg.get("type", "message")
        meta = msg.get("metadata", {})
        req_id = meta.get("request_id", "")

        if msg_type == "shutdown_request":
            BUS.send(name, "lead", "Shutting down gracefully.",
                     "shutdown_response",
                     {"request_id":req_id, "approve": True})
            print(f"  \033[35m[protocol] {name} approved shutdown "
                              f"({req_id})\033[0m")
            return True

        if msg_type == "plan_approval_response":
            if req_id != protocol_ctx["waiting_plan"]:
                return False

            protocol_ctx["waiting_plan"] = None
            approve = meta.get("approve", False)
            if approve:
                messages.append({"role": "user",
                                 "content": f"[Plan approved] Proceed with the task."})
            else:
                messages.append({"role": "user",
                                 "content": f"[Plan rejected] Feedback: {msg['content']}"})

        return False
            
    def run():
        messages = [{"role": "user", "content": prompt}]
        summary = "Stopped after 10 teammate rounds."
        deferred_inbox: list[dict] = []
        state = RecoveryState(
            current_model=PRIMARY_MODEL,
            fallback_model=FALLBACK_MODEL,
        )
        wt_ctx = {"path": None}
        
        def _wt_cwd() -> Path | None:
            p = wt_ctx["path"]
            return Path(p) if p else None

        def _run_bash(command: str) -> str:
            return run_bash(command, cwd=_wt_cwd())

        def _run_read(path: str, offset: int = 0, limit: int | None = None) -> str:
            return run_read(path, offset=offset, limit=limit, cwd=_wt_cwd())

        def _run_write(path: str, content: str) -> str:
            return run_write(path, content, cwd=_wt_cwd())

        def _run_list_tasks():
            tasks = list_tasks()
            if not tasks:
                return "No tasks."
            return "\n".join(
                f"  {t.id}: {t.subject} [{t.status}]"
                + (f" (wt:{t.worktree})" if t.worktree else "")
                for t in tasks)

        def _run_claim_task(task_id: str):
            result = claim_task(task_id, owner=name)
            if "Claimed" in result:
                # Set worktree cwd if task has one
                task = load_task(task_id)
                if task.worktree:
                    wt_ctx["path"] = str(WORKTREES_DIR / task.worktree)
                else:
                    wt_ctx["path"] = None
            return result

        def _run_complete_task(task_id: str):
            result = complete_task(task_id)

            if result.startswith("Completed"):
                wt_ctx["path"] = None

            return result

        sub_handlers = {
            "bash": _run_bash,
            "read_file": _run_read,
            "write_file": _run_write,
            "send_message": lambda to, content: (BUS.send(name, to, content), "Sent")[1],
            "submit_plan": lambda plan: _teammate_submit_plan(name, plan),
            "list_tasks": _run_list_tasks,
            "claim_task": _run_claim_task,
            "complete_task": _run_complete_task,
        }

        lifecycle_done = False
        try:
            while not lifecycle_done:
                if len(messages) <= 3:
                    messages.insert(0,{
                        "role": "user",
                        "content": f"<identity>You are '{name}', role: {role}. "
                                f"Continue your work.</identity>"
                    })

                should_shutdown = False
                work_completed = False

                for _ in range(10):
                    inbox = deferred_inbox + BUS.read_inbox(name)
                    deferred_inbox.clear()
                    for msg in inbox:
                        if handle_inbox_message(name, msg, messages):
                            should_shutdown = True
                            break
                    if should_shutdown:
                        lifecycle_done = True
                        break

                    if work_completed:
                        idle_result = idle_poll(name, messages, name, role, wt_ctx)
                        if idle_result == "work":
                            continue
                        if idle_result in ("timeout","shutdown"):
                            lifecycle_done = True
                            break

                    if inbox and not should_shutdown:
                        non_protocol = [m for m in inbox
                                        if m.get("type") == "message"]
                        if non_protocol:
                            messages.append({
                                "role": "user",
                                "content": f"<inbox>{json.dumps(non_protocol)}</inbox>"
                            })

                    if protocol_ctx["waiting_plan"]:
                        time.sleep(IDLE_POLL_INTERVAL)
                        continue
                        
                    try:
                        response = with_retry(
                            lambda: client.messages.create(
                            model = state.current_model, system = system,messages = messages[-20:],
                            tools = team_tools, max_tokens = DEFAULT_MAX_TOKENS
                            ),
                        state,
                        max_transient_retries=MAX_TRANSIENT_RETRIES,
                        max_consecutive_529=MAX_CONSECUTIVE_529,
                        base_delay_ms=BASE_DELAY_MS,
                        )
                    except Exception as e:
                        summary = (
                            f"Teammate error: "
                            f"{type(e).__name__}: {e}"
                        )
                        lifecycle_done = True
                        break

                    messages.append({"role": "assistant", "content": response.content})
                    if not has_tool_use(response.content):
                        summary = extract_text(response.content) or summary
                        work_completed = True
                        break
                        
                    results = []
                    for block in response.content:
                        if block.type != "tool_use":
                            continue

                        handler = sub_handlers.get(block.name)

                        if not handler:
                            output = f"Unknown tool: {block.name}"
                            is_error = True
                        elif block.name == "submit_plan":
                            output = handler(**block.input)
                            match = re.search(r"\((req_[^)]+)\)", str(output))

                            if match:
                                protocol_ctx["waiting_plan"] = match.group(1)
                                is_error = False
                            else:
                                output = f"Invalid plan submission response: {output}"
                                is_error = True
                        elif block.name in TEAM_GUARDED_TOOLS:
                            output, is_error = run_teammate_guarded_tool(
                                name, block, deferred_inbox, handler, _wt_cwd()
                            )
                        else:
                            output = handler(**block.input)
                            is_error = False

                        result = {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(output),
                        }

                        if is_error:
                            result["is_error"] = True

                        results.append(result)

                        if protocol_ctx["waiting_plan"]:
                            break

                    messages.append({"role": "user", "content": results})
                    if protocol_ctx["waiting_plan"]:
                        break

                    response_text = extract_text(response.content)
                    if response_text:
                        summary = response_text

                if lifecycle_done:
                        break
                if protocol_ctx["waiting_plan"]:
                    continue
                if not work_completed:
                        summary = "Stopped after 10 teammate tool rounds."
                        break

                with team_lock:
                    teammate = active_teammates.get(name)
                    if teammate:
                        teammate["status"] = "idle"

                idle_result = idle_poll(
                    name,
                    messages,
                    name,
                    role,
                    wt_ctx,
                )

                if idle_result == "work":
                    with team_lock:
                        teammate = active_teammates.get(name)
                        if teammate:
                            teammate["status"] = "running"
                    continue

                if idle_result in ("timeout", "shutdown"):
                    lifecycle_done = True
        except Exception as e:
            summary = f"Teammate error: {type(e).__name__}: {e}"

        finally:
            try:
                BUS.send(name, "lead", summary, "result")
            except Exception as e:
                print(f"  \033[31m[teammate result error]"
                    f"{name}: {e}\033[0m")
            
            with team_lock:
                active_teammates.pop(name, None)
            print(f"  \033[32m[teammate] {name} finished\033[0m")

    threading.Thread(target=run, daemon=True).start()
    print(f"  \033[36m[teammate] {name} spawned as {role}\033[0m")
    return f"Teammate '{name}' spawned as {role}"

def _teammate_submit_plan(from_name: str, plan: str) -> str:
    req_id = new_request_id()
    with protocol_lock:
        pending_requests[req_id] = ProtocolState(
            request_id=req_id, type = "plan_approval",
            sender = from_name, target = "lead",
            status = "pending", payload = plan
        )
    BUS.send(
        from_name, "lead", plan,
        "plan_approval_request",
        {"request_id": req_id}
    )
    return f"Plan submitted ({req_id}). Waiting for approval..."
    
def process_permission_request(msg: dict) -> None:
    requester = msg.get("from")
    request = msg.get("content", {})

    cwd_valid = True
    tool_cwd = None

    if cwd_valid:
        try:
            tool_cwd = resolve_tool_cwd(request.get("cwd"))
        except (TypeError, ValueError) as e:
            cwd_valid = False

    if isinstance(request, dict):
        request_id = request.get("request_id")
        tool_name = request.get("tool_name")
        tool_input = request.get("tool_input")
    else:
        request_id = None
        tool_name = None
        tool_input = None

    valid = (
        isinstance(request_id, str)
        and tool_name in TEAM_GUARDED_TOOLS
        and isinstance(tool_input, dict)
        and cwd_valid
    )

    if not valid:
        BUS.send(
            "lead",
            requester,
            {
                "request_id": request_id,
                "approved": False,
                "reason": "Invalid permission request",
            },
            msg_type="permission_response",
        )
        return

    block = SimpleNamespace(
        id=request.get("tool_use_id"),
        name=tool_name,
        input=tool_input,
        agent=requester,
        cwd = tool_cwd,
    )

    denied_reason = trigger_hook("PreToolUse", block)
    approved = denied_reason is None

    BUS.send(
        "lead",
        requester,
        {
            "request_id": request_id,
            "approved": approved,
            "reason": "" if approved else str(denied_reason),
        },
        msg_type="permission_response",
    )

def collect_lead_inbox() -> str:
    ordinary_msgs = []

    for msg in BUS.read_inbox("lead"):
        msg_type = msg.get("type", "")

        if msg_type == "permission_request":
            process_permission_request(msg)
            continue

        if msg_type in {"shutdown_response", "plan_approval_response"}:
            metadata = msg.get("metadata", {})
            request_id = metadata.get("request_id", "")

            if request_id:
                match_response(msg_type, request_id, bool(metadata.get("approve", False)))
            else:
                print(f"  [protocol] {msg_type} missing request_id")

        ordinary_msgs.append(msg)

    return ordinary_msgs

def format_team_inbox(messages: list[dict]) -> str:
    lines = ["[Team inbox]"]

    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)

        lines.append(
            f"From {msg.get('from')}"
            f"({msg.get('type')})"
            f"{content}"
        )
    return "\n".join(lines)

def has_active_teammates() -> bool:
    with team_lock:
        return bool(active_teammates)
    
def wait_for_team_activity(messages: list[dict]) -> bool:
    deadline = time.time() + PERMISSION_TIMEOUT

    while True:
        team_messages = collect_lead_inbox()

        if team_messages:
            append_user_text_blocks(
                messages,
                [format_team_inbox(team_messages)],
            )
            return True

        if not has_active_teammates():
            return False

        if time.time() >= deadline:
            print(
                "  \033[33m[team] wait timed out; "
                "teammates remain active\033[0m"
            )
            return False

        time.sleep(PERMISSION_POLL_INTERVAL)
    
def run_spawn_teammate(name: str, role:str, prompt: str) -> str:
    return spawn_teammate_thread(name, role, prompt)

def run_send_message(to: str, content: str) -> str:
    BUS.send("lead", to, content)
    return f"Sent to {to}"

def run_check_inbox() -> str:
    msgs = collect_lead_inbox()
    if not msgs:
        return "(inbox empty)"
    return format_team_inbox(msgs)

def run_request_shutdown(teammate: str) -> str:
    req_id = new_request_id()
    with protocol_lock:
        pending_requests[req_id] = ProtocolState(
            request_id=req_id, type = "shutdown",
            sender = "lead", target = teammate,
            status = "pending", payload = ""
        )
    BUS.send(
        "lead", teammate, "Please shut down gracefully.",
        "shutdown_request",
        {"request_id": req_id}
    )
    print(f"  \033[35m[protocol] shutdown_request → {teammate} "
              f"({req_id})\033[0m")
    return f"Shutdown request sent to {teammate} (req: {req_id})"

def run_request_plan(teammate: str, task: str) -> str:
    BUS.send("lead", teammate, f"Please submit a plan for: {task}", "message")
    return f"Asked {teammate} to submit a plan"

def run_review_plan(request_id: str, approve: bool, feedback: str = "") -> str:
    with protocol_lock:
        state = pending_requests.get(request_id)
        if not state:
            return f"Request {request_id} not found"
        state.status = "approved" if approve else "rejected"
    BUS.send("lead", state.sender, feedback or ("Approved" if approve else "Rejected"),
                "plan_approval_response",
                {"request_id": request_id, "approve": approve})
    icon = "✓" if approve else "✗"
    print(f"  \033[32m[protocol] plan {icon} ({request_id})\033[0m")
    return f"Plan {'approved' if approve else 'rejected'} ({request_id})"

#==================== BACKGROUND TASKS ===============
_bg_counter = 0
background_tasks: dict[str,dict] = {}
background_results: dict[str,str] = {}
background_lock = threading.Lock()

def is_slow_operation(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash":
        return False
    cmd = tool_input.get("command", "").lower()
    slow_keywords = ["install", "build", "test", "deploy", "compile",
                     "docker build", "pip install", "npm install",
                     "cargo build", "pytest", "make"]
    return any(kw in cmd for kw in slow_keywords)

def should_run_background(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash":
        return False
    if tool_input.get("run_in_background"):
        return True
    return is_slow_operation(tool_name, tool_input)

def execute_tool(block, handlers = None) -> str:
    selected_handlers = (handlers if handlers is not None else BUILTIN_HANDLERS)
    handler = selected_handlers.get(block.name)
    if handler:
        return handler(**block.input)
    return f"Unknown tool: {block.name}"

def start_background_task(block,handlers: dict) -> str:
    global _bg_counter
    handler_snapshot = dict(handlers)

    with background_lock:
        _bg_counter += 1
        bg_id = f"bg_{_bg_counter:04d}"
        background_tasks[bg_id] = {
            "id": bg_id,
            "tool_use_id": block.id,
            "tool_name": block.name,
            "command": block.input.get("command", ""),
            "status": "running",
            "error": None,
        }

    def worker():
        status = "completed"
        error = None
        output = ""

        try:
            output = str(execute_tool(block, handler_snapshot))

            trigger_hook("PostToolUse",block,output)

            output = persist_large_output(block.id, output)
        except Exception as e:
            status = "failed"
            error = f"{type(e).__name__}: {e}"
            print(f"  \033[31m[background error] {bg_id}: {error}\033[0m")
        finally:
            with background_lock:
                task = background_tasks.get(bg_id)
                if task:
                    task["status"] = status
                    task["error"] = error
                    background_results[bg_id] = output

    threading.Thread(target=worker, daemon=True).start()
    return bg_id

def collect_background_results() -> list[str]:
    with background_lock:
        ready_ids = [bid for bid, task in background_tasks.items()
                     if task["status"] == "completed" or task["status"] == "failed"]
        
    notifications = []
    for bg_id in ready_ids:
        with background_lock:
            task = background_tasks.pop(bg_id)
            output = background_results.pop(bg_id, "")
        summary_source = task.get("error") or output
        summary = (
            summary_source[:200]
            if len(summary_source) > 200
            else summary_source
        )
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{escape(str(bg_id))}</task_id>\n"
            f"  <status>{escape(str(task['status']))}</status>\n"
            f"  <command>{escape(str(task['command']))}</command>\n"
            f"  <summary>{escape(str(summary))}</summary>\n"
            f"</task_notification>"
        )
        print(f"  \033[32m[background done] {bg_id}: "
            f"{task['command'][:40]} ({len(output)} chars)\033[0m")
    return notifications


#==================== TASK SYSTEM ====================
TASK_DIR = WORKDIR / ".tasks"
TASK_DIR.mkdir(exist_ok=True)

TASK_LOCK = threading.Lock()
TASK_ID_PATTERN = re.compile(r"^task_[A-Za-z0-9_-]+$")

@dataclass
class Task:
    id: str
    subject:str
    description:str
    status: str
    owner: str | None
    blockedBy:list[str]
    worktree: str | None = None

def _task_path(task_id:str) -> Path:
    if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError(f"Invalid task id: {task_id!r}")
    task_root = TASK_DIR.resolve()
    path = (task_root / f"{task_id}.json").resolve()

    if not path.is_relative_to(task_root):
        raise ValueError(f"Task path escapes task directory: {task_id!r}")
    return path

def _save_task_unlocked(task: Task) -> None:
    path = _task_path(task.id)
    temp_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        temp_path.write_text(
            json.dumps(asdict(task), indent=2, ensure_ascii=False,),
            encoding="utf-8"
        )
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)

def create_task(subject:str, description: str = "",
                blockedBy:list[str] | None = None) -> Task:
    with TASK_LOCK:
        while True:
            task_id = f"task_{uuid.uuid4().hex}"
            if not _task_path(task_id).exists():
                break

        task = Task(
            id = task_id,
            subject = subject,
            description = description,
            status = "pending",
            owner = None,
            blockedBy = blockedBy or [],
        )
        _save_task_unlocked(task)
        return task

def save_task(task:Task):
    with TASK_LOCK:
        _save_task_unlocked(task)

def load_task(task_id:str) -> Task:
    data = json.loads(_task_path(task_id).read_text(encoding="utf-8"))
    return Task(**data)

def list_tasks() -> list[Task]:
    tasks = []

    for path in sorted(TASK_DIR.glob("task_*.json")):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            tasks.append(Task(**data))
        except (OSError, ValueError, TypeError) as e:
            print(f"[task warning] ignored {path.name}: {e}")

    return tasks

def get_task(task_id:str) -> str:
    task = load_task(task_id)
    return json.dumps(asdict(task), indent=2, ensure_ascii=False)

def can_start(task_id:str) -> bool:
    task = load_task(task_id)
    for dep_id in task.blockedBy:
        if not _task_path(dep_id).exists():
            return False
        if load_task(dep_id).status != "completed":
            return False
    return True

def claim_task(task_id:str, owner:str = "agent") -> str:
    with TASK_LOCK:
        task = load_task(task_id)
        if task.status != "pending":
            return f"Task {task_id} is {task.status}, cannot claim"
        if task.owner:
            return f"Task {task_id} already owned by {task.owner}"
        if not can_start(task_id):
            deps = [d for d in task.blockedBy
                    if not _task_path(d).exists() or load_task(d).status != "completed"]
            return f"Blocked by: {deps}"
        task.owner = owner
        task.status = "in_progress"
        _save_task_unlocked(task)
    print(f"  \033[36m[claim] {task.subject} → in_progress (owner: {owner})\033[0m")
    return f"Claimed {task.id} ({task.subject})"

def complete_task(task_id:str) -> str:
    with TASK_LOCK:
        task = load_task(task_id)
        if task.status != "in_progress":
            return f"Task {task_id} is {task.status}, cannot complete"
        task.status = "completed"
        _save_task_unlocked(task)
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy and can_start(t.id)]
    print(f"  \033[32m[complete] {task.subject} ✓\033[0m")
    msg = f"Completed {task.id} ({task.subject})"
    if unblocked:
        msg += f"\nUnblocked: {', '.join(unblocked)}"
        print(f"  \033[33m[unblocked] {', '.join(unblocked)}\033[0m")
    return msg

#==================== MCP PLUGIN =========================
class MCPClient:
    """Discovers and calls tools on an MCP server (mock for teaching)."""

    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []
        self._handlers: dict[str, callable] = {}

    def register(self, tool_defs: list[dict],
                 handlers: dict[str, callable]):
        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP error: unknown tool '{tool_name}'"
        try:
            return handler(**args)
        except Exception as e:
            return f"MCP error: {e}"


mcp_clients: dict[str, MCPClient] = {}
mcp_lock = threading.RLock()
MCP_TOOL_METADATA: dict[str, dict] = {}

_DISALLOWED_CHARS = re.compile(r'[^a-zA-Z0-9_-]')


def normalize_mcp_name(name: str) -> str:
    """Replace non [a-zA-Z0-9_-] with underscore."""
    return _DISALLOWED_CHARS.sub('_', name)


def _mock_server_docs():
    client = MCPClient("docs")
    client.register(
        tool_defs=[
            {"name": "search", "description": "Search documentation. (readOnly)",
             "inputSchema": {"type": "object",
                             "properties": {"query": {"type": "string"}},
                             "required": ["query"]},
             "annotations": {
                             "readOnly": True,
                             "destructive": False,
                            }
            },
            {"name": "get_version", "description": "Get API version. (readOnly)",
             "inputSchema": {"type": "object", "properties": {},
                             "required": []}},
        ],
        handlers={
            "search": lambda query: f"[docs] Found 3 results for '{query}'",
            "get_version": lambda: "[docs] API v2.1.0",
        })
    return client


def _mock_server_deploy():
    client = MCPClient("deploy")
    client.register(
        tool_defs=[
            {"name": "trigger",
             "description": "Trigger a deployment. (destructive — requires approval in real CC)",
             "inputSchema": {"type": "object",
                             "properties": {"service": {"type": "string"}},
                             "required": ["service"]},
             "annotations": {
                             "readOnly": False,
                             "destructive": True,
                         }
            },
            {"name": "status", "description": "Check deployment status. (readOnly)",
             "inputSchema": {"type": "object",
                             "properties": {"service": {"type": "string"}},
                             "required": ["service"]},
             "annotations": {
                             "readOnly": True,
                             "destructive": False,
                         }
            },
        ],
        handlers={
            "trigger": lambda service: f"[deploy] Triggered: {service}",
            "status": lambda service: f"[deploy] {service}: running (v1.4.2)",
        })
    return client


MOCK_SERVERS = {
    "docs": _mock_server_docs,
    "deploy": _mock_server_deploy,
}


def connect_mcp(name: str) -> str:
    factory = MOCK_SERVERS.get(name)
    if not factory:
        available = ", ".join(MOCK_SERVERS.keys())
        return f"Unknown server '{name}'. Available: {available}"
    
    with mcp_lock:
        if name in mcp_clients:
            return f"MCP server '{name}' already connected"
    
        mcp_client = factory()
        mcp_clients[name] = mcp_client

        try:
            assemble_tool_pool()
        except ValueError as e:
            mcp_clients.pop(name, None)
            return f"Error connecting to MCP server '{name}': {e}"
        
    tool_names = [t["name"] for t in mcp_client.tools]
    print(f"  \033[31m[mcp] connected: {name} → {tool_names}\033[0m")
    return (f"Connected to MCP server '{name}'. "
            f"Discovered {len(mcp_client.tools)} tools: {', '.join(tool_names)}")


def assemble_tool_pool() -> tuple[list[dict], dict]:
    """Assemble builtin tools + all MCP tools into one pool."""
    with mcp_lock:
        tools = list(BUILTIN_TOOLS)
        handlers = dict(BUILTIN_HANDLERS)
        metadata: dict[str, dict] = {}

        for server_name, mcp_client in sorted(mcp_clients.items()):
            safe_server = normalize_mcp_name(server_name)

            for tool_def in sorted(mcp_client.tools, key = lambda item: item["name"]):
                original_tool_name = tool_def["name"]
                safe_tool = normalize_mcp_name(original_tool_name)
                prefixed = f"mcp__{safe_server}__{safe_tool}"

                if prefixed in handlers:
                    raise ValueError(f"MCP tool name collision: {prefixed}")

                schema = tool_def.get("inputSchema") or {
                    "type": "object",
                    "properties": {},
                }

                tools.append({
                    "name": prefixed,
                    "description": tool_def.get("description", ""),
                    "input_schema": schema,
                })

                handlers[prefixed] = (
                    lambda *,
                    client = mcp_client,
                    tool_name = original_tool_name,
                    **kwargs: client.call_tool(tool_name, kwargs)
                )

                annotations = tool_def.get("annotations", {})
                metadata[prefixed] = {
                    "server": server_name,
                    "original_name": original_tool_name,
                    "readOnly": bool(annotations.get("readOnly", False)),
                    "destructive": bool(annotations.get("destructive", annotations.get("destructiveHint", False,))),
                }

        MCP_TOOL_METADATA.clear()
        MCP_TOOL_METADATA.update(metadata)

        return tools, handlers

#==================== WORKTREE SYSTEM ====================
WORKTREES_DIR = WORKDIR / ".worktrees"
WORKTREES_DIR.mkdir(exist_ok=True)

VALID_WT_NAME = re.compile(r'^[A-Za-z0-9._-]{1,64}$')

def validate_worktree_name(name: str) -> str:
    if not name:
        return "Worktree name cannot be empty"
    if name == "." or name == "..":
        return f"'{name}' is not a valid worktree name"
    if not VALID_WT_NAME.fullmatch(name):
        return (f"Invalid worktree name: '{name}': "
                "only letters, digits, dots, underscores, dashes (1-64 chars)")
    return None

def run_git(args: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(["git"] + args, cwd = WORKDIR,
                           capture_output = True, text = True, timeout = 30)
        out = (r.stdout + r.stderr).strip()
        out = out[:5000] if out else "(no output)"
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "Error: git timedout"

def log_event(event_type: str, worktree_name: str, task_id: str = ""):
    event = {
        "type": event_type, "worktree": worktree_name,
        "task_id": task_id, "ts": time.time()
    }
    events_file = WORKTREES_DIR / "events.jsonl"
    with open(events_file, "a") as f:
        f.write(json.dumps(event) + "\n")

def create_worktree(name: str, task_id: str = "") -> str:
    """Create a git worktree with a dedicated branch. Optionally bind to a task."""
    err = validate_worktree_name(name)
    if err:
        return f"Error: {err}"
    path = WORKTREES_DIR / name
    if path.exists():
        return f"Worktree '{name}' already exists at {path}"
    ok, result = run_git(["worktree", "add", str(path), "-b", f"wt/{name}", "HEAD"])
    if not ok:
        return f"Git error: {result}"
    if task_id:
        bind_task_to_worktree(task_id, name)
    log_event("create", name, task_id)
    print(f"  \033[33m[worktree] created: {name} at {path}\033[0m")
    return f"Worktree '{name}' created at {path}"


def bind_task_to_worktree(task_id: str, worktree_name: str):
    """Write worktree field to task. Keep status as pending for auto-claim."""
    with TASK_LOCK:
        task = load_task(task_id)
        task.worktree = worktree_name
        _save_task_unlocked(task)
    print(f"  \033[33m[bind] {task.subject} → worktree:{worktree_name}\033[0m")


def _count_worktree_changes(path: Path) -> tuple[int, int]:
    """Count uncommitted files and commits in a worktree."""
    try:
        r1 = subprocess.run(["git", "status", "--porcelain"],
                            cwd=path, capture_output=True, text=True, timeout=10)
        files = len([l for l in r1.stdout.strip().splitlines() if l.strip()])
        r2 = subprocess.run(["git", "log", "@{push}..HEAD", "--oneline"],
                            cwd=path, capture_output=True, text=True, timeout=10)
        commits = len([l for l in r2.stdout.strip().splitlines() if l.strip()])
        return files, commits
    except Exception:
        return -1, -1


def remove_worktree(name: str, discard_changes: bool = False) -> str:
    """Remove worktree. Refuses if uncommitted changes unless discard_changes."""
    err = validate_worktree_name(name)
    if err:
        return err
    path = WORKTREES_DIR / name
    if not path.exists():
        return f"Worktree '{name}' not found"
    if not discard_changes:
        files, commits = _count_worktree_changes(path)
        if files < 0:
            return (f"Cannot verify worktree '{name}' status. "
                    "Use discard_changes=true to force removal.")
        if files > 0 or commits > 0:
            return (f"Worktree '{name}' has {files} uncommitted file(s) "
                    f"and {commits} unpushed commit(s). "
                    "Use discard_changes=true to force removal, "
                    "or keep_worktree to preserve for review.")
    ok1, _ = run_git(["worktree", "remove", str(path), "--force"])
    if not ok1:
        return f"Failed to remove worktree directory for '{name}'"
    run_git(["branch", "-D", f"wt/{name}"])
    log_event("remove", name)
    print(f"  \033[33m[worktree] removed: {name}\033[0m")
    return f"Worktree '{name}' removed"


def keep_worktree(name: str) -> str:
    """Keep worktree for manual review. Branch preserved."""
    err = validate_worktree_name(name)
    if err:
        return err
    log_event("keep", name)
    print(f"  \033[36m[worktree] kept: {name}\033[0m")
    return f"Worktree '{name}' kept for review (branch: wt/{name})"

#==================== ERROR RECOVERY ===================
DEFAULT_MAX_TOKENS = 8000
ESCALATED_MAX_TOKENS = 64000
MAX_CONTINUATIONS = 3
MAX_TRANSIENT_RETRIES = 10
MAX_REACTIVE_COMPACTS = 1
BASE_DELAY_MS = 500
MAX_CONSECUTIVE_529 = 3

CONTINUATION_PROMPT = (
    "Output token limit hit. Resume directly — "
    "no apology, no recap. Pick up mid-thought."
)

#==================== MEMORY SYSTEM ====================
MEMORY_TYPES = ['user', 'feedback', 'project', 'reference']

def _parse_memory_frontmatter(text:str) -> tuple[dict,str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()

def write_memory_file(name:str, mem_type:str, description:str, body:str):
    slug = name.lower().replace(" ","-").replace("/","-")
    filename = f"{slug}.md"
    filepath = MEMORY_DIR / filename
    filepath.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n{body}\n"
    )
    _rebuild_index()
    return filepath

def _rebuild_index():
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md": continue
        raw = f.read_text()
        meta, body = _parse_memory_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({f.name}) — {desc}")
    MEMORY_INDEX.write_text("\n".join(lines) + "\n" if lines else "")

def read_memory_index() -> str:
    if not MEMORY_INDEX.exists():
        return ""
    text = MEMORY_INDEX.read_text().strip()
    return text if text else ""

def read_memory_file(filename:str) -> str | None:
    path = MEMORY_DIR / filename
    if not path.exists():
        return None
    return path.read_text()

def list_memory_files() -> list[dict]:
    result = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md": continue
        raw = f.read_text()
        meta, body = _parse_memory_frontmatter(raw)
        result.append({
            "filename": f.name,
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "user"),
            "body":body,
        })
    return result

def select_relevant_memories(messages: list, max_items: int = 5) -> list[str]:
    files = list_memory_files()
    if not files:
        return []
    
    recent_texts = []
    for msg in reversed(messages):
        content = msg.get("content","")
        if isinstance(content,list):
            content = " ".join(
                str(getattr(b,"text","")) for b in content
                if getattr(b,"type",None) == "text"
            )
        if _is_internal_reminder_text(content.strip()):
            continue
        if isinstance(content, str):
            recent_texts.append(content)
        if len(recent_texts) >= 5:
            break

    recent = " ".join(reversed(recent_texts))[:2000]

    if not recent.strip():
        return []
    
    catalog_lines = []
    for i, f in enumerate(files):
        catalog_lines.append(f"{i}: {f['name']} — {f['description']}")
    catalog = "\n".join(catalog_lines)

    prompt = (
        "Given the recent conversation and the memory catalog below, "
        "select the indices of memories that are clearly relevant. "
        "Return ONLY a JSON array of integers, e.g. [0, 3]. "
        "If none are relevant, return [].\n\n"
        f"Recent conversation:\n{recent}\n\n"
        f"Memory catalog:\n{catalog}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 200,
        )
        text = extract_text(response.content).strip()

        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            for idx in indices:
                if isinstance(idx, int) and 0<= idx < len(files):
                    selected.append(files[idx]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass

    keywords = [w.lower() for w in recent.split() if len(w) > 3]
    selected = []
    for f in files:
        text = (f["name"] + " " + f["description"]).lower()
        if any(kw in text for kw in keywords):
            selected.append(f["filename"])
            if len(selected) >= max_items:
                break
    return selected

def load_memories(messages:list) -> str:
    selected_files = select_relevant_memories(messages)
    if not selected_files:
        return ""
    
    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(filename)
        if content:
            parts.append(content)
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)

def _is_internal_reminder_text(text:str) -> bool:
    text = text.strip().lower()
    return text.startswith("<reminder>") or text.startswith("</reminder>")

def extract_memories(messages:list) -> list[dict]:
    dialoge_parts = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content,list):
            content = " ".join(
                str(getattr(b,"text","")) for b in content
                if getattr(b,"type",None) == "text"
            )
        if isinstance(content,str) and content.strip():

            if role == "user" and _is_internal_reminder_text(content.strip()):
                continue

            dialoge_parts.append(f"{role}: {content}")
    dialogue = "\n".join(dialoge_parts)

    if not dialogue.strip():
        return
    
    existing = list_memory_files()
    existing_desc = "\n".join(f"- {m['name']}: {m['description']}" for m in existing) if existing else "(none)"

    prompt = (
        "Extract user preferences, constraints, or project facts from this dialogue.\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n"
        "- name: short kebab-case identifier (e.g. 'user-preference-tabs')\n"
        "- type: one of 'user' (user preference), 'feedback' (guidance), "
        "'project' (project fact), 'reference' (external pointer)\n"
        "- description: one-line summary for index lookup\n"
        "- body: full detail in markdown\n"
        "If nothing new or already covered by existing memories, return [].\n\n"
        f"Existing memories:\n{existing_desc}\n\n"
        f"Dialogue:\n{dialogue[:4000]}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 800,
        )
        text = extract_text(response.content).strip()

        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return 
        count = 0
        for mem in items:
            name = mem.get("name",f"memory_{int(time.time())}")
            mem_type = mem.get("type","user")
            desc = mem.get("description","")
            body = mem.get("body","")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)
                count += 1
        if count:
            print(f"\n\033[33m[Memory: extracted {count} new memories]\033[0m")
    except Exception:
        pass

CONSOLIDATE_THRESHOLD = 10

def consolidate_memories():
    files = list_memory_files()
    if len(files) < CONSOLIDATE_THRESHOLD:
        return
    
    catalog = "\n".join(
        f"## {f['filename']}\nname: {f['name']}\ndescription: {f['description']}\n{f['body']}"
        for f in files
    )

    prompt = (
        "Consolidate the following memory files. Rules:\n"
        "1. Merge duplicates into one\n"
        "2. Remove outdated/contradicted memories\n"
        "3. Keep the total under 30 memories\n"
        "4. Preserve important user preferences above all\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n\n"
        f"{catalog[:16000]}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 3000,
        )
        text = extract_text(response.content).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        
        for f in MEMORY_DIR.glob("*.md"):
            if f.name != "MEMORY.md":
                f.unlink()

        for mem in items:
            name = mem.get("name",f"memory_{int(time.time())}")
            mem_type = mem.get("type","user")
            desc = mem.get("description","")
            body = mem.get("body","")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)

        print(f"\n\033[33m[Memory: consolidated {len(files)} → {len(items)} memories]\033[0m")
    except Exception:
        pass

def find_latest_text_user_message(messages: list) -> int | None:
      for i in range(len(messages) - 1, -1, -1):
          msg = messages[i]
          if msg.get("role") != "user":
              continue

          content = msg.get("content")
          if not isinstance(content, str) or not content.strip():
              continue

          if content.strip().startswith("<reminder>"):
              continue

          return i

      return None

def build_request_messages_with_memories(messages:list):
    memories = load_memories(messages)
    if not memories:
        return messages

    target = find_latest_text_user_message(messages)
    if target is None:
        return messages

    request_messages = messages.copy()
    request_messages[target] = {
        **messages[target],
        "content": messages[target]["content"] + "\n\n" + memories,
    }
    return request_messages

#==================== TODO SYSTEM ====================
def format_current_todos() -> str:
    if not CURRENT_TODOS:
        return ""
    return "\n".join(
        f"- [{t['status']}] {t['content']}"
        for t in CURRENT_TODOS
    )

#==================== SKILL LOADING ====================
def _parse_skill_frontmatter(text:str) -> dict:
    """Parse YAML frontmatter from SKILL.md. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].strip()

SKILL_REGISTRY:dict[str, dict] = {}

def _scan_skills():
    if not SKILLS_DIR.exists():
        return
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "SKILL.md"
        if manifest.exists():
            raw = manifest.read_text()
            meta, body = _parse_skill_frontmatter(raw)
            name = meta.get("name", d.name)
            desc = meta.get("description", raw.split("\n")[0].lstrip("#").strip())
            SKILL_REGISTRY[d.name] = {"name": name, "description": desc, "content": raw}

_scan_skills()

def list_skills() -> str:
    if not SKILL_REGISTRY:
        return "(no skills found)"
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILL_REGISTRY.values())


#==================== TOOL SYSTEM ====================
def run_bash(command:str, run_in_background: bool = False, cwd: str | Path | None = None) -> str:
    try:
        base = resolve_tool_cwd(cwd)
        r = subprocess.run(command, shell=True, cwd = base,
                           capture_output=True, text=True, timeout = 120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"
    
def run_read(path:str, offset:int = 0, limit:int | None = None, cwd: str | Path | None = None) -> str:
    try:
        lines = safe_path(path, cwd=cwd).read_text().splitlines()
        
        offset = max(0, offset)
        if limit is None:
            limit = 1000
        else:
            limit = max(1, min(limit, 1000))

        end = min(offset + limit, len(lines))

        result = lines[offset: end]
        if end < len(lines):
            result.append(f"... ({len(lines) - end} more lines);"
                          f"continue with offset={end}"
                          )
        return "\n".join(result)
    except Exception as exc:
        return f"Error: {exc}"
    
def run_write(path:str,content:str, cwd: str | Path | None = None) -> str:
    try:
        file_path = safe_path(path, cwd=cwd)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_edit(path:str,old_text:str,new_text:str, cwd: str | Path | None = None) -> str:
    try:
        file_path = safe_path(path, cwd=cwd)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text,new_text,1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_glob(pattern:str, cwd: str | Path | None = None) -> str:
    import glob as g
    try:
        base = resolve_tool_cwd(cwd)
        results = []
        for match in g.glob(pattern,root_dir=base):
            path = (base / match).resolve()
            if path.is_relative_to(base):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"
    
def _normalize_todos(todos):
    if isinstance(todos,str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos,list):
        return None, "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None

def run_todo_write(todos:list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"}[t["status"]]
        #print(t, icon)
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"

def load_skill(name:str) -> str:
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        return f"Skill not found: {name}"
    return skill["content"]

def run_create_task(subject: str, description: str = "", blockedBy: list[str] | None = None) -> str:
    task = create_task(subject, description,blockedBy)
    deps = f" (blocked by: {", ".join(blockedBy)})" if blockedBy else ""
    print(f"  \033[34m[create] {task.subject}{deps}\033[0m")
    return f"Created {task.id}: {task.subject}{deps}"

def run_list_tasks() -> str:
    tasks = list_tasks()
    if not tasks:
        return "No tasks. Use create_task to add some."
    lines = []
    for t in tasks:
        icon = {"pending": "○", "in_progress": "●",
                "completed": "✓"}.get(t.status, "?")
        deps = f" (blocked by: {', '.join(t.blockedBy)})"
        owner = f"[{t.owner}]" if t.owner else ""
        lines.append(f"  {icon} {t.id}: {t.subject} "
                     f"[{t.status}]{owner}{deps}")
    return "\n".join(lines)

def run_get_task(task_id: str) -> str:
    try:
        return get_task(task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot read task {task_id}: {exc}"
    
def run_claim_task(task_id: str) -> str:
    try:
        return claim_task(task_id, owner = "agent")
    except (OSError, ValueError, TypeError) as e:
        return f"Error: cannot claim task {task_id}: {e}"

def run_complete_task(task_id: str) -> str:
    try:
        return complete_task(task_id)
    except (OSError, ValueError, TypeError) as e:
        return f"Error: cannot complete task {task_id}: {e}"

def run_schedule_cron(cron: str, prompt: str,
                      recurring: bool = True, durable: bool = True) -> str:
    result = schedule_job(cron, prompt, recurring, durable)
    if isinstance(result, str):
        return f"Error: {result}"
    return f"Scheduled {result.id}: '{cron}' → '{prompt}'"

def run_list_crons() -> str:
    with cron_lock:
        jobs = list(scheduled_jobs.values())
    if not jobs:
        return "No cron jobs. Use schedule_cron to add one."
    lines = []
    for j in jobs:
        tag = "recurring" if j.recurring else "one-shot"
        dur = "durable" if j.durable else "session"
        lines.append(f"  {j.id}: '{j.cron}' → {j.prompt[:40]} "
                             f"[{tag}, {dur}]")
    return "\n".join(lines)

def run_cancel_cron(job_id: str) -> str:
    return cancel_job(job_id)

def run_create_worktree(name: str, task_id: str = "") -> str:
    return create_worktree(name, task_id)

def run_remove_worktree(name: str, discard_changes: bool = False) -> str:
    return remove_worktree(name, discard_changes)

def run_keep_worktree(name: str) -> str:
    return keep_worktree(name)

def run_connect_mcp(name: str) -> str:
    return connect_mcp(name)

BUILTIN_TOOLS = [
    {"name": "bash", 
     "description": "Run a shell command.",
     "input_schema": {"type": "object", 
                      "properties": {"command": {"type": "string"}, "run_in_background": {"type": "boolean","description": "Run this command asynchronously"}}, 
                      "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "todo_write", "description": "Create and manage a task list for your current coding session.",
     "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]}},
    {"name": "load_skill", "description": "Load the content of a skill by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "compact",
     "description": "Summarize earlier conversation and continue with compacted context.",
     "input_schema": {"type": "object",
                      "properties": {"focus": {"type": "string"}},
                      "required": []}},
    {"name": "create_task", "description": "Create a new task with optinal blockedBy dependencies.",
     "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "description": {"type": "string"}, "blockedBy": {"type": "array", "items": {"type": "string"}}}, "required": ["subject"]}},
    {"name": "list_tasks", 
     "description": "List all tasks with status, owner, and denpendencies.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "get_task",
     "description": "Get full details of a specific task by ID.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "claim_task",
     "description": "Claim a pending task. Sets owner, changes status to in_progress.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "complete_task",
     "description": "Complete an in-progress task. Reports unblocked downstream tasks.",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "spawn_teammate",
     "description": "Spawn a teammate agent in a background thread.",
     "input_schema": {"type": "object",
                      "properties": {
                          "name": {"type": "string"},
                          "role": {"type": "string"},
                          "prompt": {"type": "string"}},
                      "required": ["name", "role", "prompt"]}},
    {"name": "send_message",
     "description": "Send a message to a teammate via MessageBus.",
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["to", "content"]}},
    {"name": "check_inbox",
     "description": "Check Lead's inbox for teammate messages.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "schedule_cron",
         "description": "Schedule a cron job. cron is 5-field: min hour dom month dow.",
         "input_schema": {"type": "object",
                          "properties": {
                              "cron": {"type": "string",
                                       "description": "5-field cron expression"},
                              "prompt": {"type": "string",
                                         "description": "Message to inject when fired"},
                              "recurring": {"type": "boolean",
                                            "description": "True=recurring, False=one-shot"},
                              "durable": {"type": "boolean",
                                          "description": "True=persist to disk"}},
                          "required": ["cron", "prompt"]}},
        {"name": "list_crons",
         "description": "List all registered cron jobs.",
         "input_schema": {"type": "object", "properties": {},
                          "required": []}},
        {"name": "cancel_cron",
         "description": "Cancel a cron job by ID.",
         "input_schema": {"type": "object",
                          "properties": {"job_id": {"type": "string"}},
                          "required": ["job_id"]}},
        {"name": "request_shutdown",
             "description": "Request a teammate to shut down gracefully.",
             "input_schema": {"type": "object",
                              "properties": {"teammate": {"type": "string"}},
                              "required": ["teammate"]}},
        {"name": "request_plan",
            "description": "Ask a teammate to submit a plan for review.",
            "input_schema": {"type": "object",
                            "properties": {"teammate": {"type": "string"},
                                            "task": {"type": "string"}},
                            "required": ["teammate", "task"]}},
        {"name": "review_plan",
            "description": "Approve or reject a submitted plan by request_id.",
            "input_schema": {"type": "object",
                            "properties": {
                                "request_id": {"type": "string"},
                                "approve": {"type": "boolean"},
                                "feedback": {"type": "string"}},
                            "required": ["request_id", "approve"]}},
        {"name": "create_worktree",
             "description": "Create an isolated git worktree with its own branch.",
             "input_schema": {"type": "object",
                              "properties": {"name": {"type": "string"},
                                             "task_id": {"type": "string"}},
                              "required": ["name"]}},
        {"name": "remove_worktree",
            "description": "Remove a worktree. Refuses if uncommitted changes unless discard_changes=true.",
            "input_schema": {"type": "object",
                            "properties": {"name": {"type": "string"},
                                            "discard_changes": {"type": "boolean"}},
                            "required": ["name"]}},
        {"name": "keep_worktree",
            "description": "Keep a worktree for manual review.",
            "input_schema": {"type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"]}},
        {"name": "connect_mcp",
             "description": "Connect to an MCP server (docs, deploy) and discover tools.",
             "input_schema": {"type": "object",
                              "properties": {"name": {"type": "string"}},
                              "required": ["name"]}},
]

BUILTIN_HANDLERS = {
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
    "todo_write":run_todo_write,
    "load_skill":load_skill,
    "create_task":run_create_task,
    "list_tasks":run_list_tasks,
    "get_task":run_get_task,
    "claim_task":run_claim_task,
    "complete_task":run_complete_task,
    "spawn_teammate":run_spawn_teammate,
    "send_message":run_send_message,
    "check_inbox":run_check_inbox,
    "schedule_cron":run_schedule_cron,
    "list_crons":run_list_crons,
    "cancel_cron":run_cancel_cron,
    "request_shutdown": run_request_shutdown,
    "request_plan": run_request_plan,
    "review_plan": run_review_plan,
    "create_worktree": run_create_worktree,
    "remove_worktree": run_remove_worktree,
    "keep_worktree": run_keep_worktree,
    "connect_mcp": run_connect_mcp,
}

#==================== SUBAGENT SYSTEM ====================
SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Complete the task you were given, then return a concise summary. "
    "Do not delegate further."
)

SUB_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
]

SUB_HANDLERS = {
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
}

def extract_text(content) -> str:
    if not isinstance(content,list):
        return str(content)
    return "\n".join(getattr(b,"text","") for b in content if getattr(b,"type",None) == "text")

def has_tool_use(content) -> bool:
    return any(
        (block.get("type")
        if isinstance(block, dict) else getattr(block, "type", None)) == "tool_use"
        for block in content
    )

def spawn_subagent(description:str) -> str:
    print(f"\n\033[35m[Subagent spawned]\033[0m")
    messages = [{"role": "user", "content": description}]  # fresh context

    state = RecoveryState(
        current_model=PRIMARY_MODEL,
        fallback_model=FALLBACK_MODEL,
    )

    for _ in range(30):
        try:
            response = with_retry(lambda: client.messages.create(
                model = state.current_model,
                system = SUB_SYSTEM,
                messages = messages,
                tools = SUB_TOOLS,
                max_tokens = DEFAULT_MAX_TOKENS,
            ), state,
            max_transient_retries=MAX_TRANSIENT_RETRIES,
            max_consecutive_529=MAX_CONSECUTIVE_529,
            base_delay_ms=BASE_DELAY_MS)
        except Exception as exc:
            error = f"[Subagent error] {type(exc).__name__}: {str(exc)[:300]}"
            print(f"  \033[31m{error}\033[0m")
            return error
        
        messages.append({"role":"assistant","content":response.content})
        if not has_tool_use(response.content):
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                blocked = trigger_hook("PreToolUse", block)
                if blocked:
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": str(blocked)})
                    continue
                handler = SUB_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
                trigger_hook("PostToolUse", block, output)
                print(f"  \033[90m[sub] {block.name}: {str(output)[:100]}\033[0m")
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output})
        messages.append({"role":"user","content":results})

    result = extract_text(messages[-1]["content"])
    if not result:
        for msg in reversed(messages):
            result = extract_text(msg["content"])
            if result:
                break
        if not result:
            result = "Subagent stopped after 30 turns without final answer."
    print(f"\033[35m[Subagent done]\033[0m")
    return result

BUILTIN_TOOLS.append({
    "name": "task",
    "description": "Launch a subagent to handle a complex subtask. Returns only the final conclusion.",
    "strict": True,
    "input_schema": {"type": "object", 
                     "properties": {
                         "description": {"type": "string", 
                                         "description": "Complete instructions sent verbatim to the subagent. This is the only accepted parameter."}}, 
                     "required": ["description"], 
                     "additionalProperties": False},
})
BUILTIN_HANDLERS["task"] = spawn_subagent

#==================== COMPACTION PIPELINE ====================
CONTEXT_LIMIT = 50_000
KEEP_RECENT = 3
PERSIST_THRESHOLD = 20_000

def estimate_size(messages:list) -> int: return len(str(messages))

def _block_get(block, key, default=None):
    if isinstance(block,dict):
        return block.get(key, default)
    return getattr(block, key, default)

def _block_type(block) -> str:
    return _block_get(block, "type")

def _message_has_tool_use(msg:list) -> bool:
    if msg.get("role") != "assistant":
        return False
    content = msg.get("content")
    if not isinstance(content,list):
        return False
    return any(_block_type(b) == "tool_use" for b in content)

def _is_tool_result_message(msg):
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if not isinstance(content,list):
        return False
    return all(isinstance(b,dict) and b.get("type") == "tool_result" for b in content)

# L1:snipCompact
def snip_compact(messages,max_messages=500):
    if len(messages) <= max_messages: return messages
    keep_head, keep_tail = 3, max_messages - 3
    head_end, tail_start = keep_head, len(messages) - keep_tail
    if head_end > 0 and _message_has_tool_use(messages[head_end-1]):
        while head_end < len(messages) and _is_tool_result_message(messages[head_end]):
            head_end += 1
    if (tail_start > 0 and tail_start < len(messages) 
        and _message_has_tool_use(messages[tail_start - 1]) 
        and _is_tool_result_message(messages[tail_start])):
            tail_start -= 1
    if head_end >= tail_start:
        return messages
    snipped = tail_start - head_end
    return messages[: head_end] + [{"role": "user", "content":f"[snipped {snipped} messages]"}] + messages[tail_start:]

#L2: microCompact
PRESERVE_TOOL_RESULTS = ["task","load_skill"]

def collect_tool_results(messages:list) -> list:
    blocks = []
    for mi,msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"),list): continue
        for bi,block in enumerate(msg["content"]):
            if isinstance(block,dict) and block.get("type") == "tool_result":
                blocks.append((mi,bi,block))
    return blocks

def build_tool_use_name_map(messages: list) -> dict[str, str]:
    mapping = {}
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if _block_type(block) == "tool_use":
                tool_id = _block_get(block, "id", None)
                tool_name = _block_get(block, "name", None)
                
                if tool_id and tool_name:
                    mapping[str(tool_id)] = tool_name

    return mapping

def micro_compact(messages):
    tool_results = collect_tool_results(messages)
    if len(tool_results) < KEEP_RECENT:
        return messages
    
    tool_name = build_tool_use_name_map(messages)

    for _, _, block in tool_results[:-KEEP_RECENT]:
        content = str(block.get("content", ""))
        tid = block.get("tool_use_id")
        tname = tool_name.get(tid)

        if "<persisted-output>" in content:
            continue

        if tname in PRESERVE_TOOL_RESULTS:
            continue

        if len(content) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
    return messages

#L3: toolResultBudget
def persist_large_output(tool_use_id, output):
    if len(output) <= PERSIST_THRESHOLD: return output
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOL_RESULTS_DIR / f"{tool_use_id}.txt"
    if not path.exists(): path.write_text(output, encoding="utf-8")
    return f"<persisted-output>\nFull output: {path}\nPreview:\n{output[:2000]}\n</persisted-output>"


def tool_result_budget(messages,max_bytes=20_000):
    last = messages[-1] if messages else None
    if not last or last.get("role") != "user" or not isinstance(last.get("content"),list): return messages
    blocks = [(i, b) for i, b in enumerate(last["content"]) if isinstance(b,dict) and b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes: return messages
    ranked = sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True)
    for _, block in ranked:
        if total <= max_bytes: break
        content = str(block.get("content", ""))
        if len(content) <= PERSIST_THRESHOLD: continue
        tid = block.get("tool_use_id", "unknown")
        block["content"] = persist_large_output(tid, content)
        total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    return messages

#L4: autoCompact
def write_transcript(messages):
    TRANSCRIPTS_DIR.mkdir(parents=True,exist_ok=True)
    path=TRANSCRIPTS_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w") as f:
        for msg in messages: f.write(json.dumps(msg,default=str) + "\n")
    return path

def summarize_history(messages):
    conversation = json.dumps(messages, default=str)[:80000]
    prompt = ("Summarize this coding-agent conversation so work can continue.\n"
              "Preserve: 1. current goal, 2. key findings/decisions, 3. files read/changed, "
              "4. remaining work, 5. user constraints.\nBe compact but concrete.\n\n" + conversation)
    response = client.messages.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
    return "\n".join(
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", None) == "text").strip() or "(empty summary)"

def compact_history(messages):
    transcript_path = write_transcript(messages)
    print(f"[transcript saved: {transcript_path}]")
    summary = summarize_history(messages)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]

#Emergency: reactiveCompact
def reactive_compact(messages):
    transcript = write_transcript(messages)
    tail_start = max(0, len(messages) - 5)
    if (tail_start > 0 and tail_start < len(messages)
            and _is_tool_result_message(messages[tail_start])
            and _message_has_tool_use(messages[tail_start - 1])):
        tail_start -= 1
    summary = summarize_history(messages[:tail_start])
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}, *messages[tail_start:]]



#==================== HOOK SYSTEM ====================
HOOKS = {"UserPromptSubmit":[],"PreToolUse":[],"PostToolUse":[],"Stop":[]}

def register_hook(event:str,callback):
    HOOKS[event].append(callback)

def trigger_hook(event:str,*args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None

DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777", "curl"]

def permission_hook(block):
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command",""):
                print(f"\n\033[31m⛔ Blocked: '{pattern}'\033[0m")
                return "Permission denied by deny list"
        for kw in DESTRUCTIVE:
            if kw in block.input.get("command",""):
                print(f"\n\033[33m⚠  Potentially destructive command\033[0m")
                print(f"   Tool: {block.name}({block.input})")

                agent = getattr(block, "agent", None)
                if agent:
                    prompt = f"  Allow teammate '{agent}' to apply this change? [y/N] "
                else:
                    prompt = "  Allow this change? [y/N] "
                choice = input(prompt).strip().lower()
                if choice not in ("y","yes"):
                    return "Permission denied by user"

    if block.name.startswith("mcp__"):
        with mcp_lock:
            metadata = dict(
                MCP_TOOL_METADATA.get(block.name, {})
            )

        if not metadata:
            return ("Permission denied: unknown MCP tool metadata")

        if metadata.get("destructive"):
            print(f"\n\033[33m⚠  Potentially destructive MCP tool\033[0m")
            print(f"  Server: {metadata['server']}\n"
                  f"  Tool: {metadata['original_name']}\n"
                  f"  Input: {block.input}")

            choice = input("  Allow this MCP action? [y/N] ").strip().lower()
            if choice not in ("y","yes"):
                return "Permission denied by user"
        
    return None

def log_hook(block):
    args_preview = str(list(block.input.values())[:2])[:60]
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block,output):
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ Large output from {block.name}: {len(str(output))} chars\033[0m")
    return None

def context_inject_hook(query:str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None

def summary_hook(messages:list):
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"),list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

def diff_preview_hook(block):
    if block.name not in ("write_file","edit_file"):
        return None
    
    path = block.input.get("path","")
    try:
        file_path = safe_path(path, getattr(block, "cwd", None))
    except Exception as e:
        return(f"[HOOK] Error: {e}")

    old_text = file_path.read_text() if file_path.exists() else ""

    if block.name == "write_file":
        new_text = block.input.get("content","")
    else:
        old_price = block.input.get("old_text","")
        new_price = block.input.get("new_text","")
        if old_price not in old_text:
            return None
        new_text = old_text.replace(old_price,new_price,1)

    diff = difflib.unified_diff(
        old_text.splitlines(), 
        new_text.splitlines(),
        fromfile=f"{path}before",
        tofile=f"{path}after",
        lineterm="",
        )
    
    print("\n".join(diff) or "(no diff)")
    choice = input("  Apply change? [y/N] ").strip().lower()
    if choice not in ("y","yes"):
        return "File change rejected by user"
    
    return None

register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PreToolUse", diff_preview_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)

#==================== SYSTEM PROMPT ASSEMBLY ====================
PROMPT_SECTIONS = {
    "identity": "You are a coding agent. Act, don't explain.",
    "workspace": f"Working directory: {WORKDIR}",
    "tools": f"Available tools: ",
}

def assemble_system_prompt(context:dict) -> str:
    sections = []
    sections.append(PROMPT_SECTIONS["identity"])
    sections.append(PROMPT_SECTIONS["tools"] + ', '.join(context.get('enabled_tools', [])))
    sections.append(PROMPT_SECTIONS["workspace"])
    current_time = context.get("current_time")
    if not current_time:
        current_time = datetime.now().isoformat(timespec="seconds")
    sections.append(f"Current time: {current_time}")

    sections.append(
        "Coordination rules:\n"
        "- todo_write manages the temporary plan for the current session.\n"
        "- create_task manages the durable shared task graph.\n"
        "- task runs a synchronous one-shot subagent and waits for its result.\n"
        "- spawn_teammate starts an asynchronous persistent teammate.\n"
        "- A teammate that submits a plan must wait for Lead approval."
    )

    memories = context.get("memories","")
    if memories:
        sections.append(f"Memory index:\n{memories}")

    skills = context.get("skills")
    if skills:
        sections.append(
            "Skills catalog:\n"
            f"{skills}\n"
            "Use load_skill(name) when a skill is relevant."
        )

    todos = context.get("todos", "")
    if todos:
        sections.append(f"Current session todos:\n{todos}")

    active_names = context.get("active_teammates", [])
    if active_names:
        sections.append(f"Active teammates:\n{', '.join(active_names)}")

    connect_mcp = context.get("connect_mcp", [])
    if connect_mcp:
        sections.append(f"Connected MCP servers:\n{', '.join(connect_mcp)}")

    return "\n\n".join(sections)

_last_context_key = None
_last_prompt = None

def get_system_prompt(context:dict) -> str:
    global _last_context_key, _last_prompt
    key = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    if key == _last_context_key and _last_prompt:
        print("  \033[90m[cache hit] system prompt unchanged\033[0m")
        return _last_prompt
    _last_context_key = key
    _last_prompt = assemble_system_prompt(context)
    
    loaded = ["identity","tools","workspace"]
    if context.get("memories"):
        loaded.append("memory")
    if context.get("todos"):
        loaded.append("todos")
    print(f"  \033[32m[assembled] sections: {', '.join(loaded)}\033[0m")
    return _last_prompt

def update_context(context:dict,messages:list, tools: list[dict] | None = None) -> dict:
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    skills = list_skills() if SKILL_REGISTRY else ""

    if tools is None:
        tools, _ = assemble_tool_pool()
    tool_names = sorted(tool["name"] for tool in tools)
    serialized_tools = json.dumps(tools, ensure_ascii=False, sort_keys=True)
    tool_fingerprint = hashlib.sha256(serialized_tools.encode("utf-8")).hexdigest()

    with mcp_lock:
        connected_mcp = sorted(mcp_clients)

    todos = format_current_todos()

    with team_lock:
        active_names = sorted(active_teammates)

    return {
        "enabled_tools": tool_names,
        "workspace": str(WORKDIR),
        "memories": memories,
        "skills": skills,
        "todos": todos,
        "active_teammates": active_names,
        "connect_mcp": connected_mcp,
        "tool_fingerprint": tool_fingerprint,
        "current_time": datetime.now().isoformat(timespec="seconds"),
    }

#==================== AGENT LOOP ====================
rounds_since_todo = 0

def agent_loop(messages:list, context:dict):
    global rounds_since_todo
    state = RecoveryState(
        current_model=PRIMARY_MODEL,
        fallback_model=FALLBACK_MODEL,
    )
    max_tokens = DEFAULT_MAX_TOKENS

    while True:
        fired_jobs = consume_cron_queue()
        pending_texts = [
            f"[Scheduled: {job.id}] {job.prompt}"
            for job in fired_jobs
        ]
        pending_texts.extend(collect_background_results())
        team_messages = collect_lead_inbox()
        if team_messages:
            pending_texts.append(
                format_team_inbox(team_messages)
            )

        append_user_text_blocks(messages,pending_texts)

        pre_compact_messages = copy.deepcopy(messages)

        messages[:] = tool_result_budget(messages)
        messages[:] = snip_compact(messages)
        messages[:] = micro_compact(messages)

        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[auto compact]")
            messages[:] = compact_history(messages)

        if rounds_since_todo >=3:
            messages.append(
                {"role":"user",
                 "content":"<reminder> Update your todos.</reminder>"}
            )
            rounds_since_todo = 0

        tools, handlers = assemble_tool_pool()
        context = update_context(context, messages, tools= tools)
        system = get_system_prompt(context)

        request_messages = build_request_messages_with_memories(messages)

        try:
            def call_llm():
                return create_message_streaming(
                    system=system,
                    request_messages=request_messages,
                    model=state.current_model,
                    max_tokens=max_tokens,
                    tools=tools,
                )

            response = with_retry(
                call_llm,
                state,
                max_transient_retries=MAX_TRANSIENT_RETRIES,
                max_consecutive_529=MAX_CONSECUTIVE_529,
                base_delay_ms=BASE_DELAY_MS,
            )
        except PartialStreamError as stream_exc:
            state.has_escalated = True
            max_tokens = ESCALATED_MAX_TOKENS
            partial_text = stream_exc.partial_text

            if state.continuation_count < MAX_CONTINUATIONS:
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": partial_text,
                    }],
                })
                state.continuation_count += 1
                messages.append({
                    "role": "user",
                    "content": CONTINUATION_PROMPT,
                })
                print(
                    f"  \033[33m[stream interrupted] continuation "
                    f"{state.continuation_count}/{MAX_CONTINUATIONS} "
                    f"with {ESCALATED_MAX_TOKENS} tokens\033[0m"
                )
                continue

            cause_text = (
                f"{type(stream_exc.cause).__name__}: "
                f"{str(stream_exc.cause)[:300]}"
            )
            marker = f"[Stream interrupted: {cause_text}]"
            separator = "" if partial_text.endswith("\n") else "\n"
            print(marker)
            messages.append({
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": f"{partial_text}{separator}{marker}",
                }],
            })
            return update_context(context, messages)
        except Exception as e:
            if (
                is_prompt_too_long_error(e)
                and state.reactive_compact_count < MAX_REACTIVE_COMPACTS
            ):
                state.reactive_compact_count += 1
                try:
                     messages[:] = reactive_compact(messages)
                except Exception as compact_exc:
                    append_unrecoverable_error(messages, compact_exc)
                    return update_context(context, messages)
                
                print("[recovery] reactive compact")
                continue
            
            append_unrecoverable_error(messages, e)
            return update_context(context, messages)
        
        if response.stop_reason == "max_tokens":
            messages.append({
                "role": "assistant",
                "content": response.content,
            })
            truncated_tool_uses = [
                block for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]
            if truncated_tool_uses:
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                "Tool call was not executed because the "
                                "response hit the output token limit."
                            ),
                            "is_error": True,
                        }
                        for block in truncated_tool_uses
                    ],
                })
            state.has_escalated = True
            max_tokens = ESCALATED_MAX_TOKENS

            if state.continuation_count < MAX_CONTINUATIONS:
                state.continuation_count += 1
                if truncated_tool_uses:
                    messages[-1]["content"].append({
                        "type": "text",
                        "text": CONTINUATION_PROMPT,
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": CONTINUATION_PROMPT,
                    })

                print(
                    f"  \033[33m[max_tokens] continuation "
                    f"{state.continuation_count}/{MAX_CONTINUATIONS} "
                    f"with {ESCALATED_MAX_TOKENS} tokens\033[0m"
                )
                continue

            print("  \033[31m[max_tokens] recovery limit reached\033[0m")
            return update_context(context, messages)

        messages.append({"role":"assistant","content":response.content})
        if not has_tool_use(response.content):
            force = trigger_hook("Stop",messages)
            if force:
                messages.append({"role":"user","content": force})
                continue
            
            if wait_for_team_activity(messages):
                continue

            extract_memories(pre_compact_messages)
            consolidate_memories()

            context = update_context(context, messages)
            return context
        
        rounds_since_todo += 1
        results = []
        compacted_now = False

        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")

            if block.name == "compact":
                messages[:] = compact_history(messages)
                messages.append({
                    "role": "user",
                    "content": (
                        "[Compacted. Continue with summarized context.]"
                    ),
                })
                compacted_now = True
                break

            blocked = trigger_hook("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                continue

            if should_run_background(block.name, block.input):
                bg_id = start_background_task(block, handlers)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"[Background task {bg_id} started] "
                                           f"Command: {block.input.get('command', '')}. "
                                           f"Result will be available when complete."})
                continue
                
            output = execute_tool(block, handlers)
            trigger_hook("PostToolUse", block, output)

            if block.name == "todo_write":
                rounds_since_todo = 0
            
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        if compacted_now:
            continue

        user_content = list(results)
        bg_notifications = collect_background_results()
        if bg_notifications:
            user_content.extend([{"type": "text", "text": notif} for notif in bg_notifications])
        print(f"  \033[32m[inject] {len(bg_notifications)} background "
                  f"notification(s)\033[0m")
        messages.append({"role":"user","content":user_content})

session_history: list = []
session_context: dict = {}

def run_agent_turn_locked(user_query: str | None = None):
    global session_context

    if user_query:
        session_history.append({"role": "user", "content": user_query})

    session_context = agent_loop(session_history, session_context)
    session_context = update_context(session_context, session_history)
    print()


def create_message_streaming(system, request_messages, *, model, max_tokens, tools):
    chunks = []
    try:
        with client.messages.stream(
            model=model,
            system=system,
            messages=request_messages,
            tools=tools,
            max_tokens=max_tokens,
        ) as stream:
            for chunk in stream.text_stream:
                if not chunk:
                    continue
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            return stream.get_final_message()
    except Exception as exc:
        if chunks:
            raise PartialStreamError("".join(chunks), exc) from exc
        raise
    finally:
        if chunks and not chunks[-1].endswith("\n"):
            print()

def append_user_text_blocks(messages: list, texts: list[str]):
    if not texts:
        return
    
    blocks = [
        {"type": "text", "text": text} for text in texts
    ]

    if messages and messages[-1].get("role") == "user":
        content = messages[-1].get("content")

        if isinstance(content, list):
            content.extend(blocks)
        else:
            messages[-1]["content"] = [
                {"type": "text", "text": str(content)},
                *blocks,
            ]
    else:
        messages.append({"role": "user", "content": blocks})

_runtime_start_lock = threading.Lock()
_runtime_started = False
_runtime_threads: list[threading.Thread] = []

def queue_processor_loop(stop_event = None):
    stop_event = stop_event or threading.Event()
    while not stop_event.wait(0.2):
        if not has_cron_queue():
            continue

        if not agent_lock.acquire(blocking=False):
            continue

        try:
            if not has_cron_queue():
                continue

            print(
                  "\n  \033[35m[queue processor] "
                  "delivering scheduled work\033[0m"
              )
            run_agent_turn_locked()
        finally:
            agent_lock.release()

def start_runtime_threads(stop_event=None):
    global _runtime_started

    stop_event = stop_event or threading.Event()
    with _runtime_start_lock:
        if _runtime_started:
            return list(_runtime_threads)

        scheduler = threading.Thread(target=cron_scheduler_loop, args=(stop_event,), daemon=True, name = "cron-scheduler",)
        processor = threading.Thread(target=queue_processor_loop, args=(stop_event,), daemon=True, name = "cron-queue-processor",)

        _runtime_threads.extend([scheduler, processor])
        _runtime_started = True

        scheduler.start()
        processor.start()
    return list(_runtime_threads)

def main():
    global session_context

    print("开拓者终于等到你了！欢迎使用Pamu帕！你可以输入 'q'，'exit'或 '空格符' 退出帕！。")
    
    session_history.clear()
    context = update_context({}, session_history)

    load_durable_jobs()
    stop_event = threading.Event()
    runtime_threads = start_runtime_threads(stop_event)

    try:
        while True:
                try:
                    query = input("\033[36m>> \033[0m")
                except (EOFError, KeyboardInterrupt):
                    break
                if query.strip().lower() in ("q", "exit", ""):
                    break
                trigger_hook("UserPromptSubmit", query)
        
                with agent_lock:
                    run_agent_turn_locked(query)
    finally:
        stop_event.set()
        for thread in runtime_threads:
            thread.join(timeout=1.0)

if __name__ == "__main__":
    main()
