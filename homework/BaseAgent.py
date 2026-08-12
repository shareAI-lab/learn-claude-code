import os,json,subprocess,time,re,copy,random,threading,uuid,hashlib
from pathlib import Path
from dataclasses import dataclass,asdict,field,replace
from types import SimpleNamespace
from datetime import datetime

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv
from homework.agent_app.config import AppConfig
from homework.agent_app.runtime import SessionState
from homework.agent_app.tools import builtin as builtin_tools
from homework.agent_app.tools import executor as tool_executor
from homework.agent_app.tools.registry import ToolRegistry
from homework.agent_app.features import mcp as mcp_feature
from homework.agent_app.tools.hooks import (
    HookRegistry,
    make_context_inject_hook,
    make_diff_preview_hook,
    make_large_output_hook,
    make_log_hook,
    make_permission_hook,
    make_summary_hook,
)
from homework.agent_app.core.compaction import (
    estimate_size as compaction_estimate_size,
    micro_compact as compaction_micro_compact,
    persist_large_output as compaction_persist_large_output,
    reactive_compact as compaction_reactive_compact,
    snip_compact as compaction_snip_compact,
    tool_result_budget as compaction_tool_result_budget,
    compact_history as compaction_compact_history,
)
from homework.agent_app.features.scheduler import (
    SchedulerState,
    cancel_job as scheduler_cancel_job,
    consume_cron_queue as scheduler_consume_cron_queue,
    cron_scheduler_loop as scheduler_cron_scheduler_loop,
    has_cron_queue as scheduler_has_cron_queue,
    list_jobs as scheduler_list_jobs,
    load_durable_jobs as scheduler_load_durable_jobs,
    schedule_job as scheduler_schedule_job,
)
from homework.agent_app.features import scheduler as scheduler_feature
from homework.agent_app.features import memory as memory_feature
from homework.agent_app.features import background as background_feature
from homework.agent_app.features.teams import bus as team_bus
from homework.agent_app.features.teams import protocol as team_protocol
from homework.agent_app.features.teams import teammates as teammate_runtime
from homework.agent_app.features import subagents as subagent_runtime
from homework.agent_app.features import skills as skills_feature
from homework.agent_app.features import todos as todos_feature
from homework.agent_app.features import tasks as tasks_feature
from homework.agent_app.features import worktrees as worktrees_feature
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
APP_CONFIG = AppConfig.from_env(REPO_ROOT)
TOOL_RESULT_DIR = APP_CONFIG.tool_result_dir
TOOL_RESULTS_DIR = TOOL_RESULT_DIR
PERSIST_THRESHOLD = APP_CONFIG.persist_threshold

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
SESSION_STATE = SessionState()
SKILL_STATE = skills_feature.SkillState(root=APP_CONFIG.skills_dir)
MEMORY_STORE = memory_feature.MemoryStore(
    root=APP_CONFIG.memory_dir,
    index_path=APP_CONFIG.memory_index,
)
TASK_STORE = tasks_feature.TaskStore(root=APP_CONFIG.task_dir)
TASK_DIR = TASK_STORE.root
TASK_LOCK = TASK_STORE.lock
Task = tasks_feature.Task
CURRENT_TODOS = SESSION_STATE.todos
SKILL_REGISTRY = SKILL_STATE.registry

def resolve_tool_cwd(cwd: str | Path | None = None) -> Path:
    return builtin_tools.resolve_tool_cwd(APP_CONFIG.workdir, cwd)


def safe_path(path: str, cwd: str | Path | None = None) -> Path:
    return builtin_tools.safe_path(APP_CONFIG.workdir, path, cwd)

#==================== CRON SCHEDULER ====================
SCHEDULER_STATE = SchedulerState()
agent_lock = threading.Lock()

def schedule_job(cron, prompt, recurring=True, durable=True):
    return scheduler_schedule_job(
        SCHEDULER_STATE, APP_CONFIG, cron, prompt, recurring, durable
    )

