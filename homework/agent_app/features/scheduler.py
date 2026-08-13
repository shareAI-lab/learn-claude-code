import json
import random
import threading
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime

from ..config import AppConfig


SCHEDULER_TOOL_SCHEMAS = [
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
]


def register_scheduler_tools(registry, scheduler_state, config) -> None:
    """Register cron tools using the supplied scheduler handlers."""
    if isinstance(scheduler_state, Mapping):
        handlers = scheduler_state
    else:
        def current_state():
            return scheduler_state() if callable(scheduler_state) else scheduler_state

        def run_schedule(cron, prompt, recurring=True, durable=True):
            result = schedule_job(
                current_state(), config, cron, prompt, recurring, durable
            )
            if isinstance(result, str):
                return f"Error: {result}"
            return f"Scheduled {result.id}: '{cron}' → '{prompt}'"

        def run_list():
            jobs = list_jobs(current_state())
            if not jobs:
                return "No cron jobs. Use schedule_cron to add one."
            lines = []
            for job in jobs:
                tag = "recurring" if job.recurring else "one-shot"
                durability = "durable" if job.durable else "session"
                lines.append(
                    f"  {job.id}: '{job.cron}' → {job.prompt[:40]} "
                    f"[{tag}, {durability}]"
                )
            return "\n".join(lines)

        handlers = {
            "schedule_cron": run_schedule,
            "list_crons": run_list,
            "cancel_cron": lambda job_id: cancel_job(
                current_state(), config, job_id
            ),
        }
    for schema in SCHEDULER_TOOL_SCHEMAS:
        registry.register(schema, handlers[schema["name"]])


@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool


@dataclass(slots=True)
class SchedulerState:
    jobs: dict[str, CronJob] = field(default_factory=dict)
    queue: list[CronJob] = field(default_factory=list)
    last_fired: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _cron_field_matches(field: str, value: int) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_matches(part.strip(), value) for part in field.split(","))
    if "-" in field:
        low, high = field.split("-", 1)
        return int(low) <= value <= int(high)
    return value == int(field)


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, day_of_month, month, day_of_week = fields
    day_of_week_value = (dt.weekday() + 1) % 7

    minute_matches = _cron_field_matches(minute, dt.minute)
    hour_matches = _cron_field_matches(hour, dt.hour)
    day_of_month_matches = _cron_field_matches(day_of_month, dt.day)
    month_matches = _cron_field_matches(month, dt.month)
    day_of_week_matches = _cron_field_matches(day_of_week, day_of_week_value)

    if not (minute_matches and hour_matches and month_matches):
        return False
    day_of_month_unconstrained = day_of_month == "*"
    day_of_week_unconstrained = day_of_week == "*"
    if day_of_month_unconstrained and day_of_week_unconstrained:
        return True
    if day_of_month_unconstrained:
        return day_of_week_matches
    if day_of_week_unconstrained:
        return day_of_month_matches
    return day_of_month_matches or day_of_week_matches


def _validate_cron_field(field: str, low: int, high: int) -> str | None:
    if field == "*":
        return None
    if field.startswith("*/"):
        step_string = field[2:]
        if not step_string.isdigit():
            return f"Invalid step: {field}"
        step = int(step_string)
        if step <= 0:
            return f"Step must be > 0: {field}"
        return None
    if "," in field:
        for part in field.split(","):
            error = _validate_cron_field(part.strip(), low, high)
            if error:
                return error
        return None
    if "-" in field:
        parts = field.split("-", 1)
        if not parts[0].isdigit() or not parts[1].isdigit():
            return f"Invalid range: {field}"
        start, end = int(parts[0]), int(parts[1])
        if start < low or start > high or end < low or end > high:
            return f"Range {field} out of bounds [{low}-{high}]"
        if start > end:
            return f"Range start > end: {field}"
        return None
    if not field.isdigit():
        return f"Invalid field: {field}"
    value = int(field)
    if value < low or value > high:
        return f"Value {value} out of bounds [{low}-{high}]"
    return None


def validate_cron(cron_expr: str) -> str | None:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return f"Expected 5 fields, got {len(fields)}"
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    names = ["minute", "hour", "day-of-month", "month", "day-of-week"]
    for field, (low, high), name in zip(fields, bounds, names):
        error = _validate_cron_field(field, low, high)
        if error:
            return f"{name}: {error}"
    return None


def save_durable_jobs(state: SchedulerState, config: AppConfig):
    with state.lock:
        durable = [asdict(job) for job in state.jobs.values() if job.durable]
        temp_path = config.scheduled_tasks_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(durable, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    temp_path.replace(config.scheduled_tasks_path)


def load_durable_jobs(state: SchedulerState, config: AppConfig):
    if not config.scheduled_tasks_path.exists():
        return
    try:
        jobs = json.loads(config.scheduled_tasks_path.read_text())
        with state.lock:
            for serialized in jobs:
                job = CronJob(**serialized)
                error = validate_cron(job.cron)
                if error:
                    print(f"  \033[31m[cron] skipping invalid job {job.id}: {error}\033[0m")
                    continue
                state.jobs[job.id] = job
            valid = [job for job in jobs if job["id"] in state.jobs]
        if valid:
            print(f"  \033[35m[cron] loaded {len(valid)} durable job(s)\033[0m")
    except Exception:
        pass


def schedule_job(
    state: SchedulerState,
    config: AppConfig,
    cron: str,
    prompt: str,
    recurring: bool = True,
    durable: bool = True,
) -> CronJob | str:
    error = validate_cron(cron)
    if error:
        return error
    job = CronJob(
        id=f"cron_{random.randint(0, 999999):06d}",
        cron=cron,
        prompt=prompt,
        recurring=recurring,
        durable=durable,
    )
    with state.lock:
        state.jobs[job.id] = job
    if durable:
        save_durable_jobs(state, config)
    print(f"  \033[35m[cron register] {job.id} '{cron}' → {prompt[:40]}\033[0m")
    return job


def cancel_job(state: SchedulerState, config: AppConfig, job_id: str) -> str:
    with state.lock:
        job = state.jobs.pop(job_id, None)
    if not job:
        return f"Job {job_id} not found"
    if job.durable:
        save_durable_jobs(state, config)
    print(f"  \033[31m[cron cancel] {job_id}\033[0m")
    return f"Cancelled {job_id}"


def list_jobs(state: SchedulerState) -> list[CronJob]:
    with state.lock:
        return list(state.jobs.values())


def cron_scheduler_loop(state: SchedulerState, config: AppConfig, stop_event, now=datetime.now):
    while not stop_event.wait(1):
        current_time = now()
        minute_marker = current_time.strftime("%Y-%m-%d %H:%M")
        durable_changed = False
        with state.lock:
            for job in list(state.jobs.values()):
                try:
                    if cron_matches(job.cron, current_time):
                        if state.last_fired.get(job.id) != minute_marker:
                            state.queue.append(job)
                            state.last_fired[job.id] = minute_marker
                            print(f"  \033[35m[cron fire] {job.id} → {job.prompt[:40]}\033[0m")
                        if not job.recurring:
                            state.jobs.pop(job.id, None)
                            state.last_fired.pop(job.id, None)
                            durable_changed = durable_changed or job.durable
                except Exception as error:
                    print(f"  \033[31m[cron error] {job.id}: {error}\033[0m")
        if durable_changed:
            save_durable_jobs(state, config)


def consume_cron_queue(state: SchedulerState) -> list[CronJob]:
    with state.lock:
        fired = list(state.queue)
        state.queue.clear()
    return fired


def has_cron_queue(state: SchedulerState) -> bool:
    with state.lock:
        return bool(state.queue)
