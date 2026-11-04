import importlib.util
import multiprocessing
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s13_agent_teams" / "code.py"
DOWNSTREAM_LESSONS = (
    ROOT / "s15_integrated_harness" / "code.py",
)
RUNTIME_LESSONS = (LESSON, *DOWNSTREAM_LESSONS)
MCP_LESSONS = (
    ROOT / "s14_mcp_plugin" / "code.py",
    ROOT / "s15_integrated_harness" / "code.py",
)
BACKGROUND_LESSONS = tuple(
    ROOT / name / "code.py" for name in (
        "s11_background_tasks",
        "s15_integrated_harness",
    )
)
CRON_LESSONS = tuple(
    ROOT / name / "code.py" for name in (
        "s12_cron_scheduler",
        "s15_integrated_harness",
    )
)


def load_lesson(temp_cwd: Path, lesson_path: Path = LESSON):
    fake_anthropic = types.ModuleType("anthropic")
    fake_yaml = types.ModuleType("yaml")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)
    setattr(fake_yaml, "safe_load", lambda value: {})
    setattr(fake_yaml, "YAMLError", ValueError)

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
        "yaml": sys.modules.get("yaml"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")

    name = f"agent_teams_test_{lesson_path.parent.name}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, lesson_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {lesson_path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules["yaml"] = fake_yaml
    sys.modules[name] = module
    try:
        os.chdir(temp_cwd)
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        for module_name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def init_git_repo(root: Path):
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.com"],
        cwd=root, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Runtime Tests"],
        cwd=root, check=True,
    )
    (root / "tracked.txt").write_text("initial\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=root, check=True
    )


def claim_in_child(lesson_path: str, root: str, task_id: str, owner: str,
                   barrier, results):
    lesson = load_lesson(Path(root), Path(lesson_path))
    barrier.wait()
    results.put(lesson.claim_task(task_id, owner=owner))


def update_in_child(lesson_path: str, root: str, task_id: str,
                    dependency_id: str, barrier, results):
    lesson = load_lesson(Path(root), Path(lesson_path))
    barrier.wait()
    results.put(lesson.run_update_task(task_id, [dependency_id]))