def cancel_job(job_id):
    return scheduler_cancel_job(SCHEDULER_STATE, APP_CONFIG, job_id)

def cron_scheduler_loop(stop_event=None):
    return scheduler_cron_scheduler_loop(
        SCHEDULER_STATE, APP_CONFIG, stop_event or threading.Event()
    )

def consume_cron_queue():
    return scheduler_consume_cron_queue(SCHEDULER_STATE)

def has_cron_queue():
    return scheduler_has_cron_queue(SCHEDULER_STATE)

def load_durable_jobs():
    return scheduler_load_durable_jobs(SCHEDULER_STATE, APP_CONFIG)

#==================== AGENT TEAMS ====================
MAILBOX_DIR = APP_CONFIG.mailbox_dir
TEAM_STATE = teammate_runtime.TeamState()
team_lock = TEAM_STATE.lock
active_teammates = TEAM_STATE.active

def MessageBus(root: Path | None = None) -> team_bus.MessageBus:
    return team_bus.MessageBus(root=root or MAILBOX_DIR)


ProtocolState = team_protocol.ProtocolState
BUS = MessageBus(root=MAILBOX_DIR)
PROTOCOL_STORE = team_protocol.ProtocolStore()

def new_request_id() -> str:
    return team_protocol.new_request_id()

def match_response(response_type: str, request_id: str, approve: bool) -> bool:
    return team_protocol.match_response(
        PROTOCOL_STORE, response_type, request_id, approve
    )

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
    return teammate_runtime.idle_poll(
        BUS, agent_name, messages, name, worktree_context,
        scan_unclaimed=scan_unclaimed_tasks,
        claim_task=claim_task,
        worktree_path=lambda worktree: WORKTREES_DIR / worktree,
        sleep=time.sleep,
        poll_interval=IDLE_POLL_INTERVAL,
        timeout=IDLE_TIMEOUT,
    )

def validate_agent_name(name: str, *, allow_lead: bool = True) -> str:
    return team_bus.validate_agent_name(name, allow_lead=allow_lead)

def mailbox_path(agent: str) -> Path:
    return BUS.mailbox_path(agent)

TEAM_GUARDED_TOOLS = {"bash", "write_file"}
PERMISSION_POLL_INTERVAL = 0.5
PERMISSION_TIMEOUT = 300

def wait_for_permission_response(agent: str, request_id: str, deferred_inbox: list[dict]) -> dict:
    return team_protocol.wait_for_permission_response(
        BUS, agent, request_id, deferred_inbox,
        clock=time.time, sleep=time.sleep,
        poll_interval=PERMISSION_POLL_INTERVAL,
        timeout=PERMISSION_TIMEOUT,
    )

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
    return str(output), False
    

def spawn_teammate_thread(name: str, role: str, prompt: str) -> str:
    state = RecoveryState(
        current_model=PRIMARY_MODEL,
        fallback_model=FALLBACK_MODEL,
    )

    def llm(**kwargs):
        return with_retry(
            lambda: client.messages.create(model=state.current_model, **kwargs),
            state,
            max_transient_retries=MAX_TRANSIENT_RETRIES,
            max_consecutive_529=MAX_CONSECUTIVE_529,
            base_delay_ms=BASE_DELAY_MS,
        )

    handlers = {
        "bash": run_bash,
        "read_file": run_read,
        "write_file": run_write,
        "send_message": lambda to, content: (BUS.send(name, to, content), "Sent")[1],
        "submit_plan": lambda plan: _teammate_submit_plan(name, plan),
        "list_tasks": run_list_tasks,
        "claim_task": run_claim_task,
        "complete_task": run_complete_task,
    }
    return teammate_runtime.spawn_teammate_thread(
        TEAM_STATE, BUS, llm,
        name=name, role=role, prompt=prompt, workdir=WORKDIR,
        handlers=handlers, hooks=HOOK_REGISTRY,
        validate_name=validate_agent_name,
        guarded_tools=TEAM_GUARDED_TOOLS,
        guarded_tool=run_teammate_guarded_tool,
        idle=idle_poll,
        max_tokens=DEFAULT_MAX_TOKENS,
        thread_factory=threading.Thread,
    )


