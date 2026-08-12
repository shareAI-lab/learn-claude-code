"""Application composition root with no import-time runtime side effects."""

from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from homework.agent_app.adapters.anthropic import AnthropicAdapter
from homework.agent_app.config import AppConfig
from homework.agent_app.core.compaction import persist_large_output
from homework.agent_app.core.prompt import PromptBuilder
from homework.agent_app.core.recovery import RecoveryState, with_retry
from homework.agent_app.features import background, mcp, memory, scheduler, skills
from homework.agent_app.features import subagents, tasks, todos, worktrees
from homework.agent_app.features.teams import bus as team_bus
from homework.agent_app.features.teams import protocol as team_protocol
from homework.agent_app.features.teams import teammates
from homework.agent_app.runtime import RuntimeContext, SessionState
from homework.agent_app.tools import builtin
from homework.agent_app.tools.hooks import (
    HookRegistry,
    make_context_inject_hook,
    make_diff_preview_hook,
    make_large_output_hook,
    make_log_hook,
    make_permission_hook,
    make_summary_hook,
)
from homework.agent_app.tools.registry import ToolRegistry


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_GUARDED_TOOLS = {"bash", "write_file"}


def _create_storage_roots(config: AppConfig) -> None:
    for root in (
        config.memory_dir,
        config.transcripts_dir,
        config.tool_result_dir,
        config.task_dir,
        config.mailbox_dir,
        config.worktrees_dir,
        config.scheduled_tasks_path.parent,
    ):
        root.mkdir(parents=True, exist_ok=True)


