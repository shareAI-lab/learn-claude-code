#!/usr/bin/env python3
"""
s16: Workflow Runtime — teaching model of Dynamic Agentic Workflows.

Idea: move orchestration from intelligence to structure. Subagents judge;
the script owns topology (loops, fan-out, merge). Intermediate results live
in variables + a journal, not in the host conversation.

Claude Code accepts script / scriptPath / name / args / resumeFromRunId.
Dynamic = model writes a JS harness for this task; Saved = rerun by name.
This lesson is a small Python runtime with the same ideas, line-readable.
Demo registers one saved workflow; we do not embed a JS interpreter.

Fidelity notes baked into this file:
  - parallel/pipeline failures isolate to null slots (fleet continues)
  - resume = longest unchanged agent() call-order prefix
  - real JS runtimes ban Date.now/Math.random so journals stay aligned

Run:
  python s16_workflow_runtime/code.py
  python s16_workflow_runtime/code.py demo
  python s16_workflow_runtime/code.py resume

    +-------------+       +--------------------------------+
    | Agent loop  | ----> | Workflow(name, args, run_id)  |
    +-------------+       +---------------+----------------+
                                          |
                           +--------------+--------------+
                           | agent | parallel | pipeline  |
                           +--------------+--------------+
                                          |
                                   journal + result
"""

import asyncio
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import secrets
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# -- Runtime Guards --
AGENT_CAP = 1000                       # hard cap on agent() calls per run
CONCURRENCY = 8                        # parallelism cap (semaphore)
STORE = Path(__file__).parent / ".runtime"   # snapshots + journals live here
MISS = object()                        # journal cache miss sentinel
WORKFLOW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
RUN_ID_RE = re.compile(r"^wf_[A-Za-z0-9][A-Za-z0-9._-]{0,63}_[0-9a-f]{16}$")


def _stable_hash(s: str) -> int:
    """Process-stable hash (Python's hash() is salted per process, which would
    break resume keys across `run` and `resume`)."""
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def create_run_id(meta) -> str:
    return f"wf_{meta['name']}_{secrets.token_hex(8)}"


