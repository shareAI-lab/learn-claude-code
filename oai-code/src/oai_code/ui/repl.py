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
        todo_mgr=None,
        task_store=None,
        system_prompt: str | None = None,
        *,
        summarize_llm: LLMClient | None = None,
        pending_compact: dict | None = None,
        session_store=None,
        resumed_messages: list[dict] | None = None,
        background_manager=None,
    ):
        self.cfg = cfg
        self.llm = llm
        self.registry = registry
        self.todo_mgr = todo_mgr
        self.task_store = task_store
        self._system_prompt = system_prompt
        self._summarize_llm = summarize_llm
        self._pending_compact = pending_compact
        self._session_store = session_store
        self._resumed_messages = resumed_messages
        self._bg_manager = background_manager
        self.console = Console()
        self.state = self._new_state()
        if self._pending_compact is not None:
            self._pending_compact["state"] = self.state

        history_dir = cfg.workspace_root() / ".oaic"
        history_dir.mkdir(exist_ok=True)
        self.session = PromptSession(
            history=FileHistory(str(history_dir / "history"))
        )
        self._last_interrupt_ts: float = 0.0
        self._in_text_block = False

    def _new_state(self) -> AgentState:
        """新建带已算好 system prompt 的 AgentState,若有 resumed_messages 则恢复。"""
        s = AgentState()
        if self._resumed_messages:
            s.messages = list(self._resumed_messages)
            for m in s.messages:
                if m.get("role") == "system":
                    s.system = m.get("content", "")
                    break
            # 只在首次 new_state 时应用 resumed,后续 /clear 走空路径
            self._resumed_messages = None
            return s
        if self._system_prompt:
            s.system = self._system_prompt
            s.messages.append({"role": "system", "content": self._system_prompt})
        return s

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
                    summarize_llm=self._summarize_llm,
                    background_manager=self._bg_manager,
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
                # 每轮后落盘
                if self._session_store is not None:
                    self._session_store.append_new_messages(self.state.messages)

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
                "/help  /clear  /compact  /tools  /todos  /tasks  /bg [id]  "
                "/models [model-id]  /provider <name>  "
                "/sessions  /resume <id|latest>  "
                "/quit"
            )
        elif head == "/clear":
            self.state = self._new_state()
            if self._pending_compact is not None:
                self._pending_compact["state"] = self.state
            self.console.print("[dim]conversation cleared[/]")
        elif head == "/compact":
            if self._summarize_llm is None:
                self.console.print("[red]summarize_llm not configured[/]")
            else:
                from ..context import auto_compact

                before = len(self.state.messages)
                self.state.messages = auto_compact(
                    self.state.messages, self.cfg, self._summarize_llm
                )
                self.console.print(
                    f"[dim]compacted: {before} → {len(self.state.messages)} messages[/]"
                )
        elif head == "/todos":
            if self.todo_mgr is None:
                self.console.print("[dim](todo manager not available)[/]")
            else:
                self.console.print(self.todo_mgr.render())
        elif head == "/tasks":
            if self.task_store is None:
                self.console.print("[dim](task store not available)[/]")
            else:
                self.console.print(self.task_store.list_all())
        elif head == "/sessions":
            self._list_sessions()
        elif head == "/resume":
            if not arg:
                self.console.print("[red]usage: /resume <id|latest>[/]")
            else:
                self._do_resume(arg)
        elif head == "/bg":
            if self._bg_manager is None:
                self.console.print("[dim](no background manager)[/]")
            else:
                self.console.print(self._bg_manager.check(arg or None))
        elif head == "/models":
            if not arg:
                self._list_models()
            else:
                self._switch_model(arg)
        elif head == "/provider":
            if not arg:
                self.console.print(
                    "[red]usage: /provider <name>[/]  (see /models)"
                )
            else:
                self._switch_provider(arg)
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

    def _list_sessions(self) -> None:
        if self._session_store is None:
            self.console.print("[dim](session store not available)[/]")
            return
        ids = self._session_store.list_ids()
        if not ids:
            self.console.print("(no sessions)")
            return
        current = self._session_store.session_id
        for sid in ids[:20]:
            mark = "●" if sid == current else " "
            s = self._session_store.summary(sid)
            first = s.get("first_user", "") or "[empty]"
            self.console.print(
                f"  {mark} [cyan]{sid}[/]  msgs={s['messages']:>3}  [dim]{first}[/]"
            )
        if len(ids) > 20:
            self.console.print(f"[dim]... {len(ids) - 20} more[/]")

    def _do_resume(self, target: str) -> None:
        if self._session_store is None:
            self.console.print("[dim](session store not available)[/]")
            return
        if target == "latest":
            latest = self._session_store.latest_id()
            if not latest:
                self.console.print("[red]no sessions to resume[/]")
                return
            target = latest
        try:
            msgs = self._session_store.load(target)
        except FileNotFoundError as e:
            self.console.print(f"[red]{e}[/]")
            return
        self._resumed_messages = msgs
        self.state = self._new_state()
        if self._pending_compact is not None:
            self._pending_compact["state"] = self.state
        self.console.print(
            f"[green]✓[/] resumed [cyan]{target}[/]  [dim]({len(msgs)} messages)[/]"
        )

    def _list_models(self) -> None:
        from ..llm.providers import PROFILES

        rows = []
        for name, p in PROFILES.items():
            mark = "●" if name == self.cfg.provider else " "
            model = p.get("model") or "-"
            rows.append(f"  {mark} [cyan]{name:<14}[/] {model}")
        self.console.print(
            f"[bold]current[/]: provider=[cyan]{self.cfg.provider}[/] "
            f"model=[cyan]{self.cfg.model}[/]"
        )
        self.console.print("[bold]available providers[/]:")
        self.console.print("\n".join(rows))
        self.console.print(
            "[dim]tip: /models <model-id> to switch model; "
            "/provider <name> to switch profile[/]"
        )

    def _print_banner(self) -> None:
        self.console.print(
            f"[bold cyan]oai-code[/] "
            f"[dim]provider=[/][cyan]{self.cfg.provider}[/] "
            f"[dim]model=[/][cyan]{self.cfg.model}[/]  "
            f"[dim](/help for commands, Ctrl-D to quit)[/]"
        )
