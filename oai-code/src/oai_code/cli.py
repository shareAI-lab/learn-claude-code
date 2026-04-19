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
from .tools.registry import ToolRegistry
from .tools.builtin import register_builtins
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
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--serial", action="store_true", help="force serial tool execution")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--version", action="version", version=f"oai-code {__version__}")
    return p


def _run_once(cfg, llm, registry, prompt_text: str) -> int:
    state = AgentState()
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
        )
    except Interrupted:
        print("\n[interrupted]", file=sys.stderr)
        return 130
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=False)
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    cfg = load_config(
        cli_overrides=_build_cli_overrides(args),
        extra_config_path=args.config,
    )
    if not cfg.model:
        print("oaic: model is required (set via --model or provider profile)", file=sys.stderr)
        return 2

    llm = LLMClient(cfg)
    registry = ToolRegistry(cfg)
    register_builtins(registry)
    todo_mgr = TodoManager()
    register_todo(registry, todo_mgr)

    if args.prompt:
        return _run_once(cfg, llm, registry, args.prompt)

    repl = Repl(cfg, llm, registry, todo_mgr)
    try:
        repl.run()
    except (KeyboardInterrupt, EOFError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
