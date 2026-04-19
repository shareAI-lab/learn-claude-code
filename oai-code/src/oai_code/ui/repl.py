"""REPL: Rich 流式渲染 + prompt_toolkit 输入。"""
from __future__ import annotations

import json
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

from ..agent.dispatcher import ToolCall, ToolResult
from ..agent.loop import AgentState, Interrupted, LoopCallbacks, run_turn
from ..config.models import Config
from ..llm.client import LLMClient
from ..tools.registry import ToolRegistry


PROMPT_STYLE = Style.from_dict({"prompt": "ansicyan bold"})


class Repl:
    def __init__(
        self,
        cfg: Config,
        llm: LLMClient,
        registry: ToolRegistry,
    ):
        self.cfg = cfg
        self.llm = llm
        self.registry = registry
        self.console = Console()
        self.state = AgentState()

        history_dir = cfg.workspace_root() / ".oaic"
        history_dir.mkdir(exist_ok=True)
        self.session = PromptSession(
            history=FileHistory(str(history_dir / "history"))
        )
        self._last_interrupt_ts: float = 0.0
        self._in_text_block = False

    # ---------- Callback 渲染 ----------

    def _cb(self) -> LoopCallbacks:
        def on_text(delta: str) -> None:
            if not self._in_text_block:
                self.console.print("[bold green]assistant[/] ", end="")
                self._in_text_block = True
            self.console.print(delta, end="", highlight=False)

        def on_tool_call(c: ToolCall) -> None:
            if self._in_text_block:
                self.console.print()
                self._in_text_block = False
            args_preview = (
                json.dumps(c.arguments, ensure_ascii=False)[:120]
                if self.cfg.ui.show_tool_args
                else ""
            )
            self.console.print(
                f"[yellow]⏵ {c.name}[/] [dim]{args_preview}[/]"
            )

        def on_tool_result(c: ToolCall, r: ToolResult) -> None:
            snippet = r.content[:300].replace("\n", "\n    ")
            if r.content.startswith("Error:"):
                self.console.print(f"    [red]{snippet}[/]")
            else:
                self.console.print(f"    [dim]{snippet}[/]")

        return LoopCallbacks(
            on_text_delta=on_text,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )

    # ---------- 主循环 ----------

    def run(self) -> None:
        self._print_banner()
        while True:
            try:
                user_input = self.session.prompt(
                    [("class:prompt", "oaic > ")], style=PROMPT_STYLE
                )
            except EOFError:
                self.console.print("\n[dim]bye[/]")
                return
            except KeyboardInterrupt:
                if not self._double_ctrl_c():
                    continue
                self.console.print("\n[dim]bye[/]")
                return

            if not user_input.strip():
                continue
            if self._handle_slash(user_input.strip()):
                continue

            try:
                run_turn(
                    self.state,
                    user_input,
                    cfg=self.cfg,
                    llm=self.llm,
                    registry=self.registry,
                    callbacks=self._cb(),
                    stream=self.cfg.ui.stream,
                )
            except Interrupted:
                self.console.print("\n[yellow]⟂ interrupted[/]")
            except KeyboardInterrupt:
                if self._double_ctrl_c():
                    self.console.print("\n[dim]bye[/]")
                    return
            except Exception as e:
                self.console.print(f"[red]Error:[/] {type(e).__name__}: {e}")
            finally:
                if self._in_text_block:
                    self.console.print()
                    self._in_text_block = False

    # ---------- Helpers ----------

    def _double_ctrl_c(self) -> bool:
        now = time.monotonic()
        if now - self._last_interrupt_ts < 1.0:
            return True
        self._last_interrupt_ts = now
        self.console.print(
            "\n[dim](Ctrl-C again within 1s to exit)[/]"
        )
        return False

    def _handle_slash(self, cmd: str) -> bool:
        if not cmd.startswith("/"):
            return False
        parts = cmd.split(maxsplit=1)
        head = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""
        if head == "/help":
            self.console.print(
                "[bold]commands[/]: "
                "/help  /clear  /tools  "
                "/model [id]  /provider <name>  /models  "
                "/quit"
            )
        elif head == "/clear":
            self.state = AgentState()
            self.console.print("[dim]conversation cleared[/]")
        elif head == "/model":
            if not arg:
                self.console.print(
                    f"provider=[cyan]{self.cfg.provider}[/] model=[cyan]{self.cfg.model}[/]"
                )
            else:
                self._switch_model(arg)
        elif head == "/provider":
            if not arg:
                self.console.print(
                    "[red]usage: /provider <name>[/]  (see /models)"
                )
            else:
                self._switch_provider(arg)
        elif head == "/models":
            self._list_models()
        elif head == "/tools":
            self.console.print(
                "tools: " + ", ".join(self.registry.allowed_names())
            )
        elif head == "/quit" or head == "/exit":
            raise EOFError
        else:
            self.console.print(f"[red]unknown command: {head}[/]")
        return True

    # ---------- 运行时切换 ----------

    def _switch_model(self, model_id: str) -> None:
        """只换 model 字段,其他保留。"""
        self.cfg.model = model_id
        self.llm = LLMClient(self.cfg)
        self.console.print(
            f"[green]✓[/] model → [cyan]{self.cfg.model}[/] "
            f"[dim](provider={self.cfg.provider})[/]"
        )

    def _switch_provider(self, name: str) -> None:
        """切换到另一个 profile,base_url / model / api_key_env / default_query 一起换。"""
        from ..llm.providers import PROFILES, get_profile

        if name not in PROFILES:
            self.console.print(
                f"[red]unknown provider: {name}[/]  (available: {', '.join(PROFILES)})"
            )
            return
        profile = get_profile(name)
        self.cfg.provider = name
        for key in ("base_url", "model", "api_key_env", "default_query"):
            if profile.get(key) is not None:
                setattr(self.cfg, key, profile[key])
        if self.cfg.resolved_api_key() is None:
            self.console.print(
                f"[yellow]![/] warning: ${self.cfg.api_key_env} is empty"
            )
        self.llm = LLMClient(self.cfg)
        self.console.print(
            f"[green]✓[/] provider → [cyan]{self.cfg.provider}[/] "
            f"model=[cyan]{self.cfg.model}[/]"
        )

    def _list_models(self) -> None:
        from ..llm.providers import PROFILES

        rows = []
        for name, p in PROFILES.items():
            mark = "●" if name == self.cfg.provider else " "
            model = p.get("model") or "-"
            rows.append(f"  {mark} [cyan]{name:<14}[/] {model}")
        self.console.print("[bold]available providers[/]:")
        self.console.print("\n".join(rows))

    def _print_banner(self) -> None:
        self.console.print(
            f"[bold cyan]oai-code[/] "
            f"[dim]provider=[/][cyan]{self.cfg.provider}[/] "
            f"[dim]model=[/][cyan]{self.cfg.model}[/]  "
            f"[dim](/help for commands, Ctrl-D to quit)[/]"
        )