def reserve_run_id(meta) -> str:
    """Reserve a fresh run identity before any journal can be truncated."""
    STORE.mkdir(parents=True, exist_ok=True)
    for _ in range(32):
        run_id = validate_run_id(create_run_id(meta))
        snapshot_path = STORE / f"{run_id}.json"
        try:
            fd = os.open(snapshot_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        os.close(fd)
        return run_id
    raise WorkflowInputError("could not allocate a unique workflow runId")


def create_task_id(run_id) -> str:
    return f"local_workflow_{run_id}"


def validate_run_id(run_id):
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise WorkflowInputError("invalid workflow runId")
    return run_id


# -- Errors --
class WorkflowInputError(Exception):
    """Bad workflow, metadata, or schema input."""


_run_locks_guard = threading.Lock()
_run_locks: dict[str, threading.Lock] = {}


@contextmanager
def workflow_run_lock(run_id: str):
    """Hold one run across threads and host processes for its full lifecycle."""
    with _run_locks_guard:
        local_lock = _run_locks.setdefault(run_id, threading.Lock())
    if not local_lock.acquire(blocking=False):
        raise WorkflowInputError(f"workflow run {run_id} is already active")

    handle = None
    try:
        STORE.mkdir(parents=True, exist_ok=True)
        handle = (STORE / f"{run_id}.lock").open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowInputError(
                f"workflow run {run_id} is already active"
            ) from exc
        yield
    finally:
        if handle is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        local_lock.release()
        with _run_locks_guard:
            if not local_lock.locked() and _run_locks.get(run_id) is local_lock:
                _run_locks.pop(run_id, None)


# -- Metadata Validation --
def validate_meta(meta):
    """Validate name, description, and optional phases before launch."""
    if not isinstance(meta, dict):
        raise WorkflowInputError("meta must be an object literal")
    if not meta.get("name") or not meta.get("description"):
        raise WorkflowInputError("meta requires `name` and `description`")
    if not isinstance(meta["name"], str) or not WORKFLOW_NAME_RE.fullmatch(meta["name"]):
        raise WorkflowInputError(
            "meta.name must be a 1-64 character slug using letters, numbers, '.', '_', or '-'"
        )
    if not isinstance(meta["description"], str):
        raise WorkflowInputError("meta.description must be a string")
    if "phases" in meta:
        if not isinstance(meta["phases"], list) or not all(
            isinstance(phase, str) and phase for phase in meta["phases"]
        ):
            raise WorkflowInputError("meta.phases must be a list of non-empty strings")
    return meta


def check_permission(meta, settings=None):
    """Apply the s03 allow/deny gate before launching a workflow."""
    settings = settings or {}
    if meta["name"] in settings.get("deny", []):
        raise WorkflowInputError(f"workflow '{meta['name']}' denied by settings")
    return "allow"


# -- Minimal JSON Schema --
class SimpleJsonSchema:
    """Tiny validator backing agent({schema}):
    object/array/string/boolean/number + required keys."""

    def __init__(self, schema):
        self.schema = schema

    def validate(self, value, schema=None):
        schema = self.schema if schema is None else schema
        if "enum" in schema and value not in schema["enum"]:
            return False, f"expected one of {schema['enum']}"
        t = schema.get("type")
        if t == "object":
            if not isinstance(value, dict):
                return False, "expected object"
            for key in schema.get("required", []):
                if key not in value:
                    return False, f"missing required key '{key}'"
            for key, sub in schema.get("properties", {}).items():
                if key in value:
                    ok, err = self.validate(value[key], sub)
                    if not ok:
                        return False, f"{key}: {err}"
            return True, None
        if t == "array":
            if not isinstance(value, list):
                return False, "expected array"
            items = schema.get("items")
            if items:
                for i, el in enumerate(value):
                    ok, err = self.validate(el, items)
                    if not ok:
                        return False, f"[{i}]: {err}"
            return True, None
        if t == "string":
            return (isinstance(value, str), None if isinstance(value, str) else "expected string")
        if t == "boolean":
            return (isinstance(value, bool), None if isinstance(value, bool) else "expected boolean")
        if t in ("number", "integer"):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            return (ok, None if ok else "expected number")
        return True, None


def _fill_schema(schema, seed):
    """Deterministic generic filler used for schemas the mock doesn't special-case."""
    t = schema.get("type")
    if t == "object":
        keys = schema.get("required") or list(schema.get("properties", {}))
        return {k: _fill_schema(schema["properties"][k], f"{seed}/{k}") for k in keys}
    if t == "array":
        return [_fill_schema(schema["items"], f"{seed}/0")]
    if t == "boolean":
        return _stable_hash(seed) % 4 != 0
    if t in ("number", "integer"):
        return _stable_hash(seed) % 5
    return seed.rsplit("/", 1)[-1]


# -- Agent Runners --


@dataclass(frozen=True)
class RunnerOutput:
    value: object
    tokens: int


class MockAgentRunner:
    """Deterministic runner used by demo mode and unit tests."""

    def run(self, prompt, schema=None, label=None):
        if schema is None:
            value = f"[mock] {(label or prompt)[:60]}"
            return RunnerOutput(value, self._tokens(prompt, value))
        props = schema.get("properties", {})
        if "findings" in props:
            n = 1 + (_stable_hash(prompt) % 2)
            sev = ["high", "medium", "low"]
            value = {"findings": [
                {"title": f"{label or 'audit'} #{i + 1}",
                 "severity": sev[_stable_hash(prompt + str(i)) % 3]}
                for i in range(n)
            ]}
        elif "isReal" in props:
            real = _stable_hash(prompt) % 4 != 0
            value = {"isReal": real,
                     "reason": "reproduced" if real else "could not reproduce"}
        else:
            value = _fill_schema(schema, prompt)
        return RunnerOutput(value, self._tokens(prompt, value))

    @staticmethod
    def _tokens(prompt, result):
        return len(prompt) // 4 + len(json.dumps(result, default=str)) // 4


def _response_text(response) -> str:
    return "\n".join(
        str(getattr(block, "text", ""))
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    ).strip()


def _parse_runner_json(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for position, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(stripped[position:])
            except json.JSONDecodeError:
                continue
            return value
        raise WorkflowInputError("workflow agent returned invalid JSON")


class AnthropicAgentRunner:
    """Run workflow agents through the same API client as the host."""

    def __init__(self, client, model):
        self.client = client
        self.model = model

    def run(self, prompt, schema=None, label=None):
        request = prompt
        if schema is not None:
            request += (
                "\n\nReturn only one JSON object matching this schema:\n"
                + json.dumps(schema, ensure_ascii=True, sort_keys=True)
            )
        response = self.client.messages.create(
            model=self.model,
            system=(
                "You are a focused workflow agent. Complete only the supplied "
                "step. Do not claim access to files or results not included in "
                "the prompt."
            ),
            messages=[{"role": "user", "content": request}],
            max_tokens=2000,
        )
        text = _response_text(response)
        if schema is None:
            value = text
        else:
            try:
                value = _parse_runner_json(text)
            except WorkflowInputError:
                # Let ExecutionState's schema check trigger its single retry.
                value = text
        usage = getattr(response, "usage", None)
        tokens = int(getattr(usage, "input_tokens", 0) or 0) + int(
            getattr(usage, "output_tokens", 0) or 0
        )
        return RunnerOutput(value, tokens)


RUNNER_FACTORY = MockAgentRunner


# -- Journal --
class WorkflowJournal:
    """Append-only <runId>.journal.jsonl with longest-unchanged-prefix resume.

    Replay walks agent() calls in *invocation* order (the contract Claude Code
    and mature Pi ports use). Cache hits continue only while each call's
    semantic key matches the next journal entry. The first mismatch or missing
    entry breaks the prefix: every later call runs live, even if an older key
    still exists further down the journal.

    Why real JS runtimes ban Date.now() / Math.random() / bare new Date(): those
    make call order or prompts nondeterministic, so resume cannot match the
    journal. This Python teaching runtime does not sandbox that — write
    deterministic scripts anyway.
    """

    def __init__(self, run_id, resume, store=None):
        store = STORE if store is None else store
        store.mkdir(parents=True, exist_ok=True)
        self.path = store / f"{run_id}.journal.jsonl"
        self.resume = resume
        self.entries = []
        self.cache = {}
        self._cursor = 0          # next call-order index to assign
        self._write_cursor = 0    # next index to flush to disk
        self._pending = {}        # idx -> (key, value) awaiting in-order flush
        self._prefix_broken = False
        self._did_truncate = False
        if resume:
            if not self.path.exists():
                raise WorkflowInputError(f"resume journal not found for {run_id}")
            for line_number, line in enumerate(self.path.read_text().splitlines(), start=1):
                try:
                    rec = json.loads(line)
                    if (
                        not isinstance(rec, dict)
                        or not isinstance(rec.get("key"), str)
                        or "value" not in rec
                    ):
                        raise ValueError("expected key/value record")
                except (json.JSONDecodeError, ValueError) as exc:
                    raise WorkflowInputError(
                        f"invalid resume journal record at line {line_number}"
                    ) from exc
                self.entries.append({"key": rec["key"], "value": rec["value"]})
                self.cache[rec["key"]] = rec["value"]
            self._f = self.path.open("a")
        else:
            self._f = self.path.open("w")             # fresh run truncates

    def key(self, kind, label, prompt, schema):
        # Content hash identifies *this* call. Prefix matching uses call order;
        # the hash must stay stable across resume (not Python's salted hash()).
        basis = f"{kind}|{label}|{prompt}|{json.dumps(schema, sort_keys=True)}"
        return f"{kind}-{_stable_hash(basis) % 10**10:010d}"

    def try_replay(self, key):
        """Reserve the next call-order slot. Return (cached_value_or_MISS, idx)."""
        idx = self._cursor
        self._cursor += 1
        if self._prefix_broken or not self.resume:
            return MISS, idx
        if idx >= len(self.entries) or self.entries[idx]["key"] != key:
            self._prefix_broken = True
            return MISS, idx
        return self.entries[idx]["value"], idx

    def record(self, idx, key, value):
        """Record a live result at call-order index idx; flush in order."""
        if self.resume and self._prefix_broken and not self._did_truncate:
            # Keep only the unchanged prefix; rewrite the file from there.
            self.entries = self.entries[:idx]
            self._f.close()
            self._f = self.path.open("w")
            for rec in self.entries:
                self._f.write(json.dumps({"key": rec["key"], "value": rec["value"]}) + "\n")
            self._f.flush()
            self._write_cursor = len(self.entries)
            self._did_truncate = True

        self._pending[idx] = (key, value)
        while self._write_cursor in self._pending:
            k, v = self._pending.pop(self._write_cursor)
            self._f.write(json.dumps({"key": k, "value": v}) + "\n")
            self._f.flush()
            rec = {"key": k, "value": v}
            if self._write_cursor < len(self.entries):
                self.entries[self._write_cursor] = rec
            else:
                self.entries.append(rec)
            self.cache[k] = v
            self._write_cursor += 1

    def close(self):
        self._f.close()


# -- Token Budget --
class Budget:
    """budget.total / spent() / remaining(). Once spent reaches total, agent()
    calls raise instead of silently overspending."""

    def __init__(self, total=None):
        self.total = total
        self._spent = 0

    def add(self, n):
        if self.total is not None and self._spent + n > self.total:
            raise WorkflowInputError(
                f"token budget exceeded ({self._spent + n} > {self.total})"
            )
        self._spent += n

    def spent(self):
        return self._spent

    def remaining(self):
        return float("inf") if self.total is None else max(0, self.total - self._spent)


# -- Workflow Task Lifecycle --
class LocalWorkflowTask:
    """Hold workflow status, usage, and progress events."""

    def __init__(self, task_id, run_id, meta):
        self.task_id = task_id
        self.run_id = run_id
        self.meta = meta
        self.status = "running"
        self.usage = {"agents": 0, "tokens": 0}
        self.progress = []

    def event(self, name, **data):
        line = " ".join(f"{k}={v}" for k, v in data.items())
        print(f"  event      {name:<18} {line}")

    def progress_event(self, ptype, **data):
        self.progress.append({"type": ptype, **data})
        line = " ".join(f"{k}={v}" for k, v in data.items())
        print(f"  progress   {ptype:<16} {line}")


# -- Workflow Primitives --
class ExecutionLimits:
    """Shared run-wide limits, including nested workflows."""

    def __init__(self):
        self.agents = 0
        self.semaphore = asyncio.Semaphore(CONCURRENCY)

    def claim_agent(self):
        self.agents += 1
        if self.agents > AGENT_CAP:
            raise WorkflowInputError(f"agent() cap reached ({AGENT_CAP})")


class ExecutionState:
    """Injected into the workflow script with the orchestration primitives."""

    def __init__(self, task, journal, runner, budget, args, depth=0, limits=None):
        self.task = task
        self.journal = journal
        self.runner = runner
        self.budget = budget
        self.args = args
        self._depth = depth
        self._phase = None
        self._phases_seen = set()
        self._limits = limits or ExecutionLimits()
        # Serializes call-order tickets so parallel agent() invocations still
        # get a stable prefix position (creation order, not completion order).
        self._order_lock = asyncio.Lock()

    def phase(self, title):
        """Start a phase; subsequent agent()s group under it. Upsert: emitting the
        same phase again (e.g. from each pipeline item) does not re-announce it."""
        self._phase = title
        if title not in self._phases_seen:
            self._phases_seen.add(title)
            self.task.progress_event("workflow_phase", title=title)

    def log(self, message):
        """Emit a workflow_log progress line."""
        self.task.progress_event("workflow_log", message=message)

    async def agent(self, prompt, schema=None, label=None, phase=None):
        """Spawn one subagent. With a schema, validate (+ one retry).

        Resume uses longest unchanged prefix in agent() call order: hits continue
        until the first changed/missing call; everything after runs live.
        """
        label = label or (prompt[:24] + "...")
        self._limits.claim_agent()
        if self.budget.remaining() <= 0:
            raise WorkflowInputError("token budget exceeded")

        key = self.journal.key("agent", label, prompt, schema)
        async with self._order_lock:
            cached, call_idx = self.journal.try_replay(key)
            if cached is not MISS:
                # None is a recorded failure (null-isolation); replay it as-is.
                if cached is not None and schema is not None:
                    ok, err = SimpleJsonSchema(schema).validate(cached)
                    if not ok:
                        raise WorkflowInputError(
                            f"cached agent output failed schema validation: {err}"
                        )
                self.task.progress_event(
                    "workflow_agent",
                    label=label,
                    phase=phase or self._phase,
                    status="cached",
                )
                return cached

        result = None
        tokens = 0
        live_error = None
        try:
            async with self._limits.semaphore:
                run = await asyncio.to_thread(
                    self.runner.run, prompt, schema, label
                )
                result = run.value
                tokens = run.tokens

            if schema is not None:
                ok, err = SimpleJsonSchema(schema).validate(result)
                if not ok:
                    retry = await asyncio.to_thread(
                        self.runner.run,
                        prompt + "\n\nReturn valid JSON.",
                        schema,
                        label,
                    )
                    result = retry.value
                    tokens += retry.tokens
                    ok, err = SimpleJsonSchema(schema).validate(result)
                    if not ok:
                        raise WorkflowInputError(
                            f"agent({{schema}}) invalid output: {err}"
                        )

            self.budget.add(tokens)
            self.task.usage["agents"] += 1
            self.task.usage["tokens"] += tokens
        except Exception as exc:
            # Fill the call-order slot with null so later parallel records can
            # flush; parallel/pipeline turn the raise into a null slot.
            result = None
            live_error = exc

        async with self._order_lock:
            self.journal.record(call_idx, key, result)

        if live_error is not None:
            self.task.progress_event(
                "workflow_agent",
                label=label,
                phase=phase or self._phase,
                status="null",
            )
            raise live_error

        self.task.progress_event("workflow_agent", label=label,
                                 phase=phase or self._phase, status="done")
        return result

    async def parallel(self, thunks):
        """BARRIER: run all thunks concurrently; wait for every result.

        A failing thunk becomes None in that slot — the gather itself does not
        reject. Filter with care (e.g. [x for x in results if x]).
        """
        async def isolate(thunk):
            try:
                return await thunk()
            except Exception as exc:
                self.log(f"parallel step → null ({type(exc).__name__})")
                return None

        return await asyncio.gather(*[isolate(thunk) for thunk in thunks])

    async def pipeline(self, items, *stages):
        """Per-item staged flow, NO barrier between stages: item A can be in
        stage 3 while item B is still in stage 1. Each stage gets
        (prev_result, original_item, index).

        A failing stage drops that item to None and skips its remaining stages;
        other items keep going.
        """
        async def run_item(item, idx):
            value = item
            for stage in stages:
                try:
                    value = await stage(value, item, idx)
                except Exception as exc:
                    self.log(
                        f"pipeline item {idx} → null ({type(exc).__name__})"
                    )
                    return None
                if value is None:
                    return None
            return value

        return await asyncio.gather(*[run_item(it, i) for i, it in enumerate(items)])

    async def workflow(self, name, args=None):
        """Run a saved workflow inline as a child (one level), sharing this run's
        journal + budget + agent counter."""
        if self._depth >= 1:
            raise WorkflowInputError("workflow() nesting is one level only")
        if name not in WORKFLOWS:
            raise WorkflowInputError(f"unknown workflow '{name}'")
        meta, fn = WORKFLOWS[name]
        child = ExecutionState(self.task, self.journal, self.runner, self.budget,
                               args or {}, depth=self._depth + 1,
                               limits=self._limits)
        return await fn(child, args or {})


# -- Workflow Tool --
class WorkflowTool:
    """The Workflow tool. .call() validates meta, runs the permission check,
    creates runId/taskId, registers a LocalWorkflowTask, and emits lifecycle
    events while executing the script. It returns the result and task state and
    supports resume."""

    async def call(self, meta, script_fn, args=None, resume_from_run_id=None):
        validate_meta(meta)
        check_permission(meta)
        resuming = resume_from_run_id is not None
        if resuming:
            run_id = validate_run_id(resume_from_run_id)
        else:
            run_id = reserve_run_id(meta)
        with workflow_run_lock(run_id):
            return await self._call_locked(
                meta, script_fn, args, run_id, resuming
            )

    async def _call_locked(self, meta, script_fn, args, run_id, resuming):
        if resuming:
            snapshot = _read_snapshot(run_id)
            if snapshot.get("workflowName") != meta["name"]:
                raise WorkflowInputError("resume runId does not match workflow meta")
            saved_args = snapshot.get("args", {})
            if args is None:
                args = saved_args
            elif args != saved_args:
                raise WorkflowInputError("resume args do not match the original run")
            journal = WorkflowJournal(run_id, resume=True)
        else:
            args = args or {}
            journal = WorkflowJournal(run_id, resume=False)
        task_id = create_task_id(run_id)

        task = LocalWorkflowTask(task_id, run_id, meta)
        # Record the launch envelope before workflow execution starts.
        launched = {"status": "async_launched", "taskId": task_id,
                    "taskType": "local_workflow", "runId": run_id,
                    "workflowName": meta["name"]}
        task.event("async_launched", runId=run_id, taskId=task_id)
        task.event("task_started", workflow=meta["name"],
                   phases=",".join(meta.get("phases", [])) or "-",
                   resume=resuming)
        _write_json(STORE / f"{run_id}.json", {
            "runId": run_id,
            "workflowName": meta["name"],
            "args": args,
            "task": serialize_task(task),
        })

        try:
            ctx = ExecutionState(
                task, journal, RUNNER_FACTORY(), Budget(args.get("budget")), args
            )
            result = await script_fn(ctx, args)
            task.status = "completed"
        except Exception as e:                          # failed / stopped close the loop too
            task.status = "failed"
            result = {"error": str(e)}
        finally:
            journal.close()

        _write_json(STORE / f"{run_id}.output.json", result)
        _write_json(STORE / f"{run_id}.json", {
            "runId": run_id,
            "workflowName": meta["name"],
            "args": args,
            "task": serialize_task(task),
        })
        _save_last_run(run_id)
        task.event("task_notification", status=task.status,
                   agents=task.usage["agents"], tokens=task.usage["tokens"],
                   outputFile=f".runtime/{run_id}.output.json")
        return {"launched": launched, "result": result, "task": task}


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=str))
    os.replace(temporary, path)