class AgentTeamsRuntimeTests(unittest.TestCase):
    def test_downstream_lessons_execute_the_merged_runtime_contract(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    task = lesson.create_task("Runtime contract")
                    self.assertIn(
                        "Claimed", lesson.claim_task(task.id, owner="alice")
                    )
                    self.assertIn(
                        "Completed", lesson.complete_task(task.id, owner="alice")
                    )
                    self.assertIn("alice", lesson.teammate_assignments)
                    self.assertTrue(lesson.release_completed_assignment("alice"))
                    self.assertNotIn("alice", lesson.teammate_assignments)

    def test_task_dependencies_use_runtime_ids_and_are_lead_only(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    tool_defs = getattr(lesson, "TOOLS", None)
                    if tool_defs is None:
                        tool_defs = lesson.BUILTIN_TOOLS
                    tools = {tool["name"]: tool for tool in tool_defs}

                    self.assertIn("update_task", tools)
                    self.assertNotIn(
                        "blockedBy",
                        tools["create_task"]["input_schema"]["properties"],
                    )
                    self.assertIn(
                        "runtime-generated IDs",
                        lesson.PROMPT_SECTIONS["tasks"],
                    )

                    dependency = lesson.create_task("Create schema")
                    target = lesson.create_task("Write API")
                    self.assertIn(
                        "Updated",
                        lesson.run_update_task(target.id, [dependency.id]),
                    )
                    self.assertEqual(
                        lesson.load_task(target.id).blockedBy, [dependency.id]
                    )

                    captured_tools = []

                    def stop_after_capture(**kwargs):
                        captured_tools.extend(
                            tool["name"] for tool in kwargs["tools"]
                        )
                        raise RuntimeError("stop after capturing teammate tools")

                    lesson.client.messages.create = stop_after_capture
                    lesson.spawn_teammate_thread(
                        "tool-auditor", "reviewer", "Inspect the task board."
                    )
                    self.assertTrue(wait_until(
                        lambda: "tool-auditor" not in lesson.active_teammates
                    ))
                    self.assertIn("claim_task", captured_tools)
                    self.assertNotIn("update_task", captured_tools)

    def test_inbox_delivery_is_runtime_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))

            tool_names = {tool["name"] for tool in lesson.TOOLS}
            self.assertNotIn("check_inbox", tool_names)
            self.assertIn("create_worktree", tool_names)
            self.assertNotIn("remove_worktree", tool_names)
            self.assertNotIn("keep_worktree", tool_names)
            worktree_tools = {
                tool["name"]: tool["input_schema"] for tool in lesson.TOOLS
                if tool["name"] == "create_worktree"
            }
            for schema in worktree_tools.values():
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["name"]["maxLength"], 64)
            self.assertIn("wait for the user's confirmation",
                          lesson.PROMPT_SECTIONS["teams"])
            self.assertIn("creating a Task", lesson.PROMPT_SECTIONS["teams"])
            self.assertIn("not a sandbox", lesson.PROMPT_SECTIONS["teams"])

            lesson.BUS.send("alice", "lead", "done", "result")
            events = lesson.consume_lead_inbox()

            self.assertEqual([event["type"] for event in events], ["result"])
            self.assertIn("[result] alice: done",
                          lesson.format_team_events(events))

    def test_spawn_claims_the_initial_task_before_starting_the_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            task = lesson.create_task("Review authentication")
            schema = next(
                tool["input_schema"] for tool in lesson.TOOLS
                if tool["name"] == "spawn_teammate"
            )
            self.assertIn("task_id", schema["properties"])

            with patch.object(
                lesson.threading.Thread, "start", lambda _thread: None
            ):
                result = lesson.spawn_teammate_thread(
                    "alice", "reviewer", "Review the assigned Task.", task.id
                )

            self.assertIn(task.id, result)
            claimed = lesson.load_task(task.id)
            self.assertEqual(claimed.status, "in_progress")
            self.assertEqual(claimed.owner, "alice")
            self.assertEqual(
                lesson.teammate_assignments["alice"]["task_id"], task.id
            )

    def test_spawn_allows_an_idle_teammate_without_an_initial_task(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    tool_defs = getattr(lesson, "TOOLS", None)
                    if tool_defs is None:
                        tool_defs = lesson.BUILTIN_TOOLS
                    schema = next(
                        tool["input_schema"] for tool in tool_defs
                        if tool["name"] == "spawn_teammate"
                    )
                    self.assertNotIn("task_id", schema["required"])

                    with patch.object(
                        lesson.threading.Thread, "start", lambda _thread: None
                    ):
                        result = lesson.run_spawn_teammate(
                            "alice", "reviewer", "Wait for a ready Task."
                        )

                    self.assertIn("without an initial Task", result)
                    self.assertNotIn("alice", lesson.teammate_assignments)

    def test_teammate_workspace_tools_require_a_claimed_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lesson = load_lesson(root)
            runtime = lesson.TeammateRuntime(
                "alice", "reviewer", "Inspect the project.", None, False
            )

            result = runtime.write("unassigned.txt", "must not be written")

            self.assertIn("Claim a Task", result)
            self.assertFalse((root / "unassigned.txt").exists())

    def test_plain_message_does_not_change_assignment_or_plan_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.active_teammates["alice"] = "working"
            lesson.plan_gates["alice"] = "approved"
            lesson.assignment_versions["alice"] = 3

            self.assertIn("Sent", lesson.run_send_message("alice", "Continue."))

            self.assertEqual(lesson.plan_gates["alice"], "approved")
            self.assertEqual(lesson.assignment_versions["alice"], 3)

    def test_worktree_removal_is_host_only(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    tool_defs = getattr(lesson, "TOOLS", None)
                    if tool_defs is None:
                        tool_defs = lesson.BUILTIN_TOOLS
                    self.assertNotIn(
                        "remove_worktree",
                        {tool["name"] for tool in tool_defs},
                    )
                    self.assertTrue(callable(lesson.remove_worktree))
                    self.assertFalse(hasattr(lesson, "run_remove_worktree"))

    def test_agent_teams_builds_on_tasks_not_background_or_cron(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lesson = load_lesson(root)
            tool_names = {tool["name"] for tool in lesson.TOOLS}

            self.assertTrue({
                "bash", "read_file", "write_file", "edit_file", "glob",
                "create_task", "list_tasks", "get_task", "claim_task",
                "complete_task", "spawn_teammate", "list_teammates",
                "send_message", "request_shutdown", "request_plan",
                "review_plan", "create_worktree",
            }.issubset(tool_names))
            self.assertTrue({
                "schedule_cron", "list_crons", "cancel_cron",
            }.isdisjoint(tool_names))
            self.assertNotIn("run_in_background", next(
                tool["input_schema"] for tool in lesson.TOOLS
                if tool["name"] == "bash"
            )["properties"])
            self.assertFalse((root / ".tasks").exists())
            self.assertFalse((root / ".mailboxes").exists())
            self.assertFalse((root / ".worktrees").exists())

    def test_integrated_harness_reuses_memory_recall_and_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp), DOWNSTREAM_LESSONS[0])
            calls = []
            lesson.MEMORY_RUNTIME = types.SimpleNamespace(
                read_memory_index=lambda: "- [Style](style.md) - Project style",
                load_memories=lambda messages: (
                    calls.append(("recall", list(messages)))
                    or '[{"source":"style.md","content":"Use black."}]'
                ),
                extract_memories=lambda messages: (
                    calls.append(("extract", list(messages))) or 1
                ),
                consolidate_memories=lambda: calls.append(("consolidate", None)),
            )
            messages = [{"role": "user", "content": "Format this file."}]

            context = lesson.update_context({}, messages)
            system = lesson.assemble_system_prompt(context)
            lesson.remember_after_turn(messages)

            self.assertIn("Memory catalog", system)
            self.assertIn("Relevant memory records", system)
            self.assertEqual(
                [name for name, _payload in calls],
                ["recall", "extract", "consolidate"],
            )

    def test_mcp_lesson_builds_on_the_base_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s14_mcp_plugin" / "code.py"
            )
            tools_before, handlers_before = lesson.assemble_tool_pool()
            self.assertEqual(
                {tool["name"] for tool in tools_before},
                {"bash", "read_file", "write_file", "edit_file", "glob",
                 "connect_mcp"},
            )
            self.assertNotIn("mcp__docs__search", handlers_before)

            self.assertIn(
                "Connected to MCP server 'docs'", lesson.connect_mcp("docs")
            )
            tools_after, handlers_after = lesson.assemble_tool_pool()
            self.assertIn(
                "mcp__docs__search",
                {tool["name"] for tool in tools_after},
            )
            self.assertEqual(
                handlers_after["mcp__docs__search"](query="hooks"),
                "[docs] Found 3 results for 'hooks'",
            )

    def test_background_dispatch_is_bash_only_and_reports_failures(self):
        for lesson_path in BACKGROUND_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    self.assertFalse(
                        lesson.should_run_background(
                            "write_file", {"run_in_background": True}
                        )
                    )
                    block = types.SimpleNamespace(
                        id="tool_fail",
                        name="bash",
                        input={"command": "exit 7", "run_in_background": True},
                    )
                    if lesson_path.parent.name in {
                        "s14_mcp_plugin", "s15_integrated_harness"
                    }:
                        bg_id = lesson.start_background_task(block, {})
                    else:
                        bg_id = lesson.start_background_task(block)
                    self.assertTrue(
                        wait_until(
                            lambda: lesson.background_tasks[bg_id]["status"]
                            != "running"
                        )
                    )
                    self.assertEqual(
                        lesson.background_tasks[bg_id]["status"], "failed"
                    )
                    notification = lesson.collect_background_results()[0]
                    self.assertIn("<status>failed</status>", notification)
                    self.assertIn("status 7", notification)

    def test_shell_completion_terminates_children_in_the_same_process_group(self):
        for lesson_path in BACKGROUND_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    marker = Path(tmp) / "late-write.txt"
                    command = (
                        "nohup sh -c "
                        + shlex.quote(f"sleep 0.3; printf late > {marker}")
                        + " >/dev/null 2>&1 &"
                    )

                    _, exit_code = lesson._run_bash_process(command)
                    time.sleep(0.5)

                    self.assertEqual(exit_code, 0)
                    self.assertFalse(marker.exists())

    def test_sigterm_stops_active_shell_process_groups(self):
        for lesson_path in BACKGROUND_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    started = root / "started.txt"
                    late = root / "late.txt"
                    command = (
                        f"printf started > {shlex.quote(str(started))}; "
                        f"sleep 0.8; printf late > {shlex.quote(str(late))}"
                    )
                    script = (
                        "import importlib.util, os, sys, time, types\n"
                        "fake_anthropic = types.ModuleType('anthropic')\n"
                        "fake_anthropic.Anthropic = lambda *a, **k: "
                        "types.SimpleNamespace(messages=types.SimpleNamespace(create=None))\n"
                        "fake_dotenv = types.ModuleType('dotenv')\n"
                        "fake_dotenv.load_dotenv = lambda **k: None\n"
                        "fake_yaml = types.ModuleType('yaml')\n"
                        "fake_yaml.safe_load = lambda value: {}\n"
                        "fake_yaml.YAMLError = ValueError\n"
                        "sys.modules.update({'anthropic': fake_anthropic, "
                        "'dotenv': fake_dotenv, 'yaml': fake_yaml})\n"
                        f"os.environ['MODEL_ID'] = 'test-model'\n"
                        f"os.environ['ANTHROPIC_API_KEY'] = 'test-key'\n"
                        f"spec = importlib.util.spec_from_file_location('lesson', {str(lesson_path)!r})\n"
                        "lesson = importlib.util.module_from_spec(spec)\n"
                        "spec.loader.exec_module(lesson)\n"
                        f"lesson.run_bash({command!r}, run_in_background=True)\n"
                        "time.sleep(10)\n"
                    )
                    process = subprocess.Popen(
                        [sys.executable, "-c", script],
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    try:
                        self.assertTrue(wait_until(started.exists))
                        process.terminate()
                        process.wait(timeout=2)
                        time.sleep(1)
                        self.assertFalse(late.exists())
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=2)

    def test_durable_one_shot_is_acknowledged_after_model_acceptance(self):
        for lesson_path in CRON_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    job = lesson.CronJob(
                        id="cron_test",
                        cron="* * * * *",
                        prompt="resume the report",
                        recurring=False,
                        durable=True,
                        pending_delivery=True,
                    )
                    lesson.scheduled_jobs[job.id] = job
                    lesson.cron_queue.append(job)
                    lesson.save_durable_jobs()

                    self.assertIn(job.id, lesson.scheduled_jobs)
                    persisted = lesson.DURABLE_PATH.read_text()
                    self.assertIn('"pending_delivery": true', persisted)
                    lesson.client.messages.create = lambda **_: types.SimpleNamespace(
                        content=[], stop_reason="end_turn"
                    )
                    messages = []
                    if lesson_path.parent.name == "s15_integrated_harness":
                        lesson.agent_loop(messages, {}, "scheduled delivery")
                    else:
                        lesson.agent_loop(messages, {})

                    self.assertTrue(any(
                        message.get("content") == "[Scheduled] resume the report"
                        for message in messages
                    ))
                    self.assertNotIn(job.id, lesson.scheduled_jobs)
                    self.assertNotIn("cron_test", lesson.DURABLE_PATH.read_text())

    def test_failed_model_call_restores_unacknowledged_cron_delivery(self):
        for lesson_path in CRON_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    job = lesson.CronJob(
                        id="cron_retry",
                        cron="* * * * *",
                        prompt="retry me",
                        recurring=False,
                        durable=True,
                        pending_delivery=True,
                    )
                    lesson.scheduled_jobs[job.id] = job
                    lesson.cron_queue.append(job)
                    lesson.save_durable_jobs()
                    lesson.client.messages.create = (
                        lambda **_: (_ for _ in ()).throw(RuntimeError("offline"))
                    )

                    messages = []
                    if lesson_path.parent.name == "s15_integrated_harness":
                        lesson.agent_loop(messages, {}, "scheduled retry")
                    else:
                        lesson.agent_loop(messages, {})

                    self.assertIn(job.id, lesson.scheduled_jobs)
                    self.assertEqual(
                        [queued.id for queued in lesson.cron_queue], [job.id]
                    )
                    self.assertIn(job.id, lesson.DURABLE_PATH.read_text())

    def test_failed_cron_persistence_retries_before_queueing(self):
        for lesson_path in CRON_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    job = lesson.CronJob(
                        id="cron_persist_retry",
                        cron="* * * * *",
                        prompt="persist before delivery",
                        recurring=False,
                        durable=True,
                    )
                    lesson.scheduled_jobs[job.id] = job
                    original_save = lesson.save_durable_jobs
                    attempts = 0

                    def flaky_save():
                        nonlocal attempts
                        attempts += 1
                        if attempts == 1:
                            raise OSError("disk unavailable")
                        original_save()

                    lesson.save_durable_jobs = flaky_save
                    with self.assertRaisesRegex(OSError, "disk unavailable"):
                        with lesson.cron_lock:
                            lesson._enqueue_due_job(job)

                    self.assertFalse(job.pending_delivery)
                    self.assertEqual(lesson.cron_queue, [])

                    with lesson.cron_lock:
                        lesson._enqueue_due_job(job)

                    self.assertTrue(job.pending_delivery)
                    self.assertEqual([queued.id for queued in lesson.cron_queue], [job.id])
                    self.assertIn(
                        '"pending_delivery": true',
                        lesson.DURABLE_PATH.read_text(),
                    )

    def test_cancelled_cron_is_removed_from_pending_queue(self):
        for lesson_path in CRON_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    job = lesson.CronJob(
                        id="cron_cancel",
                        cron="* * * * *",
                        prompt="do not run",
                        recurring=True,
                        durable=True,
                    )
                    lesson.scheduled_jobs[job.id] = job
                    lesson.cron_queue.append(job)

                    self.assertIn("Cancelled", lesson.cancel_job(job.id))
                    self.assertEqual(lesson.consume_cron_queue(), [])

    def test_mcp_permission_uses_host_policy(self):
        for lesson_path in MCP_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    lesson.connect_mcp("deploy")
                    lesson.assemble_tool_pool()
                    status = types.SimpleNamespace(
                        name="mcp__deploy__status", input={"service": "web"}
                    )
                    trigger = types.SimpleNamespace(
                        name="mcp__deploy__trigger", input={"service": "web"}
                    )

                    self.assertIsNone(lesson.permission_hook(status))
                    with patch("builtins.input", return_value="no"):
                        self.assertEqual(
                            lesson.permission_hook(trigger),
                            "Permission denied by user",
                        )

                    spoofed = types.SimpleNamespace(
                        name="mcp__third_party__erase",
                        input={"description": "Erase records. (readOnly)"},
                    )
                    with patch("builtins.input", return_value="no"):
                        self.assertEqual(
                            lesson.permission_hook(spoofed),
                            "Permission denied by user",
                        )

    def test_integrated_permission_requires_approval_for_every_shell_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lesson = load_lesson(
                root, ROOT / "s15_integrated_harness" / "code.py"
            )
            outside = root.parent / f"outside-{time.time_ns()}.txt"
            block = types.SimpleNamespace(
                name="bash",
                input={"command": f"printf overwritten > {outside}"},
            )
            try:
                with patch("builtins.input", return_value="no"):
                    self.assertEqual(
                        lesson.permission_hook(block),
                        "Permission denied by user",
                    )
                self.assertFalse(outside.exists())
            finally:
                outside.unlink(missing_ok=True)

    def test_message_bus_rejects_unregistered_or_unsafe_recipients(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lesson = load_lesson(root)
            lesson.active_teammates["alice"] = "idle"

            with self.assertRaises(ValueError):
                lesson.BUS.send("alice", "../escape", "bad")
            self.assertFalse((root / "escape.jsonl").exists())

            result = lesson._teammate_send_message(
                "alice", "ghost", "Are you there?"
            )
            self.assertIn("not active", result)
            self.assertFalse((lesson.MAILBOX_DIR / "ghost.jsonl").exists())

    def test_reserved_teammate_names_do_not_shadow_runtime_identities(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)

                    for name in ("lead", "agent", "Lead", "Agent"):
                        rejected = lesson.spawn_teammate_thread(
                            name, "backend", "Inspect auth."
                        )
                        self.assertIn("reserved", rejected.lower())
                        self.assertNotIn(name, lesson.active_teammates)

                    lesson.BUS.send("alice", "lead", "still routable")
                    self.assertEqual(
                        lesson.BUS.read_inbox("lead")[0]["content"],
                        "still routable",
                    )

                    lesson.active_teammates["Alice"] = "idle"
                    duplicate = lesson.spawn_teammate_thread(
                        "alice", "backend", "Inspect auth."
                    )
                    self.assertIn("already exists", duplicate)

    def test_public_task_tools_return_errors_for_bad_ids(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    for task_id in ("../escape", "task_missing"):
                        for tool_name in (
                            "run_get_task",
                            "run_claim_task",
                            "run_complete_task",
                        ):
                            with self.subTest(tool=tool_name, task_id=task_id):
                                result = getattr(lesson, tool_name)(task_id)
                                self.assertIn("Error:", result)
                        self.assertIn(
                            "Error:", lesson.run_update_task(task_id, [])
                        )

    def test_plan_gate_blocks_mutating_tools_until_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            cases = {
                "write_file": {"path": "config.py", "content": "VALUE = 1"},
                "edit_file": {
                    "path": "config.py", "old_text": "0", "new_text": "1"
                },
            }
            for tool_name, tool_input in cases.items():
                with self.subTest(tool=tool_name):
                    calls = []
                    block = types.SimpleNamespace(
                        name=tool_name, input=tool_input
                    )
                    handlers = {
                        tool_name: lambda **kwargs: calls.append(kwargs) or "done"
                    }

                    lesson.plan_gates["alice"] = "pending"
                    blocked = lesson._run_teammate_tool(
                        "alice", block, handlers
                    )
                    self.assertIn("Blocked", blocked)
                    self.assertEqual(calls, [])

                    lesson.plan_gates["alice"] = "approved"
                    allowed = lesson._run_teammate_tool(
                        "alice", block, handlers
                    )
                    self.assertEqual(allowed, "done")
                    self.assertEqual(len(calls), 1)

    def test_teammate_tool_errors_become_tool_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.plan_gates["alice"] = "not_required"
            block = types.SimpleNamespace(
                name="write_file", input={"path": "config.py"}
            )

            result = lesson._run_teammate_tool(
                "alice", block,
                {"write_file": lambda path, content: "wrote"},
            )

            self.assertIn("TypeError", result)

    def test_teammate_keeps_complete_tool_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.IDLE_SCAN_INTERVAL = 5.0
            calls = 0

            def respond(**kwargs):
                nonlocal calls
                calls += 1
                self.assertEqual(
                    kwargs["messages"][0]["content"], "Inspect the project."
                )
                if calls <= 11:
                    return types.SimpleNamespace(
                        stop_reason="tool_use",
                        content=[types.SimpleNamespace(
                            type="tool_use", name="list_tasks",
                            id=f"list-{calls}", input={},
                        )],
                    )
                return types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(
                        type="text", text="Inspection complete."
                    )],
                )

            lesson.client.messages.create = respond
            lesson.spawn_teammate_thread(
                "alice", "reviewer", "Inspect the project."
            )
            self.assertTrue(wait_until(
                lambda: lesson.BUS.peek("lead"), timeout=3.0
            ))
            self.assertEqual(calls, 12)
            lesson.run_request_shutdown("alice")
            self.assertTrue(wait_until(
                lambda: "alice" not in lesson.active_teammates
            ))

    def test_s15_teammate_dispatch_runs_permission_and_post_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            block = types.SimpleNamespace(
                name="write_file",
                input={"path": "config.py", "content": "VALUE = 1"},
            )
            calls = []
            handlers = {
                "write_file": lambda **kwargs: calls.append(
                    ("handler", kwargs)
                ) or "wrote"
            }
            lesson.plan_gates["alice"] = "approved"
            lesson.HOOKS["PreToolUse"] = [
                lambda seen: calls.append(("pre", seen.name)) or "denied"
            ]
            lesson.HOOKS["PostToolUse"] = [
                lambda seen, output: calls.append(
                    ("post", seen.name, output)
                )
            ]

            denied = lesson._run_teammate_tool("alice", block, handlers)
            self.assertEqual(denied, "denied")
            self.assertEqual(calls, [("pre", "write_file")])

            calls.clear()
            lesson.HOOKS["PreToolUse"] = [
                lambda seen: calls.append(("pre", seen.name))
            ]
            allowed = lesson._run_teammate_tool("alice", block, handlers)

            self.assertEqual(allowed, "wrote")
            self.assertEqual(
                calls,
                [
                    ("pre", "write_file"),
                    ("handler", block.input),
                    ("post", "write_file", "wrote"),
                ],
            )

    def test_s15_teammate_reads_shutdown_between_tool_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            entered = threading.Event()
            release = threading.Event()
            calls = []

            def create(**_kwargs):
                calls.append("llm")
                entered.set()
                release.wait(timeout=2)
                block = types.SimpleNamespace(
                    type="tool_use", id="tool_1", name="list_tasks", input={}
                )
                return types.SimpleNamespace(
                    stop_reason="tool_use", content=[block]
                )

            lesson.client.messages.create = create
            lesson.spawn_teammate_thread("alice", "reviewer", "Inspect tasks")
            self.assertTrue(entered.wait(timeout=2))
            lesson.run_request_shutdown("alice")
            release.set()

            self.assertTrue(
                wait_until(lambda: "alice" not in lesson.active_teammates)
            )
            self.assertEqual(calls, ["llm"])

    def test_normalized_mcp_tool_name_collisions_are_rejected(self):
        for lesson_path in MCP_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    first = lesson.MCPClient("docs.one")
                    first.register(
                        [{"name": "get.version", "inputSchema": {}}],
                        {"get.version": lambda: "one"},
                    )
                    second = lesson.MCPClient("docs_one")
                    second.register(
                        [{"name": "get_version", "inputSchema": {}}],
                        {"get_version": lambda: "two"},
                    )
                    lesson.mcp_clients.clear()
                    lesson.mcp_clients.update({
                        "docs.one": first,
                        "docs_one": second,
                    })

                    with self.assertRaisesRegex(
                        ValueError, "collision.*mcp__docs_one__get_version"
                    ):
                        lesson.assemble_tool_pool()

    def test_plan_rejection_requires_a_new_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.active_teammates["alice"] = "idle"

            self.assertIn("Plan requested",
                          lesson.run_request_plan("alice", "Refactor auth"))
            request = lesson.BUS.read_inbox("alice")
            self.assertEqual(request[0]["type"], "plan_request")
            self.assertEqual(lesson.plan_gates["alice"], "required")

            submission = lesson._teammate_submit_plan("alice", "1. Read\n2. Test")
            request_id = submission.split("(")[1].split(")")[0]
            self.assertEqual(lesson.pending_requests[request_id].status, "pending")

            result = lesson.run_review_plan(
                request_id, False, "Add a rollback step."
            )
            self.assertIn("rejected", result)
            self.assertEqual(lesson.plan_gates["alice"], "pending")

            responses = lesson.BUS.read_inbox("alice")
            accepted, _ = lesson.apply_plan_response("alice", responses[-1])
            self.assertTrue(accepted)
            self.assertEqual(lesson.plan_gates["alice"], "rejected")

            second = lesson._teammate_submit_plan(
                "alice", "1. Read\n2. Change\n3. Test\n4. Roll back on failure"
            )
            second_id = second.split("(")[1].split(")")[0]
            self.assertNotEqual(second_id, request_id)
            self.assertEqual(lesson.pending_requests[second_id].status, "pending")

    def test_mismatched_plan_response_cannot_release_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.active_teammates["alice"] = "waiting_approval"
            submission = lesson._teammate_submit_plan("alice", "1. Read\n2. Test")
            request_id = submission.split("(")[1].split(")")[0]

            forged = {
                "from": "lead",
                "to": "alice",
                "type": "plan_approval_response",
                "content": "Approved",
                "metadata": {"request_id": "req_stale", "approve": True},
            }
            accepted, notice = lesson.apply_plan_response("alice", forged)

            self.assertFalse(accepted)
            self.assertIn("Ignored", notice)
            self.assertEqual(lesson.plan_gates["alice"], "pending")
            self.assertEqual(lesson.plan_request_ids["alice"], request_id)

            current_but_unreviewed = {
                **forged,
                "metadata": {"request_id": request_id, "approve": True},
            }
            accepted, _ = lesson.apply_plan_response(
                "alice", current_but_unreviewed
            )
            self.assertFalse(accepted)
            self.assertEqual(lesson.plan_gates["alice"], "pending")

    def test_shutdown_response_must_come_from_requested_teammate(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.active_teammates.update({"alice": "idle", "bob": "idle"})
            result = lesson.run_request_shutdown("alice")
            request_id = result.split("(")[1].split(")")[0]

            lesson.BUS.send(
                "bob", "lead", "Shutdown acknowledged.",
                "shutdown_response",
                {"request_id": request_id, "approve": True},
            )
            lesson.consume_lead_inbox()

            self.assertEqual(
                lesson.pending_requests[request_id].status, "pending"
            )

    def test_shutdown_request_must_match_active_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.active_teammates["alice"] = "idle"
            forged = {
                "from": "lead",
                "to": "alice",
                "type": "shutdown_request",
                "content": "Shut down.",
                "metadata": {"request_id": "req_unknown"},
            }

            accepted, notice = lesson.apply_shutdown_request("alice", forged)
            self.assertFalse(accepted)
            self.assertIn("Ignored", notice)
            self.assertEqual(lesson.active_teammates["alice"], "idle")

            result = lesson.run_request_shutdown("alice")
            request_id = result.split("(")[1].split(")")[0]
            request = lesson.BUS.read_inbox("alice")[-1]
            accepted, matched_id = lesson.apply_shutdown_request(
                "alice", request
            )

            self.assertTrue(accepted)
            self.assertEqual(matched_id, request_id)
            self.assertEqual(lesson.active_teammates["alice"], "stopping")
            replayed, _ = lesson.apply_shutdown_request("alice", request)
            self.assertFalse(replayed)

    def test_teammate_emits_result_then_idle_and_shuts_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            lesson.IDLE_SCAN_INTERVAL = 5.0
            pending = lesson.create_task("Do not claim before mailbox delivery")
            seen_tools = set()

            def respond(**kwargs):
                seen_tools.update(tool["name"] for tool in kwargs["tools"])
                return types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(
                        type="text", text="Task complete."
                    )],
                )

            lesson.client.messages.create = respond

            lesson.spawn_teammate_thread("alice", "backend", "Inspect auth.")
            lead_inbox = lesson.MAILBOX_DIR / "lead.jsonl"
            self.assertTrue(wait_until(
                lambda: (
                    lead_inbox.exists()
                    and len(lead_inbox.read_text().splitlines()) >= 2
                )
            ))
            events = lesson.consume_lead_inbox()

            self.assertEqual(
                [event["type"] for event in events],
                ["result", "idle_notification"],
            )
            self.assertEqual(lesson.active_teammates["alice"], "idle")
            self.assertTrue(
                {"list_tasks", "claim_task", "complete_task"}
                .issubset(seen_tools)
            )
            self.assertTrue(
                {"create_worktree", "remove_worktree", "keep_worktree"}
                .isdisjoint(seen_tools)
            )

            lesson.run_request_shutdown("alice")
            self.assertTrue(
                wait_until(lambda: "alice" not in lesson.active_teammates)
            )
            shutdown_events = lesson.consume_lead_inbox()
            self.assertEqual(shutdown_events[-1]["type"], "shutdown_response")
            request_id = shutdown_events[-1]["metadata"]["request_id"]
            self.assertEqual(
                lesson.pending_requests[request_id].status, "approved"
            )
            self.assertEqual(lesson.load_task(pending.id).status, "pending")

    def test_downstream_teammates_continue_past_ten_tool_rounds(self):
        for lesson_path in DOWNSTREAM_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    lesson.IDLE_SCAN_INTERVAL = 5.0
                    calls = 0

                    def respond(**kwargs):
                        nonlocal calls
                        calls += 1
                        if calls <= 11:
                            return types.SimpleNamespace(
                                stop_reason="tool_use",
                                content=[types.SimpleNamespace(
                                    type="tool_use",
                                    name="list_tasks",
                                    id=f"list-{calls}",
                                    input={},
                                )],
                            )
                        return types.SimpleNamespace(
                            stop_reason="end_turn",
                            content=[types.SimpleNamespace(
                                type="text", text="Long task complete."
                            )],
                        )

                    lesson.client.messages.create = respond
                    lesson.spawn_teammate_thread(
                        "alice", "backend", "Use more than ten tool rounds."
                    )
                    lead_inbox = lesson.MAILBOX_DIR / "lead.jsonl"
                    self.assertTrue(wait_until(
                        lambda: (
                            lead_inbox.exists()
                            and len(lead_inbox.read_text().splitlines()) >= 2
                        ),
                        timeout=3.0,
                    ))
                    events = lesson.consume_lead_inbox()

                    self.assertEqual(calls, 12)
                    self.assertEqual(
                        [event["type"] for event in events],
                        ["result", "idle_notification"],
                    )
                    self.assertEqual(
                        lesson.active_teammates.get("alice"), "idle"
                    )
                    lesson.run_request_shutdown("alice")
                    self.assertTrue(wait_until(
                        lambda: "alice" not in lesson.active_teammates
                    ))

    def test_teammate_exception_releases_runtime_and_task_ownership(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    task = lesson.create_task("Implement auth")
                    calls = 0

                    def respond(**kwargs):
                        nonlocal calls
                        calls += 1
                        tool_name = "claim_task" if calls == 1 else "list_tasks"
                        tool_input = {"task_id": task.id} if calls == 1 else {}
                        return types.SimpleNamespace(
                            stop_reason="tool_use",
                            content=[types.SimpleNamespace(
                                type="tool_use", name=tool_name,
                                id=f"tool-{calls}", input=tool_input,
                            )],
                        )

                    original_dispatch = lesson._run_teammate_tool

                    def crash_after_claim(name, block, handlers):
                        if block.name == "list_tasks":
                            raise RuntimeError("simulated dispatch failure")
                        return original_dispatch(name, block, handlers)

                    lesson.client.messages.create = respond
                    lesson._run_teammate_tool = crash_after_claim
                    lesson.spawn_teammate_thread(
                        "alice", "backend", "Claim and begin work."
                    )

                    self.assertTrue(wait_until(
                        lambda: "alice" not in lesson.active_teammates
                    ))
                    self.assertNotIn("alice", lesson.teammate_assignments)
                    recovered = lesson.load_task(task.id)
                    self.assertEqual(recovered.status, "pending")
                    self.assertIsNone(recovered.owner)
                    events = lesson.consume_lead_inbox()
                    self.assertEqual([event["type"] for event in events], ["error"])
                    self.assertIn("simulated dispatch failure", events[0]["content"])

    def test_s15_completed_background_task_wakes_the_agent_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            seen_messages = []

            def respond(messages, context, tools, state, max_tokens):
                seen_messages.append(list(messages))
                return types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(
                        type="text", text="Background result handled."
                    )],
                )

            lesson.call_llm = respond
            lesson.background_tasks["bg_0001"] = {
                "tool_use_id": "tool-1",
                "command": "pytest",
                "status": "completed",
            }
            lesson.background_results["bg_0001"] = "all tests passed"
            history = []
            context = {}
            session_state = {"active_user_request": "Run tests"}
            threading.Thread(
                target=lesson.async_event_loop,
                args=(history, context, session_state),
                daemon=True,
            ).start()

            self.assertTrue(wait_until(lambda: bool(seen_messages), timeout=3.0))
            delivered = str(seen_messages[0])
            self.assertIn("<task_notification>", delivered)
            self.assertIn("all tests passed", delivered)
            self.assertFalse(lesson.has_pending_background())
            calls_after_delivery = len(seen_messages)
            time.sleep(1.2)
            self.assertEqual(len(seen_messages), calls_after_delivery)

    def test_s15_background_results_have_one_atomic_consumer(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )

            class CoordinatedLock:
                def __init__(self):
                    self.lock = threading.Lock()
                    self.barrier = threading.Barrier(2)
                    self.local = threading.local()

                def __enter__(self):
                    self.lock.acquire()
                    return self

                def __exit__(self, exc_type, exc_value, traceback):
                    self.lock.release()
                    if not getattr(self.local, "coordinated", False):
                        self.local.coordinated = True
                        self.barrier.wait(timeout=2.0)

            lesson.background_tasks["bg_0001"] = {
                "tool_use_id": "tool-1",
                "command": "pytest",
                "status": "completed",
            }
            lesson.background_results["bg_0001"] = "all tests passed"
            lesson.background_lock = CoordinatedLock()

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(
                    lambda _: lesson.collect_background_results(), range(2)
                ))

            notifications = [note for batch in results for note in batch]
            self.assertEqual(len(notifications), 1)
            self.assertIn("all tests passed", notifications[0])
            self.assertFalse(lesson.background_tasks)
            self.assertFalse(lesson.background_results)

    def test_s15_background_ids_are_allocated_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )

            class TrackingLock:
                def __init__(self):
                    self.lock = threading.Lock()
                    self.owner = None

                def __enter__(self):
                    self.lock.acquire()
                    self.owner = threading.get_ident()
                    return self

                def __exit__(self, exc_type, exc_value, traceback):
                    self.owner = None
                    self.lock.release()

                def held_by_current_thread(self):
                    return self.owner == threading.get_ident()

            class RaceAwareCounter:
                def __init__(self, lock):
                    self.lock = lock
                    self.barrier = threading.Barrier(2)

                def __add__(self, value):
                    if not self.lock.held_by_current_thread():
                        self.barrier.wait(timeout=2.0)
                    return 1

            blocks = [
                types.SimpleNamespace(
                    id=f"tool-{index}",
                    name="bash",
                    input={"command": f"printf {index}",
                           "run_in_background": True},
                )
                for index in (1, 2)
            ]
            lock = TrackingLock()
            lesson.background_lock = lock
            lesson._bg_counter = RaceAwareCounter(lock)
            lesson._run_bash_process = lambda *args, **kwargs: ("ok", 0)
            with ThreadPoolExecutor(max_workers=2) as executor:
                task_ids = list(executor.map(
                    lambda block: lesson.start_background_task(block, {}),
                    blocks,
                ))

            self.assertCountEqual(task_ids, ["bg_0001", "bg_0002"])
            self.assertEqual(set(lesson.background_tasks),
                             {"bg_0001", "bg_0002"})

    def test_s15_background_hook_failure_reaches_terminal_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            block = types.SimpleNamespace(
                id="tool-hook",
                name="bash",
                input={"command": "printf ok", "run_in_background": True},
            )
            lesson._run_bash_process = lambda *args, **kwargs: ("ok", 0)

            def fail_post_hook(event, *args):
                if event == "PostToolUse":
                    raise RuntimeError("hook failed")

            lesson.trigger_hooks = fail_post_hook
            bg_id = lesson.start_background_task(block, {})

            self.assertTrue(wait_until(
                lambda: lesson.background_tasks[bg_id]["status"] != "running"
            ))
            self.assertEqual(lesson.background_tasks[bg_id]["status"], "failed")
            self.assertIn("PostToolUse hook failed",
                          lesson.background_results[bg_id])
            notification = lesson.collect_background_results()[0]
            self.assertIn("<status>failed</status>", notification)
            self.assertIn("PostToolUse hook failed", notification)

    def test_s15_background_thread_start_failure_rolls_back_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            block = types.SimpleNamespace(
                id="tool-start",
                name="bash",
                input={"command": "printf ok", "run_in_background": True},
            )

            class FailingThread:
                def __init__(self, *args, **kwargs):
                    pass

                def start(self):
                    raise RuntimeError("cannot start thread")

            with patch.object(lesson.threading, "Thread", FailingThread):
                with self.assertRaisesRegex(RuntimeError, "cannot start thread"):
                    lesson.start_background_task(block, {})

            self.assertFalse(lesson.background_tasks)
            self.assertFalse(lesson.background_results)

    def test_s15_background_start_failure_becomes_tool_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(
                Path(tmp), ROOT / "s15_integrated_harness" / "code.py"
            )
            block = types.SimpleNamespace(
                type="tool_use",
                id="tool-start",
                name="bash",
                input={"command": "printf ok", "run_in_background": True},
            )
            responses = iter([
                types.SimpleNamespace(
                    stop_reason="tool_use",
                    content=[block],
                ),
                types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(type="text", text="done")],
                ),
            ])
            lesson.call_llm = lambda *args, **kwargs: next(responses)
            lesson.trigger_hooks = lambda *args, **kwargs: None
            lesson.remember_after_turn = lambda messages: None

            def fail_start(*args, **kwargs):
                raise RuntimeError("cannot start thread")

            lesson.start_background_task = fail_start
            messages = []
            lesson.agent_loop(messages, {}, "run in background")

            tool_results = [
                item
                for message in messages
                if message.get("role") == "user"
                and isinstance(message.get("content"), list)
                for item in message["content"]
                if item.get("type") == "tool_result"
            ]
            self.assertEqual(len(tool_results), 1)
            self.assertIn("Failed to start background task",
                          tool_results[0]["content"])
            self.assertIn("cannot start thread", tool_results[0]["content"])

    def test_teammate_survives_stale_worktree_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            lesson.IDLE_SCAN_INTERVAL = 5.0
            task = lesson.create_task("Implement auth")
            lesson.create_worktree("auth", task.id)
            worktree = lesson.WORKTREES_DIR / "auth"
            calls = 0
            bash_result = []

            def respond(**kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return types.SimpleNamespace(
                        stop_reason="tool_use",
                        content=[types.SimpleNamespace(
                            type="tool_use", name="claim_task", id="claim-1",
                            input={"task_id": task.id},
                        )],
                    )
                if calls == 2:
                    subprocess.run(
                        ["git", "worktree", "remove", "--force",
                         str(worktree)], cwd=root, check=True,
                    )
                    return types.SimpleNamespace(
                        stop_reason="tool_use",
                        content=[types.SimpleNamespace(
                            type="tool_use", name="bash", id="bash-1",
                            input={"command": "pwd"},
                        )],
                    )
                bash_result.append(
                    kwargs["messages"][-1]["content"][0]["content"]
                )
                return types.SimpleNamespace(
                    stop_reason="end_turn",
                    content=[types.SimpleNamespace(
                        type="text", text="Handled stale assignment."
                    )],
                )

            lesson.client.messages.create = respond
            lesson.spawn_teammate_thread("alice", "backend", "Claim the task.")

            self.assertTrue(wait_until(lambda: bool(bash_result)))
            self.assertIn("Invalid task assignment", bash_result[0])
            self.assertIn("alice", lesson.active_teammates)
            lesson.run_request_shutdown("alice")
            self.assertTrue(
                wait_until(lambda: "alice" not in lesson.active_teammates)
            )

    def test_idle_claim_is_atomic_across_teammates(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            task = lesson.create_task("Refactor auth")

            barrier = threading.Barrier(3)
            claimed = {}

            def claim(name):
                barrier.wait()
                claimed[name] = lesson.claim_next_task(name)

            threads = [
                threading.Thread(target=claim, args=(name,))
                for name in ("alice", "bob")
            ]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join(timeout=2)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(
                len([result for result in claimed.values() if result is not None]),
                1,
            )
            winner = next(result.owner for result in claimed.values()
                          if result is not None)
            self.assertEqual(lesson.load_task(task.id).owner, winner)

    def test_assignment_enforces_one_task_and_owner_only_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = load_lesson(Path(tmp))
            first = lesson.create_task("Refactor auth")
            second = lesson.create_task("Refactor login")

            self.assertIn("Claimed", lesson.claim_task(first.id, owner="alice"))
            denied = lesson.claim_task(second.id, owner="alice")
            self.assertIn("must finish", denied)
            self.assertEqual(lesson.load_task(second.id).status, "pending")

            denied = lesson.complete_task(first.id, owner="bob")
            self.assertIn("not bob", denied)
            self.assertEqual(lesson.load_task(first.id).status, "in_progress")

            self.assertIn(
                "Completed", lesson.complete_task(first.id, owner="alice")
            )
            self.assertIn("alice", lesson.teammate_assignments)
            denied = lesson.claim_task(second.id, owner="alice")
            self.assertIn("must finish", denied)
            self.assertTrue(lesson.release_completed_assignment("alice"))
            self.assertIn("Claimed", lesson.claim_task(second.id, owner="alice"))

    def test_completed_assignment_keeps_lead_in_worktree_until_turn_boundary(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    lesson = load_lesson(root, lesson_path)
                    first = lesson.create_task("Implement auth")
                    second = lesson.create_task("Update docs")
                    lesson.create_worktree("auth", first.id)

                    self.assertIn(
                        "Claimed", lesson.claim_task(first.id, owner="agent")
                    )
                    self.assertIn(
                        "Completed", lesson.complete_task(first.id, owner="agent")
                    )
                    self.assertIn(
                        "Wrote",
                        lesson.run_agent_write("after-complete.txt", "done"),
                    )
                    self.assertTrue(
                        (lesson.WORKTREES_DIR / "auth" / "after-complete.txt").exists()
                    )
                    self.assertFalse((root / "after-complete.txt").exists())
                    self.assertIn(
                        "must finish",
                        lesson.claim_task(second.id, owner="agent"),
                    )

                    self.assertTrue(lesson.release_completed_assignment("agent"))
                    self.assertIn(
                        "Claimed", lesson.claim_task(second.id, owner="agent")
                    )

    def test_in_progress_assignment_rehydrates_after_runtime_restart(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    lesson = load_lesson(root, lesson_path)
                    task = lesson.create_task("Implement auth")
                    lesson.create_worktree("auth", task.id)
                    lesson.claim_task(task.id, owner="alice")

                    lesson.teammate_assignments.clear()
                    recovered = lesson.assignment_cwd("alice")

                    self.assertEqual(
                        recovered.resolve(),
                        (lesson.WORKTREES_DIR / "auth").resolve(),
                    )
                    self.assertEqual(
                        lesson.teammate_assignments["alice"]["task_id"], task.id
                    )

    def test_completion_rehydrates_cwd_lease_before_status_change(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    lesson = load_lesson(root, lesson_path)
                    task = lesson.create_task("Implement auth")
                    lesson.create_worktree("auth", task.id)
                    lesson.claim_task(task.id, owner="agent")
                    lesson.teammate_assignments.clear()

                    self.assertIn(
                        "Completed", lesson.complete_task(task.id, owner="agent")
                    )
                    self.assertIn(
                        "Wrote", lesson.run_agent_write("after.txt", "done")
                    )
                    self.assertTrue(
                        (lesson.WORKTREES_DIR / "auth" / "after.txt").exists()
                    )
                    self.assertFalse((root / "after.txt").exists())

    def test_completion_replaces_a_stale_cross_runtime_cwd_lease(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    first = load_lesson(root, lesson_path)
                    old_task = first.create_task("Old assignment")
                    first.create_worktree("old", old_task.id)
                    first.claim_task(old_task.id, owner="agent")
                    first.complete_task(old_task.id, owner="agent")

                    second = load_lesson(root, lesson_path)
                    new_task = second.create_task("New assignment")
                    second.create_worktree("new", new_task.id)
                    second.claim_task(new_task.id, owner="agent")

                    self.assertIn(
                        "Completed",
                        first.complete_task(new_task.id, owner="agent"),
                    )
                    self.assertIn(
                        "Wrote", first.run_agent_write("after.txt", "done")
                    )
                    self.assertTrue(
                        (first.WORKTREES_DIR / "new" / "after.txt").exists()
                    )
                    self.assertFalse(
                        (first.WORKTREES_DIR / "old" / "after.txt").exists()
                    )

    def test_task_claim_is_atomic_across_processes(self):
        context = multiprocessing.get_context("spawn")
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    task = lesson.create_task("Only once")
                    barrier = context.Barrier(3)
                    results = context.Queue()

                    workers = [
                        context.Process(
                            target=claim_in_child,
                            args=(
                                str(lesson_path), tmp, task.id, owner,
                                barrier, results,
                            ),
                        )
                        for owner in ("alice", "bob")
                    ]
                    for worker in workers:
                        worker.start()
                    barrier.wait()
                    for worker in workers:
                        worker.join(5)
                        self.assertEqual(worker.exitcode, 0)
                    outcomes = [results.get(timeout=1) for _ in workers]

                    self.assertEqual(
                        sum(outcome.startswith("Claimed ") for outcome in outcomes),
                        1,
                    )
                    persisted = lesson.load_task(task.id)
                    self.assertEqual(persisted.status, "in_progress")
                    self.assertIn(persisted.owner, {"alice", "bob"})

    def test_dependency_updates_are_atomic_across_processes(self):
        context = multiprocessing.get_context("spawn")
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    first = lesson.create_task("First")
                    second = lesson.create_task("Second")
                    barrier = context.Barrier(3)
                    results = context.Queue()
                    workers = [
                        context.Process(
                            target=update_in_child,
                            args=(
                                str(lesson_path), tmp, task_id, dependency_id,
                                barrier, results,
                            ),
                        )
                        for task_id, dependency_id in (
                            (first.id, second.id),
                            (second.id, first.id),
                        )
                    ]

                    for worker in workers:
                        worker.start()
                    barrier.wait()
                    for worker in workers:
                        worker.join(5)
                        self.assertEqual(worker.exitcode, 0)
                    outcomes = [results.get(timeout=1) for _ in workers]

                    self.assertEqual(
                        sum(outcome.startswith("Updated ") for outcome in outcomes),
                        1,
                    )
                    self.assertEqual(
                        sum("Dependency cycle detected" in outcome
                            for outcome in outcomes),
                        1,
                    )
                    persisted = {
                        first.id: lesson.load_task(first.id).blockedBy,
                        second.id: lesson.load_task(second.id).blockedBy,
                    }
                    self.assertEqual(
                        sum(bool(value) for value in persisted.values()), 1
                    )

    def test_plan_approval_cannot_cross_assignment_boundary(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    lesson.active_teammates["alice"] = "working"
                    lesson.plan_gates["alice"] = "required"
                    lesson.assignment_versions["alice"] = 1
                    lesson._teammate_submit_plan("alice", "Inspect, edit, test")
                    request_id = next(iter(lesson.pending_requests))

                    lesson.advance_assignment_version("alice")
                    result = lesson.run_review_plan(request_id, True)

                    self.assertIn("earlier assignment", result)
                    self.assertNotEqual(lesson.plan_gates["alice"], "approved")

    def test_required_plan_is_active_before_teammate_thread_starts(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    tool_defs = getattr(lesson, "TOOLS", None)
                    if tool_defs is None:
                        tool_defs = lesson.BUILTIN_TOOLS
                    spawn_schema = next(
                        tool["input_schema"] for tool in tool_defs
                        if tool["name"] == "spawn_teammate"
                    )
                    self.assertIn("require_plan", spawn_schema["properties"])
                    with patch.object(
                        lesson.threading.Thread, "start", lambda _thread: None
                    ):
                        lesson.spawn_teammate_thread(
                            "alice", "backend", "Claim and edit.",
                            require_plan=True,
                        )
                    task = lesson.create_task("Edit auth")
                    self.assertIn("Claimed", lesson.claim_task(task.id, "alice"))
                    self.assertEqual(lesson.plan_gates["alice"], "required")
                    calls = []
                    block = types.SimpleNamespace(
                        name="write_file",
                        input={"path": "auth.py", "content": "changed"},
                    )
                    denied = lesson._run_teammate_tool(
                        "alice", block,
                        {"write_file": lambda **kw: calls.append(kw)},
                    )
                    self.assertIn("Blocked", denied)
                    self.assertEqual(calls, [])

    def test_worktree_registry_parsing_does_not_use_display_truncation(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    lesson = load_lesson(Path(tmp), lesson_path)
                    entries = []
                    for index in range(80):
                        path = Path(tmp) / ".worktrees" / (f"work-{index}-" + "x" * 80)
                        entries.append(
                            f"worktree {path}\nHEAD {'0' * 40}\n"
                            f"branch refs/heads/wt/work-{index}\n"
                        )
                    porcelain = "\n".join(entries)
                    self.assertGreater(len(porcelain), 5000)
                    lesson._run_git = lambda args, cwd=None: (True, porcelain)

                    registered, error = lesson._registered_worktrees()

                    self.assertIsNone(error)
                    self.assertEqual(len(registered), 80)

    def test_task_worktree_sets_assignment_cwd_and_contains_file_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")

            created = lesson.create_worktree("auth", task.id)
            self.assertIn("created", created)
            worktree = lesson.WORKTREES_DIR / "auth"
            self.assertEqual(lesson.load_task(task.id).worktree, "auth")

            self.assertIn("Claimed", lesson.claim_task(task.id, owner="alice"))
            assignment = lesson.teammate_assignments["alice"]
            self.assertEqual(assignment["task_id"], task.id)
            self.assertEqual(assignment["cwd"], worktree)
            self.assertIn(
                "Wrote", lesson.run_write(
                    "nested/result.txt", "done", cwd=lesson.assignment_cwd("alice")
                )
            )
            self.assertEqual((worktree / "nested" / "result.txt").read_text(),
                             "done")
            escaped = lesson.run_write(
                "../outside.txt", "bad", cwd=lesson.assignment_cwd("alice")
            )
            self.assertIn("escapes workspace", escaped)
            self.assertFalse((lesson.WORKTREES_DIR / "outside.txt").exists())
            missing_cwd = lesson.run_bash("pwd", cwd=worktree / "missing")
            self.assertIn("FileNotFoundError", missing_cwd)

    def test_invalid_or_unregistered_worktree_never_becomes_claimable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")

            invalid = lesson.create_worktree("../escape", task.id)
            self.assertIn("Error", invalid)
            self.assertIsNone(lesson.load_task(task.id).worktree)
            self.assertFalse((root / "escape").exists())

            missing = lesson.create_worktree("auth", "../missing")
            self.assertIn("Error", missing)
            self.assertFalse((lesson.WORKTREES_DIR / "auth").exists())

            bound = lesson.load_task(task.id)
            bound.worktree = "ghost"
            lesson.save_task(bound)
            denied = lesson.claim_task(task.id, owner="alice")
            self.assertIn("not registered", denied)
            self.assertEqual(lesson.load_task(task.id).status, "pending")
            self.assertEqual(lesson.scan_unclaimed_tasks(), [])

    def test_create_validates_branch_and_binds_only_after_git_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            subprocess.run(
                ["git", "branch", "wt/auth"], cwd=root, check=True
            )

            collision = lesson.create_worktree("auth", task.id)
            self.assertIn("already exists", collision)
            self.assertIsNone(lesson.load_task(task.id).worktree)
            self.assertFalse((lesson.WORKTREES_DIR / "auth").exists())

            original_run_git = lesson.run_git

            def fail_add(args, cwd=None):
                if args[:2] == ["worktree", "add"]:
                    return False, "simulated add failure"
                return original_run_git(args, cwd=cwd)

            lesson.run_git = fail_add
            failed = lesson.create_worktree("login", task.id)
            self.assertIn("simulated add failure", failed)
            self.assertIsNone(lesson.load_task(task.id).worktree)
            self.assertFalse((lesson.WORKTREES_DIR / "login").exists())

    def test_failed_git_add_reports_and_preserves_partial_artifacts(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    lesson = load_lesson(root, lesson_path)
                    task = lesson.create_task("Implement auth")
                    original_run_git = lesson.run_git

                    def fail_after_add(args, cwd=None):
                        if args[:2] == ["worktree", "add"]:
                            ok, output = original_run_git(args, cwd=cwd)
                            self.assertTrue(ok, output)
                            return False, "simulated late add failure"
                        return original_run_git(args, cwd=cwd)

                    lesson.run_git = fail_after_add
                    result = lesson.create_worktree("auth", task.id)

                    self.assertIn("Partial operation", result)
                    self.assertIn("simulated late add failure", result)
                    self.assertIn("remains unbound", result)
                    self.assertIn("git worktree list", result)
                    self.assertTrue((lesson.WORKTREES_DIR / "auth").is_dir())
                    self.assertIsNone(lesson.load_task(task.id).worktree)
                    branch = subprocess.run(
                        ["git", "show-ref", "--verify", "--quiet",
                         "refs/heads/wt/auth"],
                        cwd=root,
                    )
                    self.assertEqual(branch.returncode, 0)

    def test_binding_failure_retains_created_git_data_for_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            original_save_task = lesson.save_task

            def fail_binding(candidate):
                if candidate.worktree == "auth":
                    raise OSError("simulated task persistence failure")
                original_save_task(candidate)

            lesson.save_task = fail_binding
            result = lesson.create_worktree("auth", task.id)

            self.assertIn("Partial success", result)
            self.assertIn("manual recovery", result)
            self.assertTrue((lesson.WORKTREES_DIR / "auth").is_dir())
            self.assertIsNone(lesson.load_task(task.id).worktree)
            branch = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet",
                 "refs/heads/wt/auth"], cwd=root,
            )
            self.assertEqual(branch.returncode, 0)

    def test_remove_worktree_refuses_dirty_checkout_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            lesson.create_worktree("auth", task.id)
            lesson.claim_task(task.id, owner="alice")
            lesson.complete_task(task.id, owner="alice")
            lesson.release_completed_assignment("alice")
            worktree = lesson.WORKTREES_DIR / "auth"
            (worktree / "dirty.txt").write_text("unsaved\n")

            denied = lesson.remove_worktree("auth")

            self.assertIn("uncommitted", denied)
            self.assertTrue(worktree.exists())
            self.assertEqual(lesson.load_task(task.id).worktree, "auth")

    def test_remove_worktree_treats_ignored_files_as_uncommitted_data(self):
        for lesson_path in RUNTIME_LESSONS:
            with self.subTest(lesson=lesson_path.parent.name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_git_repo(root)
                    (root / ".gitignore").write_text("ignored.log\n")
                    subprocess.run(
                        ["git", "add", ".gitignore"], cwd=root, check=True
                    )
                    subprocess.run(
                        ["git", "commit", "-q", "-m", "ignore runtime log"],
                        cwd=root,
                        check=True,
                    )
                    lesson = load_lesson(root, lesson_path)
                    task = lesson.create_task("Implement auth")
                    lesson.create_worktree("auth", task.id)
                    lesson.claim_task(task.id, owner="alice")
                    lesson.complete_task(task.id, owner="alice")
                    lesson.release_completed_assignment("alice")
                    worktree = lesson.WORKTREES_DIR / "auth"
                    (worktree / "ignored.log").write_text("valuable output\n")

                    denied = lesson.remove_worktree("auth")

                    self.assertIn("uncommitted", denied)
                    self.assertTrue(worktree.exists())
                    self.assertEqual(lesson.load_task(task.id).worktree, "auth")
                    removed = lesson.remove_worktree(
                        "auth", discard_changes=True
                    )
                    self.assertIn("branch 'wt/auth' retained", removed)
                    self.assertFalse(worktree.exists())

    def test_discard_removes_checkout_but_retains_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            lesson.create_worktree("auth", task.id)
            lesson.claim_task(task.id, owner="alice")
            lesson.complete_task(task.id, owner="alice")
            lesson.release_completed_assignment("alice")
            worktree = lesson.WORKTREES_DIR / "auth"
            (worktree / "dirty.txt").write_text("discard me\n")

            removed = lesson.remove_worktree("auth", discard_changes=True)

            self.assertIn("branch 'wt/auth' retained", removed)
            self.assertFalse(worktree.exists())
            self.assertIsNone(lesson.load_task(task.id).worktree)
            branch = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet",
                 "refs/heads/wt/auth"], cwd=root,
            )
            self.assertEqual(branch.returncode, 0)

    def test_clean_local_commit_survives_non_force_checkout_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            lesson.create_worktree("auth", task.id)
            lesson.claim_task(task.id, owner="alice")
            lesson.complete_task(task.id, owner="alice")
            lesson.release_completed_assignment("alice")
            worktree = lesson.WORKTREES_DIR / "auth"
            (worktree / "feature.txt").write_text("committed work\n")
            subprocess.run(
                ["git", "add", "feature.txt"], cwd=worktree, check=True
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "feature"],
                cwd=worktree, check=True,
            )
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=worktree, text=True
            ).strip()
            upstream = subprocess.check_output(
                ["git", "for-each-ref", "--format=%(upstream)",
                 "refs/heads/wt/auth"], cwd=root, text=True,
            ).strip()
            self.assertEqual(upstream, "")

            removed = lesson.remove_worktree("auth")

            self.assertIn("branch 'wt/auth' retained", removed)
            self.assertFalse(worktree.exists())
            retained = subprocess.check_output(
                ["git", "rev-parse", "wt/auth"], cwd=root, text=True
            ).strip()
            self.assertEqual(retained, commit)

    def test_active_task_blocks_normal_and_discard_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            lesson = load_lesson(root)
            task = lesson.create_task("Implement auth")
            lesson.create_worktree("auth", task.id)
            worktree = lesson.WORKTREES_DIR / "auth"

            pending_normal = lesson.remove_worktree("auth")
            pending_discard = lesson.remove_worktree(
                "auth", discard_changes=True
            )
            self.assertIn("active task", pending_normal)
            self.assertIn("active task", pending_discard)

            lesson.claim_task(task.id, owner="alice")
            progress_normal = lesson.remove_worktree("auth")
            progress_discard = lesson.remove_worktree(
                "auth", discard_changes=True
            )

            self.assertIn("active task", progress_normal)
            self.assertIn("active task", progress_discard)
            self.assertTrue(worktree.exists())
            self.assertEqual(lesson.load_task(task.id).status, "in_progress")


if __name__ == "__main__":
    unittest.main()