def _run_git(config: AppConfig, args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=config.workdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output[:5000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return False, "Error: git timedout"


def _register_default_hooks(
    hooks: HookRegistry, config: AppConfig, mcp_state: mcp.MCPState
) -> None:
    hooks.register("UserPromptSubmit", make_context_inject_hook(config.workdir))
    hooks.register(
        "PreToolUse",
        make_permission_hook(config.workdir, input, mcp_state=mcp_state),
    )
    hooks.register("PreToolUse", make_log_hook(config.workdir))
    hooks.register("PreToolUse", make_diff_preview_hook(config.workdir, input))
    hooks.register("PostToolUse", make_large_output_hook(config.workdir))
    hooks.register("Stop", make_summary_hook(config.workdir))


def build_runtime(config: AppConfig, sdk_client) -> RuntimeContext:
    """Build one completely independent runtime from explicit dependencies."""
    _create_storage_roots(config)
    llm = AnthropicAdapter(sdk_client)

    session = SessionState()
    scheduler_state = scheduler.SchedulerState()
    background_state = background.BackgroundState()
    task_store = tasks.TaskStore(config.task_dir)
    skill_state = skills.SkillState(config.skills_dir)
    memory_store = memory.MemoryStore(config.memory_dir, config.memory_index)
    message_bus = team_bus.MessageBus(config.mailbox_dir)
    protocols = team_protocol.ProtocolStore()
    team_state = teammates.TeamState()
    mcp_state = mcp.MCPState()
    worktree_state = worktrees.WorktreeState(
        workdir=config.workdir,
        root=config.worktrees_dir,
        run_git=lambda args: _run_git(config, args),
    )
    skills.scan_skills(skill_state)

    hooks = HookRegistry()
    _register_default_hooks(hooks, config, mcp_state)
    registry = ToolRegistry()

    run_bash = lambda command, run_in_background=False, cwd=None: builtin.run_bash(
        config.workdir, command, run_in_background, cwd
    )
    run_read = lambda path, offset=0, limit=None, cwd=None: builtin.run_read(
        config.workdir, path, offset, limit, cwd
    )
    run_write = lambda path, content, cwd=None: builtin.run_write(
        config.workdir, path, content, cwd
    )
    run_edit = lambda path, old_text, new_text, cwd=None: builtin.run_edit(
        config.workdir, path, old_text, new_text, cwd
    )
    run_glob = lambda pattern, cwd=None: builtin.run_glob(
        config.workdir, pattern, cwd
    )
    builtin_handlers = {
        "bash": run_bash,
        "read_file": run_read,
        "write_file": run_write,
        "edit_file": run_edit,
        "glob": run_glob,
        "load_skill": lambda name: skills.load_skill(skill_state, name),
    }
    builtin.register_builtin_tools(registry, builtin_handlers)
    todos.register_todo_tools(registry, session)
    tasks.register_task_tools(registry, task_store)
    scheduler.register_scheduler_tools(registry, scheduler_state, config)

    def scan_unclaimed() -> list[dict]:
        return [
            asdict(task)
            for task in tasks.list_tasks(task_store)
            if task.status == "pending"
            and not task.owner
            and tasks.can_start(task_store, task.id)
        ]

    def wait_for_permission(
        agent: str, request_id: str, deferred_inbox: list[dict]
    ) -> dict:
        return team_protocol.wait_for_permission_response(
            message_bus,
            agent,
            request_id,
            deferred_inbox,
            clock=time.time,
            sleep=time.sleep,
            poll_interval=config.permission_poll_interval,
            timeout=config.permission_timeout,
        )

    def guarded_tool(agent, block, deferred_inbox, handler, cwd):
        request_id = uuid.uuid4().hex
        message_bus.send(
            agent,
            "lead",
            {
                "request_id": request_id,
                "tool_use_id": block.id,
                "tool_name": block.name,
                "tool_input": block.input,
                "cwd": str(cwd) if cwd else None,
            },
            msg_type="permission_request",
        )
        response = wait_for_permission(agent, request_id, deferred_inbox)
        if not response.get("approved"):
            return f"Permission denied: {response.get('reason', 'Permission denied')}", True
        return str(handler(**block.input)), False

    def collect_lead_inbox() -> list[dict]:
        return team_protocol.collect_lead_inbox(
            message_bus,
            protocols,
            hook=hooks.trigger,
            cwd_resolver=lambda cwd: builtin.resolve_tool_cwd(config.workdir, cwd),
            guarded_tools=TEAM_GUARDED_TOOLS,
            clock=time.time,
            sleep=time.sleep,
        )

    def format_inbox(messages: list[dict]) -> str:
        if not messages:
            return "(inbox empty)"
        return "\n".join(
            ["[Team inbox]"]
            + [f"From {item.get('from')}({item.get('type')}){item.get('content', '')}" for item in messages]
        )

    def spawn_teammate(name: str, role: str, prompt: str) -> str:
        recovery = RecoveryState(config.primary_model, config.fallback_model)

        def teammate_llm(**kwargs):
            return with_retry(
                lambda: llm.create(model=recovery.current_model, **kwargs),
                recovery,
                max_transient_retries=config.max_transient_retries,
                max_consecutive_529=config.max_consecutive_529,
                base_delay_ms=config.base_delay_ms,
            )

        teammate_handlers = {
            "bash": run_bash,
            "read_file": run_read,
            "write_file": run_write,
            "send_message": lambda to, content: (
                message_bus.send(name, to, content),
                "Sent",
            )[1],
            "submit_plan": lambda plan: team_protocol.submit_plan(
                message_bus, protocols, name, plan
            ),
            "list_tasks": lambda: tasks._run_list_tasks_tool(task_store),
            "claim_task": lambda task_id: tasks._run_task_operation(
                task_store, "claim", task_id, tasks.claim_task
            ),
            "complete_task": lambda task_id: tasks._run_task_operation(
                task_store, "complete", task_id, tasks.complete_task
            ),
        }

        def idle(*args):
            return teammates.idle_poll(
                message_bus,
                *args,
                scan_unclaimed=scan_unclaimed,
                claim_task=lambda task_id, owner: tasks.claim_task(
                    task_store, task_id, owner
                ),
                worktree_path=lambda name: config.worktrees_dir / name,
                sleep=time.sleep,
                poll_interval=config.idle_poll_interval,
                timeout=config.idle_timeout,
            )

        return teammates.spawn_teammate_thread(
            team_state,
            message_bus,
            teammate_llm,
            name=name,
            role=role,
            prompt=prompt,
            workdir=config.workdir,
            handlers=teammate_handlers,
            hooks=hooks,
            validate_name=team_bus.validate_agent_name,
            guarded_tools=TEAM_GUARDED_TOOLS,
            guarded_tool=guarded_tool,
            idle=idle,
            max_tokens=config.default_max_tokens,
            thread_factory=threading.Thread,
        )

    team_handlers = {
        "spawn_teammate": spawn_teammate,
        "send_message": lambda to, content: (
            message_bus.send("lead", to, content),
            f"Sent to {to}",
        )[1],
        "check_inbox": lambda: format_inbox(collect_lead_inbox()),
        "request_shutdown": lambda teammate: team_protocol.request_shutdown(
            message_bus, protocols, teammate
        ),
        "request_plan": lambda teammate, task: (
            message_bus.send(
                "lead", teammate, f"Please submit a plan for: {task}", "message"
            ),
            f"Asked {teammate} to submit a plan",
        )[1],
        "review_plan": lambda request_id, approve, feedback="": team_protocol.review_plan(
            message_bus, protocols, request_id, approve, feedback
        ),
    }
    teammates.register_team_tools(registry, team_handlers)
    worktrees.register_worktree_tools(registry, worktree_state, task_store)

    subagent_system = (
        f"You are a coding agent at {config.workdir}. "
        "Complete the task you were given, then return a concise summary. "
        "Do not delegate further."
    )
    subagent_tools = [
        schema
        for schema in builtin.BUILTIN_TOOL_SCHEMAS
        if schema["name"] in {"bash", "read_file", "write_file", "edit_file", "glob"}
    ]

    def spawn_subagent(description: str) -> str:
        recovery = RecoveryState(config.primary_model, config.fallback_model)

        def subagent_llm(**kwargs):
            return with_retry(
                lambda: llm.create(**kwargs),
                recovery,
                max_transient_retries=config.max_transient_retries,
                max_consecutive_529=config.max_consecutive_529,
                base_delay_ms=config.base_delay_ms,
            )

        return subagents.spawn_subagent(
            description,
            subagent_llm,
            config,
            subagent_system,
            subagent_tools,
            {name: builtin_handlers[name] for name in ("bash", "read_file", "write_file", "edit_file", "glob")},
            hooks,
        )

    subagents.register_subagent_tool(registry, spawn_subagent)
    mcp.register_mcp_connection_tool(registry, mcp_state)

    return RuntimeContext(
        config=config,
        llm=llm,
        session=session,
        prompt_builder=PromptBuilder(),
        tools=registry,
        hooks=hooks,
        scheduler=scheduler_state,
        background=background_state,
        tasks=task_store,
        worktrees=worktree_state,
        skills=skill_state,
        memory=memory_store,
        bus=message_bus,
        protocols=protocols,
        team=team_state,
        mcp=mcp_state,
    )


def build_default_runtime() -> RuntimeContext:
    """Load process configuration and construct the production SDK client."""
    from anthropic import Anthropic
    from dotenv import load_dotenv

    load_dotenv(override=True)
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    config = AppConfig.from_env(DEFAULT_REPO_ROOT)
    return build_runtime(config, Anthropic(base_url=base_url))