def _read_snapshot(run_id):
    path = STORE / f"{run_id}.json"
    if not path.exists():
        raise WorkflowInputError(f"resume snapshot not found for {run_id}")
    try:
        snapshot = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise WorkflowInputError(f"invalid resume snapshot for {run_id}") from exc
    if not isinstance(snapshot, dict):
        raise WorkflowInputError(f"invalid resume snapshot for {run_id}")
    return snapshot


def _save_last_run(run_id):
    (STORE / "last_run.txt").write_text(run_id)


def _read_last_run():
    p = STORE / "last_run.txt"
    return p.read_text().strip() if p.exists() else None


# -- Sample Workflow --
FINDINGS_SCHEMA = {
    "type": "object", "required": ["findings"],
    "properties": {"findings": {"type": "array", "items": {
        "type": "object", "required": ["title", "severity"],
        "properties": {
            "title": {"type": "string"},
            "severity": {
                "type": "string", "enum": ["high", "medium", "low"]
            },
        }}}},
}
VERDICT_SCHEMA = {
    "type": "object", "required": ["isReal", "reason"],
    "properties": {"isReal": {"type": "boolean"}, "reason": {"type": "string"}},
}

SAMPLE_META = {
    "name": "review-changes",
    "description": "Review changed files across dimensions, verify each finding",
    "phases": ["Review", "Verify"],
}

