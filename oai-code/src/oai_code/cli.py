"""oaic CLI 入口。

支持两种模式:
- 交互式 REPL: `oaic`
- 单次 prompt:  `oaic -p "帮我看看项目结构"`
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from dotenv import load_dotenv

from . import __version__
from .agent.loop import AgentState, Interrupted, LoopCallbacks, run_turn
from .config import load_config
from .llm.client import LLMClient
from .agent.system_prompt import build_system_prompt
from .context import auto_compact
from .mcp import MCPManager
from .session import SessionStore
from .team import MessageBus, TeammateManager
from .team.tools import register_team_tools
from .tools.registry import ToolRegistry
from .tools.ask_user import non_interactive_ask, register_ask_user
from .tools.background import BackgroundManager, register_background
from .tools.builtin import register_builtins
from .tools.compact_tool import register_compact
from .tools.plan_mode import PlanModeState, register_plan_mode
from .tools.skills import discover_skills, register_load_skill
from .tools.subagent import register_task_tool
from .tools.tasks import TaskStore, register_tasks
from .tools.todo import TodoManager, register_todo
from .ui.repl import Repl


def _build_cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if args.provider:
        d["provider"] = args.provider
    if args.model:
        d["model"] = args.model
    if args.base_url:
        d["base_url"] = args.base_url
    if args.no_stream:
        d.setdefault("ui", {})["stream"] = False
    if args.serial:
        d["serial_only"] = True
    return d


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oaic", description="OpenAI-compatible coding agent")
    p.add_argument("-p", "--prompt", help="run once with the given prompt and exit")
    p.add_argument("--provider", help="provider profile name")
    p.add_argument("--model", help="model id")
    p.add_argument("--base-url", help="override base_url")
    p.add_argument("--config", help="extra settings.json path")
    p.add_argument("--resume", help="resume a session by id, or 'latest'")
    p.add_argument("--list-sessions", action="store_true", help="list saved sessions and exit")
    p.add_argument("--no-save", action="store_true", help="do not persist this session to disk")
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--serial", action="store_true", help="force serial tool execution")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--version", action="version", version=f"oai-code {__version__}")
    return p


def _run_once(
    cfg,
    llm,
    registry,
    prompt_text: str,
    system_prompt: str | None = None,
    *,
    summarize_llm=None,
    pending_compact: dict | None = None,
    session_store=None,
    resumed_messages: list[dict] | None = None,
    background_manager=None,
    plan_state=None,
) -> int:
    state = AgentState()
    if resumed_messages:
        state.messages = list(resumed_messages)
        for m in state.messages:
            if m.get("role") == "system":
                state.system = m.get("content", "")
                break
    elif system_prompt:
        state.system = system_prompt
        state.messages.insert(0, {"role": "system", "content": system_prompt})
    if pending_compact is not None:
        pending_compact["state"] = state
    import sys as _sys

    def on_text(delta: str) -> None:
        _sys.stdout.write(delta)
        _sys.stdout.flush()

    def on_tool(c):  # noqa
        _sys.stderr.write(f"\n[tool] {c.name}\n")

    try:
        run_turn(
            state,
            prompt_text,
            cfg=cfg,
            llm=llm,
            registry=registry,
            callbacks=LoopCallbacks(on_text_delta=on_text, on_tool_call=on_tool),
            stream=cfg.ui.stream,
            summarize_llm=summarize_llm,
            background_manager=background_manager,
            plan_state=plan_state,
        )
    except Interrupted:
        print("\n[interrupted]", file=sys.stderr)
        if session_store is not None:
            session_store.append_new_messages(state.messages)
        return 130
    if session_store is not None:
        session_store.append_new_messages(state.messages)
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=False)
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    overrides = _build_cli_overrides(args)
    if args.no_save:
        overrides.setdefault("session", {})["auto_save"] = False
    cfg = load_config(
        cli_overrides=overrides,
        extra_config_path=args.config,
    )

    # --list-sessions 不需要 model,提前处理
    if args.list_sessions:
        store = SessionStore(cfg)
        ids = store.list_ids()
        if not ids:
            print("(no sessions)")
            return 0
        for sid in ids:
            s = store.summary(sid)
            first = s.get("first_user", "")
            print(f"{sid}  msgs={s['messages']:>4}  {first}")
        return 0

    if not cfg.model:
        print("oaic: model is required (set via --model or provider profile)", file=sys.stderr)
        return 2

    # main LLM 走 roles.main(未填则继承顶层)
    main_cfg = cfg.derive_for_role("main")
    llm = LLMClient(main_cfg)

    # summarize LLM 走 roles.summarize,用于 auto/manual compact
    summarize_cfg = cfg.derive_for_role("summarize")
    summarize_llm = LLMClient(summarize_cfg)

    # subagent LLM 走 roles.subagent
    subagent_cfg = cfg.derive_for_role("subagent")
    subagent_llm = LLMClient(subagent_cfg)

    registry = ToolRegistry(cfg)
    register_builtins(registry)
    todo_mgr = TodoManager()
    register_todo(registry, todo_mgr)
    task_store = TaskStore(cfg)
    register_tasks(registry, task_store)
    register_task_tool(registry, cfg=subagent_cfg, llm=subagent_llm)
    skills = discover_skills(cfg)
    register_load_skill(registry, skills)
    bg_manager = BackgroundManager(cfg)
    register_background(registry, bg_manager)

    # 多 Agent (M3): 仅在 team.enabled=true 时注册
    team_bus: MessageBus | None = None
    team_manager: TeammateManager | None = None
    if cfg.team.enabled:
        team_bus = MessageBus(cfg)
        team_manager = TeammateManager(cfg=cfg)
        register_team_tools(
            registry,
            cfg=subagent_cfg,
            llm=subagent_llm,
            bus=team_bus,
            manager=team_manager,
            parent_registry=registry,
            task_store=task_store,
            summarize_llm=summarize_llm,
        )

    # MCP (stdio only for M2): 启动 enabled 的 server,把它们的 tools 加入 registry
    mcp_manager: MCPManager | None = None
    if cfg.mcp_servers:
        mcp_manager = MCPManager(cfg)
        started = mcp_manager.start()
        if started:
            mcp_manager.register_into(registry)

    # 预先计算 system prompt,注入 skills 目录
    system_prompt = build_system_prompt(cfg, skills=skills)

    # Compact 工具的触发器 —— 闭包里绑定 agent state,REPL/run_once 各自注入
    pending_compact: dict[str, object] = {"state": None}

    def trigger_compact() -> str:
        state = pending_compact.get("state")
        if state is None:
            return "Error: no active conversation state"
        before = len(state.messages)
        state.messages = auto_compact(state.messages, cfg, summarize_llm)
        return f"Compacted: {before} → {len(state.messages)} messages"

    register_compact(registry, trigger_compact_fn=trigger_compact)

    # AskUserQuestion: 交互模式下由 Repl 注入实现;单次 / 管道模式 fallback 到非交互
    ask_holder = {"fn": non_interactive_ask}

    def _dispatch_ask(questions):
        return ask_holder["fn"](questions)

    register_ask_user(registry, ask_fn=_dispatch_ask)

    # Plan Mode: EnterPlanMode 设 flag, ExitPlanMode 通过 AskUserQuestion 要审批
    plan_state = PlanModeState()
    register_plan_mode(registry, state=plan_state, ask_fn=_dispatch_ask)

    # Session 持久化
    session_store = SessionStore(cfg)
    resumed_messages: list[dict] | None = None
    if args.resume:
        target = args.resume
        if target == "latest":
            latest = session_store.latest_id()
            if not latest:
                print("oaic: no sessions to resume", file=sys.stderr)
                return 2
            target = latest
        try:
            resumed_messages = session_store.load(target)
            print(f"[resumed session {target}: {len(resumed_messages)} messages]")
        except FileNotFoundError as e:
            print(f"oaic: {e}", file=sys.stderr)
            return 2
    else:
        session_store.new_session()

    if args.prompt:
        return _run_once(
            cfg, llm, registry, args.prompt, system_prompt,
            summarize_llm=summarize_llm, pending_compact=pending_compact,
            session_store=session_store, resumed_messages=resumed_messages,
            background_manager=bg_manager,
            plan_state=plan_state,
        )

    repl = Repl(
        cfg, llm, registry, todo_mgr, task_store, system_prompt,
        summarize_llm=summarize_llm, pending_compact=pending_compact,
        session_store=session_store, resumed_messages=resumed_messages,
        background_manager=bg_manager,
        mcp_manager=mcp_manager,
        team_manager=team_manager,
        team_bus=team_bus,
        ask_holder=ask_holder,
        plan_state=plan_state,
    )
    try:
        repl.run()
    except (KeyboardInterrupt, EOFError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
