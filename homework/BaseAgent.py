import os,json,ast,subprocess,difflib,yaml,time,re,copy,random,threading,uuid
from pathlib import Path
from dataclasses import dataclass,asdict
from types import SimpleNamespace

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

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
LARGE_OUTPUT_DIR = WORKDIR / ".large_results"
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
CURRENT_TODOS:list[dict] = []

def safe_path(p:str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

#==================== AGENT TEAMS ====================
MAILBOX_DIR = WORKDIR / ".mailbox"; 
MAILBOX_DIR.mkdir(exist_ok=True)
AGENT_NAME_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_-]{0,31}$"
)

mailbox_lock = threading.RLock()
team_lock = threading.Lock()
active_teammates: dict[str,dict] = {}

class MessageBus:
    def send(self,from_agent: str, to_agent:str, content:object,
             msg_type:str = "message"):
        validate_agent_name(from_agent)
        validate_agent_name(to_agent)

        if msg_type not in {"message", "result", "permission_request", "permission_response"}:
            raise ValueError(f"Invalid message type: {msg_type}")

        msg = {"from": from_agent, "to": to_agent, 
               "content": content,  "type": msg_type, 
               "ts": time.time()}
        path = mailbox_path(to_agent)

        with mailbox_lock:
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
        },
        msg_type="permission_request"
    )

    response = wait_for_permission_response(agent, request_id, deferred_inbox)

    if not response.get("approved"):
        reason = response.get("reason", "Permission denied")
        return f"Permission denied: {reason}", True
    
    raw_handler = {
        "bash": run_bash,
        "write_file": run_write,
    }

    output = raw_handler[block.name](**block.input)
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
    
    system = (f"You are '{name}', role: {role}.\n"
              f"Workspace: {WORKDIR}\n"
              "Available tools: bash, read_file, write_file, send_message.\n"
              "You must send your final result to lead using send_message.\n"
              "Do not create subagents or additional teammates.\n"
              "bash and write_file require permission from Lead. "
              "When permission is approved, you will execute the tool yourself. "
              "Do not claim that a protected operation succeeded until its "
              "tool_result confirms success.")
    
    team_tools = [{"name": "bash", "description": "Run a shell command.",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "run_in_background": {"type": "boolean","description": "Run this command asynchronously"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "send_message", "description": "Send a message to another agent.", 
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}}]
    
    def run():
        messages = [{"role": "user", "content": prompt}]
        summary = "Stopped after 10 teammate rounds."
        deferred_inbox: list[dict] = []
        state = RecoveryState()

        sub_handlers = {
            "read_file": run_read,
            "send_message": lambda to, content: (BUS.send(name, to, content), "Sent")[1]
        }
        for _ in range(10):
            inbox = deferred_inbox + BUS.read_inbox(name)
            deferred_inbox.clear()
            if inbox:
                messages.append({"role": "user", 
                                 "content": f"<inbox>{json.dumps(inbox)}</inbox>"})
            try:
                response = with_retry(
                    lambda: client.messages.create(
                    model = MODEL, system = system,messages = messages[-20:],
                    tools = team_tools, max_tokens = DEFAULT_MAX_TOKENS
                    ),
                state
                )
            except Exception:
                break
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name in TEAM_GUARDED_TOOLS:
                    output, is_error = run_teammate_guarded_tool(name, block, deferred_inbox)
                else:
                    handler = sub_handlers.get(block.name)

                    if not handler:
                        output = f"Unknown tool: {block.name}"
                        is_error = True
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

            messages.append({"role": "user", "content": results})
            response_text = extract_text(response.content)
            if response_text:
                summary = response_text

        summary = "Done."
        for msg in reversed(messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                for b in msg["content"]:
                    if getattr(b, "type", None) == "text":
                        summary = b.text
                        break
                else:
                    continue
                break
        BUS.send(name, "lead", summary, "result")
        with team_lock:
            active_teammates.pop(name, None)
        print(f"  \033[32m[teammate] {name} finished\033[0m")

    active_teammates[name] = True
    threading.Thread(target=run, daemon=True).start()
    print(f"  \033[36m[teammate] {name} spawned as {role}\033[0m")
    return f"Teammate '{name}' spawned as {role}"
    
def process_permission_request(msg: dict) -> None:
    requester = msg.get("from")
    request = msg.get("content", {})

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
        if msg.get("type") == "permission_request":
            process_permission_request(msg)
        else:
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
    handlers = TOOL_HANDLERS if handlers is None else handlers
    handler = handlers.get(block.name)
    if handler:
        return handler(**block.input)
    return f"Unknown tool: {block.name}"

def start_background_task(block) -> str:
    global _bg_counter
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
            output = str(execute_tool(block))

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
        summary = output[:200] if len(output) > 200 else output
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{bg_id}</task_id>\n"
            f"  <status>{task['status']}</status>\n"
            f"  <command>{task['command']}</command>\n"
            f"  <summary>{summary}</summary>\n"
            f"</task_notification>"
        )
        print(f"  \033[32m[background done] {bg_id}: "
            f"{task['command'][:40]} ({len(output)} chars)\033[0m")
    return notifications


