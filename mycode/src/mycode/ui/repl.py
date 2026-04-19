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
        mcp_manager=None,
        team_manager=None,
        team_bus=None,
        ask_holder=None,
        plan_state=None,
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
        self._mcp_manager = mcp_manager
        self._team_manager = team_manager
        self._team_bus = team_bus
        if ask_holder is not None:
            ask_holder["fn"] = self._interactive_ask
        self._plan_state = plan_state
        self.console = Console()
        self.state = self._new_state()
        if self._pending_compact is not None:
            self._pending_compact["state"] = self.state

        history_dir = cfg.workspace_root() / ".mycode"
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
        # M5-4: 给每个进行中的 tool_call 记个开始时间,完成时显示耗时
        call_start: dict[str, float] = {}

        def on_text(delta: str) -> None:
            if not self._in_text_block:
                self.console.print("[bold green]assistant[/] ", end="")
                self._in_text_block = True
            self.console.print(delta, end="", highlight=False)

        def on_tool_call(c: ToolCall) -> None:
            if self._in_text_block:
                self.console.print()
                self._in_text_block = False
            call_start[c.id] = time.monotonic()
            args_preview = (
                json.dumps(c.arguments, ensure_ascii=False)[:120]
                if self.cfg.ui.show_tool_args
                else ""
            )
            self.console.print(
                f"[yellow]⚙[/] [bold]{c.name}[/] [dim]{args_preview}[/]"
            )

        def on_tool_result(c: ToolCall, r: ToolResult) -> None:
            elapsed = time.monotonic() - call_start.pop(c.id, time.monotonic())
            elapsed_str = (
                f"{int(elapsed * 1000)}ms" if elapsed < 1 else f"{elapsed:.1f}s"
            )
            is_error = r.content.startswith("Error:")
            icon = "[red]✗[/]" if is_error else "[green]✓[/]"
            self.console.print(
                f"  {icon} [dim]{c.name} · {elapsed_str}[/]"
            )
            # TodoWrite 特殊渲染:用 rich Table
            if c.name == "TodoWrite" and not is_error:
                self._render_todo_result(r.content)
                return
            snippet = r.content[:300].replace("\n", "\n    ")
            if is_error:
                self.console.print(f"    [red]{snippet}[/]")
            else:
                self.console.print(f"    [dim]{snippet}[/]")

        return LoopCallbacks(
            on_text_delta=on_text,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )

    def _render_todo_result(self, content: str) -> None:
        """把 TodoWrite 返回的纯文本清单用 rich 图标重绘。

        输入格式(见 tools/todo.py):
            [ ] pending item
            [>] in_progress item  <-- doing ...
            [x] completed item

            (N/M completed)
        """
        from rich.text import Text

        for raw in content.splitlines():
            stripped = raw.strip()
            if not stripped:
                self.console.print()
                continue
            if stripped.startswith("[ ]"):
                body = stripped[3:].lstrip()
                self.console.print(Text("  ○ ", style="dim") + Text(body))
            elif stripped.startswith("[>]"):
                body = stripped[3:].lstrip()
                self.console.print(Text("  ● ", style="yellow bold") + Text(body, style="bold"))
            elif stripped.startswith("[x]"):
                body = stripped[3:].lstrip()
                self.console.print(Text("  ✓ ", style="green") + Text(body, style="dim"))
            elif stripped.startswith("(") and "completed" in stripped:
                self.console.print(f"  [dim]{stripped}[/]")
            else:
                self.console.print(f"  [dim]{raw}[/]")

    # ---------- 主循环 ----------

    def run(self) -> None:
        self._print_banner()
        while True:
            try:
                user_input = self.session.prompt(
                    [("class:prompt", "mycode > ")], style=PROMPT_STYLE
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
                    plan_state=self._plan_state,
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
                "[bold]session[/]:      "
                "/sessions  /resume <id|latest>  /save  /clear  /compact"
            )
            self.console.print(
                "[bold]inspect[/]:      "
                "/tools  /todos  /tasks  /bg [id]  /mcp  /team  /inbox  "
                "/system  /history [N]  /debug"
            )
            self.console.print(
                "[bold]model[/]:        "
                "/models [model-id]  /provider <name>"
            )
            self.console.print(
                "[bold]other[/]:        "
                "/help  /quit [--summary]  /exit-summary"
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
        elif head == "/mcp":
            if self._mcp_manager is None:
                self.console.print("[dim](no mcp servers configured)[/]")
            else:
                self.console.print(self._mcp_manager.summary())
        elif head == "/team":
            if self._team_manager is None:
                self.console.print("[dim](team not enabled; set team.enabled=true)[/]")
            else:
                self.console.print(self._team_manager.render())
        elif head == "/plan":
            if self._plan_state is None:
                self.console.print("[dim](plan mode not available)[/]")
            else:
                status = "[yellow]ON[/]" if self._plan_state.active else "[dim]off[/]"
                self.console.print(f"plan mode: {status}")
        elif head == "/inbox":
            if self._team_bus is None:
                self.console.print("[dim](team not enabled)[/]")
            else:
                msgs = self._team_bus.read_inbox("lead")
                if not msgs:
                    self.console.print("(inbox empty)")
                else:
                    for m in msgs:
                        self.console.print(
                            f"[{m.get('type')}] from [cyan]{m.get('from')}[/]: "
                            f"{m.get('content', '')[:300]}"
                        )
        elif head == "/save":
            if self._session_store is None:
                self.console.print("[dim](no session store)[/]")
            else:
                n = self._session_store.append_new_messages(self.state.messages)
                self.console.print(
                    f"[green]✓[/] saved session [cyan]{self._session_store.session_id}[/] "
                    f"[dim]({n} new messages flushed)[/]"
                )
        elif head == "/debug":
            self._debug = not getattr(self, "_debug", False)
            self._print_debug_status()
        elif head == "/system":
            self._print_system()
        elif head == "/history":
            try:
                n = int(arg) if arg else 10
            except ValueError:
                n = 10
            self._print_history(n)
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
            if arg == "--summary":
                self._do_exit_summary()
            raise EOFError
        elif head == "/exit-summary":
            self._do_exit_summary()
            raise EOFError
        else:
            self.console.print(f"[red]unknown command: {head}[/]")
        return True

    def _do_exit_summary(self) -> None:
        if self._summarize_llm is None:
            self.console.print("[yellow]![/] summarize_llm not configured,skip")
            return
        from ..memory import summarize_to_memory

        self.console.print("[dim]generating exit summary to .mycode/MEMORY.md ...[/]")
        out = summarize_to_memory(self.state.messages, self.cfg, self._summarize_llm)
        self.console.print(f"[green]✓[/] {out}")

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

    def _interactive_ask(self, questions: list[dict]) -> list[dict]:
        """AskUserQuestion 工具在 REPL 模式下的实现:在 TUI 里等用户选数字。"""
        from prompt_toolkit.shortcuts import prompt as pt_prompt

        answers: list[dict] = []
        total = len(questions)
        for i, q in enumerate(questions, 1):
            self.console.print()
            header = f" [{q['header']}]" if q.get("header") else ""
            self.console.print(
                f"[bold yellow]?[/] [{i}/{total}]{header} [bold]{q['question']}[/]"
            )
            for idx, opt in enumerate(q["options"], 1):
                desc = f"  [dim]{opt['description']}[/]" if opt.get("description") else ""
                self.console.print(f"   [cyan]{idx}[/]) {opt['label']}{desc}")
            while True:
                raw = pt_prompt(f"your choice (1-{len(q['options'])}): ").strip()
                if raw.isdigit():
                    k = int(raw)
                    if 1 <= k <= len(q["options"]):
                        chosen = q["options"][k - 1]
                        answers.append(
                            {
                                "question": q["question"],
                                "header": q.get("header", ""),
                                "label": chosen["label"],
                                "description": chosen["description"],
                            }
                        )
                        break
                self.console.print("[red]invalid,请输入对应的数字[/]")
        return answers

    def _print_debug_status(self) -> None:
        from ..context import estimate_tokens

        on = getattr(self, "_debug", False)
        n_msgs = len(self.state.messages)
        tokens = estimate_tokens(self.state.messages)
        self.console.print(
            f"[bold]debug[/]: {'on' if on else 'off'}  "
            f"messages=[cyan]{n_msgs}[/]  "
            f"est_tokens=[cyan]{tokens}[/]  "
            f"ctx_limit=[cyan]{self.cfg.context_window}[/]"
        )

    def _print_system(self) -> None:
        sys_msgs = [m for m in self.state.messages if m.get("role") == "system"]
        if not sys_msgs:
            self.console.print("[dim](no system message)[/]")
            return
        content = sys_msgs[0].get("content", "") or ""
        preview = content[:2000]
        more = f"\n[dim]... ({len(content) - 2000} more chars)[/]" if len(content) > 2000 else ""
        self.console.print(f"[bold]system prompt[/] [dim]({len(content)} chars)[/]:")
        self.console.print(preview + more)

    def _print_history(self, n: int) -> None:
        if n <= 0:
            n = 10
        msgs = self.state.messages[-n:]
        if not msgs:
            self.console.print("[dim](no history)[/]")
            return
        for m in msgs:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, str):
                preview = content[:200].replace("\n", " ")
            else:
                preview = str(content)[:200]
            color = {"user": "green", "assistant": "cyan", "tool": "yellow", "system": "magenta"}.get(role, "white")
            extra = ""
            if m.get("tool_calls"):
                extra = f" [dim](+{len(m['tool_calls'])} tool_calls)[/]"
            self.console.print(f"[{color}]{role:>9}[/] {preview}{extra}")

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
            f"[bold cyan]mycode[/] "
            f"[dim]provider=[/][cyan]{self.cfg.provider}[/] "
            f"[dim]model=[/][cyan]{self.cfg.model}[/]  "
            f"[dim](/help for commands, Ctrl-D to quit)[/]"
        )