def _teammate_submit_plan(from_name: str, plan: str) -> str:
    return team_protocol.submit_plan(BUS, PROTOCOL_STORE, from_name, plan)
    
def process_permission_request(msg: dict) -> None:
    return team_protocol.process_permission_request(
        BUS, PROTOCOL_STORE, msg,
        hook=trigger_hook, cwd_resolver=resolve_tool_cwd,
        guarded_tools=TEAM_GUARDED_TOOLS,
        clock=time.time, sleep=time.sleep,
    )

def collect_lead_inbox() -> str:
    return team_protocol.collect_lead_inbox(
        BUS, PROTOCOL_STORE,
        hook=trigger_hook, cwd_resolver=resolve_tool_cwd,
        guarded_tools=TEAM_GUARDED_TOOLS,
        clock=time.time, sleep=time.sleep,
    )

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
    return team_protocol.request_shutdown(BUS, PROTOCOL_STORE, teammate)

def run_request_plan(teammate: str, task: str) -> str:
    BUS.send("lead", teammate, f"Please submit a plan for: {task}", "message")
    return f"Asked {teammate} to submit a plan"

def run_review_plan(request_id: str, approve: bool, feedback: str = "") -> str:
    return team_protocol.review_plan(
        BUS, PROTOCOL_STORE, request_id, approve, feedback
    )

#==================== BACKGROUND TASKS ===============
BACKGROUND_STATE = background_feature.BackgroundState()

def is_slow_operation(tool_name: str, tool_input: dict) -> bool:
    return tool_executor.is_slow_operation(tool_name, tool_input)

def should_run_background(tool_name: str, tool_input: dict) -> bool:
    return tool_executor.should_run_background(tool_name, tool_input)

def execute_tool(block, handlers: dict) -> str:
    return tool_executor.execute_tool(block, handlers)

def start_background_task(block,handlers: dict) -> str:
    return background_feature.start_background_task(
        BACKGROUND_STATE,
        block,
        handlers,
        post_tool=lambda used_block, output: trigger_hook(
            "PostToolUse", used_block, output
        ),
        persist_output=persist_large_output,
    )

def collect_background_results() -> list[str]:
    return background_feature.collect_background_results(BACKGROUND_STATE)


#==================== TASK SYSTEM ====================
def _task_path(task_id):
    return tasks_feature.task_path(TASK_STORE, task_id)

def create_task(subject, description="", blockedBy=None):
    return tasks_feature.create_task(TASK_STORE, subject, description, blockedBy)

def save_task(task):
    return tasks_feature.save_task(TASK_STORE, task)

def load_task(task_id):
    return tasks_feature.load_task(TASK_STORE, task_id)

def list_tasks():
    return tasks_feature.list_tasks(TASK_STORE)

def get_task(task_id):
    return tasks_feature.get_task(TASK_STORE, task_id)

def can_start(task_id):
    return tasks_feature.can_start(TASK_STORE, task_id)

def claim_task(task_id, owner="agent"):
    return tasks_feature.claim_task(TASK_STORE, task_id, owner)

def complete_task(task_id):
    return tasks_feature.complete_task(TASK_STORE, task_id)

#==================== MCP PLUGIN =========================
MCP_STATE = mcp_feature.MCPState()
mcp_clients = MCP_STATE.clients
mcp_lock = MCP_STATE.lock
MCP_TOOL_METADATA = MCP_STATE.metadata

def connect_mcp(name: str) -> str:
    return mcp_feature.connect_mcp(MCP_STATE, name, TOOL_REGISTRY.snapshot)

def assemble_tool_pool() -> tuple[list[dict], dict]:
    return mcp_feature.snapshot_mcp_tools(MCP_STATE, *TOOL_REGISTRY.snapshot())