#==================== TASK SYSTEM ====================
TASK_DIR = WORKDIR / ".tasks"
TASK_DIR.mkdir(exist_ok=True)

@dataclass
class Task:
    id: str
    subject:str
    description:str
    status: str
    owner: str | None
    blockedBy:list[str]

def _task_path(task_id:str) -> Path:
    return TASK_DIR / f"{task_id}.json"

def create_task(subject:str, description: str = "",
                blockedBy:list[str] | None = None) -> Task:
    task = Task(
        id = f"task_{int(time.time())}_{random.randint(0,9999):04d}",
        subject = subject,
        description = description,
        status = "pending",
        owner = None,
        blockedBy = blockedBy or [],
    )
    save_task(task)
    return task

def save_task(task:Task):
    _task_path(task.id).write_text(json.dumps(asdict(task), indent=2, ensure_ascii=False), encoding="utf-8")

def load_task(task_id:str) -> Task:
    return Task(**json.loads(_task_path(task_id).read_text()))

def list_tasks() -> list[Task]:
    return [Task(**json.loads(p.read_text())) for p in sorted(TASK_DIR.glob("*.json"))]

def get_task(task_id:str) -> str:
    task = load_task(task_id)
    return json.dumps(asdict(task), indent=2)

def can_start(task_id:str) -> bool:
    task = load_task(task_id)
    for dep_id in task.blockedBy:
        if not _task_path(dep_id).exists():
            return False
        if load_task(dep_id).status != "completed":
            return False
    return True

def claim_task(task_id:str, owner:str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "pending":
        return f"Task {task_id} is {task.status}, cannot claim"
    if not can_start(task_id):
        deps = [d for d in task.blockedBy
                if not _task_path(d).exists() or load_task(d).status != "completed"]
        return f"Blocked by: {deps}"
    task.owner = owner
    task.status = "in_progress"
    save_task(task)
    print(f"  \033[36m[claim] {task.subject} → in_progress (owner: {owner})\033[0m")
    return f"Claimed {task.id} ({task.subject})"

def complete_task(task_id:str) -> str:
    task = load_task(task_id)
    if task.status != "in_progress":
        return f"Task {task_id} is {task.status}, cannot complete"
    task.status = "completed"
    save_task(task)
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy and can_start(t.id)]
    print(f"  \033[32m[complete] {task.subject} ✓\033[0m")
    msg = f"Completed {task.id} ({task.subject})"
    if unblocked:
        msg += f"\nUnblocked: {', '.join(unblocked)}"
        print(f"  \033[33m[unblocked] {', '.join(unblocked)}\033[0m")
    return msg

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

class RecoveryState:
    def __init__(self):
        self.has_escalated = False
        self.continuation_count = 0
        self.consecutive_529 = 0
        self.reactive_compact_count = 0
        self.current_model = PRIMARY_MODEL

class PartialStreamError(Exception):
    def __init__(self, partial_text: str, cause: Exception):
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.partial_text = partial_text
        self.cause = cause

def get_status_code(exc):
    status_code = getattr(exc, "status_code", None)
    if status_code:
        return status_code
    
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)

def is_rate_limit_error(exc):
    name = type(exc).__name__.lower()
    message = str(exc).lower()

    return (
        get_status_code(exc) == 429
        or "ratelimit" in message
        or "rate limit" in message
        or "429" in message
    )