DIMENSIONS = ["correctness", "security", "performance", "style"]
DEMO_CHANGES = (
    "def load_user(user_id):\n"
    "    query = f\"SELECT * FROM users WHERE id = {user_id}\"\n"
    "    return db.execute(query).fetchone()\n"
)


async def sample_workflow(ctx, args):
    """pipeline over review dimensions (audit -> verify-each), then keep only the
    findings a verifier confirms. The plan is code, not a chat turn."""
    ctx.phase("Review")
    changes = args.get("changes", "")
    if not isinstance(changes, str):
        raise WorkflowInputError("args.changes must be a string")
    review_input = changes.strip() or "No change context was supplied."

    async def audit(_value, dimension, _idx):
        out = await ctx.agent(
            f"Review this change context for {dimension} issues. "
            "Report only issues supported by the supplied text.\n\n"
            f"{review_input}",
            schema=FINDINGS_SCHEMA, label=f"audit:{dimension}", phase="Review")
        return {"dimension": dimension, "findings": out["findings"]}

    async def verify(audited, dimension, _idx):
        ctx.phase("Verify")
        # Each finding is verified by its own adversarial subagent, concurrently.
        verdicts = await ctx.parallel([
            (lambda f=f: ctx.agent(
                f"Adversarially verify this {dimension} finding against the "
                "supplied change context.\n\n"
                f"Change context:\n{review_input}\n\n"
                f"Finding:\n{json.dumps(f, ensure_ascii=True)}",
                schema=VERDICT_SCHEMA, label=f"verify:{dimension}:{f['title']}", phase="Verify"))
            for f in audited["findings"]])
        confirmed = [f for f, v in zip(audited["findings"], verdicts)
                     if v and v.get("isReal")]
        return {"dimension": dimension, "confirmed": confirmed}

    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    confirmed = [{"dimension": r["dimension"], **f}
                 for r in results if r for f in r["confirmed"]]
    confirmed.sort(key=lambda f: {"high": 0, "medium": 1, "low": 2}.get(f["severity"], 3))
    ctx.log(f"confirmed {len(confirmed)} real finding(s)")
    return {"confirmed": confirmed}