#==================== WORKTREE SYSTEM ====================
def run_git(args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=WORKDIR, capture_output=True, text=True, timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output[:5000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return False, "Error: git timedout"

WORKTREE_STATE = worktrees_feature.WorktreeState(
    workdir=WORKDIR,
    root=APP_CONFIG.worktrees_dir,
    run_git=run_git,
)
WORKTREES_DIR = WORKTREE_STATE.root

def create_worktree(name, task_id=""):
    return worktrees_feature.create_worktree(
        WORKTREE_STATE, name, task_id, TASK_STORE
    )

def bind_task_to_worktree(task_id, worktree_name):
    return worktrees_feature.bind_task_to_worktree(TASK_STORE, task_id, worktree_name)

def remove_worktree(name, discard_changes=False):
    return worktrees_feature.remove_worktree(WORKTREE_STATE, name, discard_changes)

def keep_worktree(name):
    return worktrees_feature.keep_worktree(WORKTREE_STATE, name)

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
def memory_summarize(prompt, max_tokens):
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return extract_text(response.content)

#==================== TODO, SKILL, AND MEMORY WIRING ====================
def format_current_todos() -> str:
    global CURRENT_TODOS
    if CURRENT_TODOS is not SESSION_STATE.todos:
        SESSION_STATE.todos = CURRENT_TODOS
    return todos_feature.format_current_todos(SESSION_STATE)

def list_skills() -> str:
    return skills_feature.list_skills(SKILL_STATE)

def load_memories(messages):
    return memory_feature.load_memories(MEMORY_STORE, messages, memory_summarize)

def extract_memories(messages):
    return memory_feature.extract_memories(MEMORY_STORE, messages, memory_summarize)

def consolidate_memories():
    return memory_feature.consolidate_memories(MEMORY_STORE, memory_summarize)

def build_request_messages_with_memories(messages):
    return memory_feature.build_request_messages_with_memories(
        MEMORY_STORE, messages, memory_summarize
    )

skills_feature.scan_skills(SKILL_STATE)


#==================== TOOL SYSTEM ====================
def run_bash(command: str, run_in_background: bool = False, cwd=None) -> str:
    return builtin_tools.run_bash(
        APP_CONFIG.workdir, command, run_in_background=run_in_background, cwd=cwd
    )


def run_read(path: str, offset: int = 0, limit: int | None = None, cwd=None) -> str:
    return builtin_tools.run_read(APP_CONFIG.workdir, path, offset, limit, cwd)


def run_write(path: str, content: str, cwd=None) -> str:
    return builtin_tools.run_write(APP_CONFIG.workdir, path, content, cwd)


def run_edit(path: str, old_text: str, new_text: str, cwd=None) -> str:
    return builtin_tools.run_edit(APP_CONFIG.workdir, path, old_text, new_text, cwd)


def run_glob(pattern: str, cwd=None) -> str:
    return builtin_tools.run_glob(APP_CONFIG.workdir, pattern, cwd)
    
def run_todo_write(todos:list) -> str:
    global CURRENT_TODOS
    if CURRENT_TODOS is not SESSION_STATE.todos:
        SESSION_STATE.todos = CURRENT_TODOS
    result = todos_feature.run_todo_write(SESSION_STATE, todos)
    CURRENT_TODOS = SESSION_STATE.todos
    return result

def load_skill(name:str) -> str:
    return skills_feature.load_skill(SKILL_STATE, name)

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
    jobs = scheduler_list_jobs(SCHEDULER_STATE)
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

def spawn_subagent(description: str) -> str:
    state = RecoveryState(current_model=PRIMARY_MODEL, fallback_model=FALLBACK_MODEL)

    def llm(**kwargs):
        return with_retry(
            lambda: client.messages.create(**kwargs), state,
            max_transient_retries=MAX_TRANSIENT_RETRIES,
            max_consecutive_529=MAX_CONSECUTIVE_529,
            base_delay_ms=BASE_DELAY_MS,
        )

    return subagent_runtime.spawn_subagent(
        description, llm, APP_CONFIG, SUB_SYSTEM, SUB_TOOLS, SUB_HANDLERS, HOOK_REGISTRY
    )

TOOL_REGISTRY = ToolRegistry()

# Temporary composition root: owners provide schemas; this file supplies dependencies.
_BUILTIN_DEPENDENCIES = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    "load_skill": load_skill,
}
_TEAM_DEPENDENCIES = {
    "spawn_teammate": run_spawn_teammate,
    "send_message": run_send_message,
    "check_inbox": run_check_inbox,
    "request_shutdown": run_request_shutdown,
    "request_plan": run_request_plan,
    "review_plan": run_review_plan,
}

builtin_tools.register_builtin_tools(TOOL_REGISTRY, _BUILTIN_DEPENDENCIES)
todos_feature.register_todo_tools(
    TOOL_REGISTRY, {"state": SESSION_STATE, "todo_write": run_todo_write}
)
tasks_feature.register_task_tools(TOOL_REGISTRY, lambda: TASK_STORE)
scheduler_feature.register_scheduler_tools(
    TOOL_REGISTRY, lambda: SCHEDULER_STATE, APP_CONFIG
)
teammate_runtime.register_team_tools(TOOL_REGISTRY, _TEAM_DEPENDENCIES)
worktrees_feature.register_worktree_tools(
    TOOL_REGISTRY, lambda: WORKTREE_STATE, lambda: TASK_STORE
)
subagent_runtime.register_subagent_tool(
    TOOL_REGISTRY, {"task": spawn_subagent}
)
mcp_feature.register_mcp_connection_tool(TOOL_REGISTRY, lambda: MCP_STATE)

# Compatibility snapshots for existing callers; each loop uses TOOL_REGISTRY.
BUILTIN_TOOLS, BUILTIN_HANDLERS = TOOL_REGISTRY.snapshot()

#==================== COMPACTION PIPELINE ====================
CONTEXT_LIMIT = APP_CONFIG.context_limit

def estimate_size(messages):
    return compaction_estimate_size(messages)

def snip_compact(messages, max_messages=500):
    return compaction_snip_compact(messages, max_messages=max_messages)

def micro_compact(messages):
    return compaction_micro_compact(APP_CONFIG, messages)

def persist_large_output(tool_use_id, output):
    config = replace(
        APP_CONFIG,
        persist_threshold=PERSIST_THRESHOLD,
        tool_result_dir=TOOL_RESULT_DIR,
    )
    return compaction_persist_large_output(config, tool_use_id, output)

def tool_result_budget(messages, max_bytes=20_000):
    return compaction_tool_result_budget(APP_CONFIG, messages, max_bytes=max_bytes)

def summarize(messages):
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
    return compaction_compact_history(APP_CONFIG, summarize, messages)

def reactive_compact(messages):
    return compaction_reactive_compact(APP_CONFIG, summarize, messages)

#==================== HOOK SYSTEM ====================
HOOK_REGISTRY = HookRegistry()

def register_hook(event:str,callback):
    HOOK_REGISTRY.register(event, callback)

def trigger_hook(event:str,*args):
    return HOOK_REGISTRY.trigger(event, *args)


register_hook("UserPromptSubmit", make_context_inject_hook(APP_CONFIG.workdir))
register_hook(
    "PreToolUse",
    make_permission_hook(
        APP_CONFIG.workdir, input, MCP_TOOL_METADATA, mcp_lock
    ),
)
register_hook("PreToolUse", make_log_hook(APP_CONFIG.workdir))
register_hook("PreToolUse", make_diff_preview_hook(APP_CONFIG.workdir, input))
register_hook("PostToolUse", make_large_output_hook(APP_CONFIG.workdir))
register_hook("Stop", make_summary_hook(APP_CONFIG.workdir))

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
    memories = memory_feature.read_memory_index(MEMORY_STORE)
    skills = list_skills() if SKILL_STATE.registry else ""

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