def is_overloaded_error(exc):
    name = type(exc).__name__.lower()
    message = str(exc).lower()

    return (
        get_status_code(exc) == 529
        or "overloaded" in name
        or "overloaded" in message
        or "529" in message
    )

def is_prompt_too_long_error(exc):
    message = str(exc).lower()
    return (
        "prompt_is_too_long" in message
        or "context_length_exceeded" in message
        or "max_context_window" in message
        or ("prompt" in message and "too long" in message)
    )

def extract_retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)

    if not headers:
        headers = getattr(exc, "headers", None)

    if not headers:
        return None
    
    value = headers.get("retry-after")

    try:
        delay = float(value)
    except (TypeError, ValueError):
        return None
    
    return delay if delay > 0 else None

def retry_delay(attempt:int, retry_after=None):
    if retry_after:
        return retry_after
    
    base = min(BASE_DELAY_MS * (2 ** attempt), 32000) / 1000
    jitter = random.uniform(0,base * 0.25)
    return base + jitter

def with_retry(fn, state:RecoveryState):
    for attempt in range(MAX_TRANSIENT_RETRIES):
        try:
            response = fn()
            state.consecutive_529 = 0
            return response
        except PartialStreamError:
            raise
        except Exception as e:
            is_429 = is_rate_limit_error(e)
            is_529 = is_overloaded_error(e)

            if not is_429 and not is_529:
                raise

            if is_429:
                state.consecutive_529 = 0

            if is_529:
                state.consecutive_529 += 1
                if state.consecutive_529 >= MAX_CONSECUTIVE_529:
                    if FALLBACK_MODEL and state.current_model != FALLBACK_MODEL:
                        state.current_model = FALLBACK_MODEL
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                                f" switching to {FALLBACK_MODEL}\033[0m")
                    else:
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                                    f" no FALLBACK_MODEL_ID configured, continuing retry\033[0m")

            if attempt == MAX_TRANSIENT_RETRIES - 1:
                raise

            delay = retry_delay(attempt, extract_retry_after(e))
            print(f"  \033[33m[529 overloaded] retry {attempt+1}/{MAX_TRANSIENT_RETRIES},"
                      f" wait {delay:.1f}s\033[0m")
            
            time.sleep(delay)

    raise RuntimeError("unreachable")
    
def append_unrecoverable_error(messages, exc):
    name = type(exc).__name__
    text = f"[Error] {type(exc).__name__}: {str(exc)[:300]}"

    messages.append({
        "role": "assistant",
        "content": [{
            "type": "text",
            "text": text,
        }],
    })

    print(f"  \033[31m[unrecoverable] {name}: {str(exc)[:100]}\033[0m")

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

def build_memory_system() -> str:
    index = read_memory_index()
    memories_section = f"\n\nMemories available:\n{index}" if index else ""
    return (
        f"You are a coding agent at {WORKDIR}."
        f"{memories_section}\n"
        "Relevant memories are injected below. Respect user preferences from memory.\n"
        "When the user says 'remember' or expresses a clear preference, extract it as a memory."
    )


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
def run_bash(command:str, run_in_background: bool = False) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd = WORKDIR,
                           capture_output=True, text=True, timeout = 120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    