# Saved workflow registry
WORKFLOWS = {SAMPLE_META["name"]: (SAMPLE_META, sample_workflow)}

# Teaching adapter: saved-workflow path (name + args). Claude Code also accepts
# script / scriptPath for dynamic JS the model writes; we keep this surface
# small and map the same resume idea via resume_from_run_id / resumeFromRunId.
WORKFLOW_TOOL = {
    "name": "Workflow",
    "description": (
        "Run a saved workflow by name. Pass input in args. "
        "Optional resume_from_run_id (alias: resumeFromRunId) continues a prior run."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "object"},
            "resume_from_run_id": {"type": "string"},
            "resumeFromRunId": {"type": "string"},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
}


def serialize_task(task):
    return {
        "taskId": task.task_id,
        "taskType": "local_workflow",
        "runId": task.run_id,
        "workflowName": task.meta["name"],
        "status": task.status,
        "usage": dict(task.usage),
        "progress": list(task.progress),
    }


async def run_workflow(
    name,
    args=None,
    resume_from_run_id=None,
    resumeFromRunId=None,
):
    """Model-facing adapter: resolve a saved workflow from the host registry.

    Claude Code's dynamic door passes script/scriptPath instead of name; this
    teaching runtime stays on the saved-name path so every line stays readable.
    """
    if not isinstance(name, str):
        raise WorkflowInputError("workflow name must be a string")
    if name not in WORKFLOWS:
        raise WorkflowInputError(f"unknown workflow '{name}'")
    if args is not None and not isinstance(args, dict):
        raise WorkflowInputError("workflow args must be an object")
    if resume_from_run_id and resumeFromRunId and resume_from_run_id != resumeFromRunId:
        raise WorkflowInputError(
            "resume_from_run_id and resumeFromRunId disagree"
        )
    resume_id = resume_from_run_id or resumeFromRunId
    meta, script_fn = WORKFLOWS[name]
    out = await WorkflowTool().call(
        meta,
        script_fn,
        args=args,
        resume_from_run_id=resume_id,
    )
    return {
        "launched": out["launched"],
        "result": out["result"],
        "task": serialize_task(out["task"]),
    }