def run_read(path:str,offset:int = 0,limit:int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        
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
    
def run_write(path:str,content:str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_edit(path:str,old_text:str,new_text:str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text,new_text,1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_glob(pattern:str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern,root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
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
    except FileNotFoundError:
        return f"Error: Task {task_id} not found"
    
def run_claim_task(task_id: str) -> str:
    return claim_task(task_id, owner = "agent")

def run_complete_task(task_id: str) -> str:
    return complete_task(task_id)

TOOLS = [
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
]

TOOL_HANDLERS = {
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
}

#==================== SUBAGENT SYSTEM ====================
SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Complete the task you were given, then return a concise summary. "
    "Do not delegate further."
)

SUB_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "run_in_background": {"type": "boolean", "description": "Run this command asynchronously"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
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

def spawn_subagent(description:str) -> str:
    print(f"\n\033[35m[Subagent spawned]\033[0m")
    messages = [{"role": "user", "content": description}]  # fresh context

    state = RecoveryState()

    for _ in range(30):
        try:
            response = with_retry(lambda: client.messages.create(
                model = state.current_model,
                system = SUB_SYSTEM,
                messages = messages,
                tools = SUB_TOOLS,
                max_tokens = DEFAULT_MAX_TOKENS,
            ), state)
        except Exception as exc:
            error = f"[Subagent error] {type(exc).__name__}: {str(exc)[:300]}"
            print(f"  \033[31m{error}\033[0m")
            return error
        
        messages.append({"role":"assistant","content":response.content})
        if response.stop_reason != "tool_use":
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

TOOLS.append({
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
TOOL_HANDLERS["task"] = spawn_subagent

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
    LARGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = LARGE_OUTPUT_DIR / f"{tool_use_id}.txt"
    if not path.exists(): path.write_text(output)
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
        file_path = safe_path(path)
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
    "tools": f"Available tools: {','.join([t['name'] for t in TOOLS])}.",
    "skills": "Skills available:" + list_skills(),
}

def assemble_system_prompt(context:dict) -> str:
    sections = []
    sections.append(PROMPT_SECTIONS["identity"])
    sections.append(PROMPT_SECTIONS["tools"])
    sections.append(PROMPT_SECTIONS["workspace"])

    memories = context.get("memories","")
    if memories:
        sections.append(f"Memory index:\n{memories}")

    skills = context.get("skills")
    if skills:
        sections.append(PROMPT_SECTIONS["skills"])

    todos = context.get("todos", "")
    if todos:
        sections.append(f"Current tasks:\n{todos}")

    active_names = context.get("active_teammates", [])
    if active_names:
        sections.append(f"Active teammates:\n{', '.join(active_names)}")

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

def update_context(context:dict,messages:list) -> dict:
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    skills = ""
    if SKILL_REGISTRY:
        skills = str(','.join([s['name'] for s in SKILL_REGISTRY.values()]))

    todos = format_current_todos()

    with team_lock:
        active_names = sorted(active_teammates)

    return {
        "enabled_tools": TOOL_HANDLERS.keys(),
        "workspace": str(WORKDIR),
        "memories": memories,
        "skills": skills,
        "todos": todos,
        "active_teammates": active_names,
    }

#==================== AGENT LOOP ====================
rounds_since_todo = 0
MAX_REACTIVE_RETRIES = 1

def agent_loop(messages:list, context:dict):
    global rounds_since_todo
    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS

    while True:
        pending_texts = collect_background_results()
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
        
        context = update_context(context, messages)
        system = get_system_prompt(context)

        request_messages = build_request_messages_with_memories(messages)

        try:
            def call_llm():
                return create_message_streaming(
                    system=system,
                    request_messages=request_messages,
                    model=state.current_model,
                    max_tokens=max_tokens,
                )

            response = with_retry(call_llm, state)
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
        if response.stop_reason != "tool_use":
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

        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")

            blocked = trigger_hook("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                continue

            if should_run_background(block.name, block.input):
                bg_id = start_background_task(block)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"[Background task {bg_id} started] "
                                           f"Command: {block.input.get('command', '')}. "
                                           f"Result will be available when complete."})
                continue
                
            output = execute_tool(block)
            trigger_hook("PostToolUse", block, output)

            if block.name == "todo_write":
                rounds_since_todo = 0
            
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        user_content = list(results)
        bg_notifications = collect_background_results()
        if bg_notifications:
            user_content.extend([{"type": "text", "text": notif} for notif in bg_notifications])
        print(f"  \033[32m[inject] {len(bg_notifications)} background "
                  f"notification(s)\033[0m")
        messages.append({"role":"user","content":user_content})

def run_agent_turn(history:list, content:str, context:dict):
    history.append({"role":"user","content":content})
    context = agent_loop(history, context)
    print()
    return context

def create_message_streaming(system, request_messages, *, model, max_tokens):
    chunks = []
    try:
        with client.messages.stream(
            model=model,
            system=system,
            messages=request_messages,
            tools=TOOLS,
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
      
def print_response_text(response):
    text = extract_text(response.content)
    if text:
        print(text)

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


def main():
    print("开拓者终于等到你了！欢迎使用Pamu帕！你可以输入 'q'，'exit'或 '空格符' 退出帕！。")
    
    history = []
    context = update_context({}, [])

    while True:
        try:
            query = input("\033[36m>> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hook("UserPromptSubmit", query)
        context = run_agent_turn(history, query, context)

if __name__ == "__main__":
    main()