WORKFLOW_HANDLERS = {"Workflow": run_workflow}
INHERITS_TOOLS_FROM = "s15"


def run_workflow_sync(**tool_input):
    """Bridge the synchronous host dispatcher to the async workflow runtime."""
    try:
        return json.dumps(asyncio.run(run_workflow(**tool_input)), default=str)
    except WorkflowInputError as exc:
        return f"Error: {exc}"


def install_workflow_tool(host):
    """Extend the s15 host tool pool without changing its dispatch loop."""
    global RUNNER_FACTORY
    RUNNER_FACTORY = lambda: AnthropicAgentRunner(host.client, host.MODEL)
    if getattr(host, "_workflow_tool_installed", False):
        return
    base_assemble = host.assemble_tool_pool

    def assemble_with_workflow():
        tools, handlers = base_assemble()
        if not any(tool.get("name") == "Workflow" for tool in tools):
            tools.append(WORKFLOW_TOOL)
        handlers["Workflow"] = run_workflow_sync
        return tools, handlers

    host.assemble_tool_pool = assemble_with_workflow
    host._workflow_tool_installed = True


def load_integrated_host():
    """Load s15 lazily so deterministic workflow tests need no API key."""
    path = Path(__file__).resolve().parents[1] / "s15_integrated_harness" / "code.py"
    spec = importlib.util.spec_from_file_location("integrated_host", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load integrated host from {path}")
    host = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = host
    spec.loader.exec_module(host)
    return host


# -- CLI --
async def run_demo(argv):
    resume_id = None
    if argv and argv[0] == "resume":
        resume_id = _read_last_run()
        if not resume_id:
            print("nothing to resume; run `python code.py demo` first.")
            return
        print(
            f"resuming {resume_id}\n"
            "longest unchanged agent() prefix → cache hit; "
            "first change breaks the prefix\n"
        )
    else:
        print("launching saved workflow `review-changes`")
        print("watch phases: Review → Verify, then a confirmed list\n")

    out = await WORKFLOW_HANDLERS["Workflow"](
        name="review-changes",
        args={"budget": None, "changes": DEMO_CHANGES},
        resume_from_run_id=resume_id,
    )

    print("\nresult:")
    for f in out["result"].get("confirmed", []):
        print(f"  [{f['severity']:<6}] {f['dimension']}: {f['title']}")
    task = out["task"]
    usage = task["usage"]
    print(f"\nstatus={task['status']}  agents={usage['agents']}  "
          f"tokens={usage['tokens']}  journal=.runtime/{task['runId']}.journal.jsonl")


def run_cli():
    """Run the cumulative s15 host with Workflow added to its tool pool."""
    host = load_integrated_host()
    install_workflow_tool(host)
    host.CLI_ACTIVE = True
    host.start_runtime_services()
    print("s16: workflow runtime")
    print("Enter a question, press Enter to send. Type q to quit.\n")
    history = []
    context = host.update_context({}, history)
    session_state = {"active_user_request": "(no active user request)"}
    threading.Thread(
        target=host.async_event_loop,
        args=(history, context, session_state),
        daemon=True,
    ).start()
    while True:
        try:
            query = host.CONSOLE.ask("\033[36ms16 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        with host.agent_lock:
            host.trigger_hooks("UserPromptSubmit", query)
            turn_start = len(history)
            session_state["active_user_request"] = query
            history.append({"role": "user", "content": query})
            host.agent_loop(history, context, query)
            context = host.update_context(context, history)
            host.print_turn_assistants(history, turn_start)
        print()


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] in {"demo", "resume"}:
        asyncio.run(run_demo(sys.argv[1:]))
    else:
        run_cli()
