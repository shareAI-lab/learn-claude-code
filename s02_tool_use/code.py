#!/usr/bin/env python3
# PyCharm debugger compatibility: this teaching file is named code.py, which
# can shadow Python's stdlib "code" module when pydevd imports it.
if __name__ == "code":
    import importlib.util as _importlib_util
    import sys as _sys
    import sysconfig as _sysconfig
    from pathlib import Path as _Path

    _stdlib_code = _Path(_sysconfig.get_paths()["stdlib"]) / "code.py"
    _spec = _importlib_util.spec_from_file_location("_stdlib_code", _stdlib_code)
    _module = _importlib_util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_module)
    globals().update({name: value for name, value in _module.__dict__.items()
                      if not name.startswith("__")})
else:
    """
    s02: Tool Use — 在 s01 基础上新增 5 个工具 + 分发映射。

    运行: python s02_tool_use/code.py
    需要: pip install anthropic python-dotenv + .env 中配置 ANTHROPIC_API_KEY

    本文件 = s01 的全部代码 + 以下新增:
      + run_read / run_write / run_edit / run_glob 四个工具实现
      + TOOL_HANDLERS 分发映射（替代 s01 中硬编码的 run_bash 调用）
      + safe_path 路径安全校验

    循环本身（agent_loop）与 s01 完全一致。
    """

    import os, subprocess, sys, faulthandler, traceback
    from pathlib import Path

    try:
        import readline
        readline.parse_and_bind('set bind-tty-special-chars off')
        readline.parse_and_bind('set input-meta on')
        readline.parse_and_bind('set output-meta on')
        readline.parse_and_bind('set convert-meta off')
    except ImportError:
        pass

    from anthropic import Anthropic
    from dotenv import load_dotenv

    load_dotenv(override=True)
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    WORKDIR = Path.cwd()
    client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
    MODEL = os.environ["MODEL_ID"]

    CHAPTER = Path(__file__).resolve().parent.name
    DEBUG = "--debug" in sys.argv or os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")
    DEBUG_BREAK = "--break" in sys.argv or os.getenv("DEBUG_BREAK", "").lower() in ("1", "true", "yes", "on")
    for _debug_arg in ("--debug", "--break"):
        while _debug_arg in sys.argv:
            sys.argv.remove(_debug_arg)


    def _debug_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except ValueError:
            return default


    TOOL_OUTPUT_PREVIEW = _debug_int("TOOL_OUTPUT_PREVIEW", 2000 if DEBUG else 300)


    def debug_setup():
        faulthandler.enable()

        def _excepthook(exc_type, exc, tb):
            print(f"\n[debug] unhandled {exc_type.__name__}: {exc}", file=sys.stderr)
            traceback.print_exception(exc_type, exc, tb)
            if DEBUG_BREAK:
                breakpoint()

        sys.excepthook = _excepthook
        if DEBUG:
            print(f"[debug] {CHAPTER}: cwd={WORKDIR} model={MODEL} preview={TOOL_OUTPUT_PREVIEW}")


    def debug_log(message: str):
        if DEBUG:
            print(f"\033[90m[debug] {message}\033[0m")


    def preview_output(output, limit: int | None = None) -> str:
        text = str(output)
        max_chars = TOOL_OUTPUT_PREVIEW if limit is None else limit
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        hidden = len(text) - max_chars
        return f"{text[:max_chars]}\n... ({hidden} more chars; set TOOL_OUTPUT_PREVIEW to see more)"


    def debug_tool_call(block):
        debug_log(f"tool={getattr(block, 'name', '?')} input={getattr(block, 'input', {})}")


    SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


    # ═══════════════════════════════════════════════════════════
    #  FROM s01 (unchanged)
    # ═══════════════════════════════════════════════════════════

    def run_bash(command: str) -> str:
        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            return "Error: Dangerous command blocked"
        try:
            r = subprocess.run(command, shell=True, cwd=WORKDIR,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (120s)"
        except (FileNotFoundError, OSError) as e:
            return f"Error: {e}"


    # ═══════════════════════════════════════════════════════════
    #  NEW in s02: 4 个新工具
    # ═══════════════════════════════════════════════════════════

    def safe_path(p: str) -> Path:
        path = (WORKDIR / p).resolve()
        if not path.is_relative_to(WORKDIR):
            raise ValueError(f"Path escapes workspace: {p}")
        return path


    def run_read(path: str, limit: int | None = None) -> str:
        try:
            lines = safe_path(path).read_text().splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"


    def run_write(path: str, content: str) -> str:
        try:
            file_path = safe_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error: {e}"


    def run_edit(path: str, old_text: str, new_text: str) -> str:
        try:
            file_path = safe_path(path)
            text = file_path.read_text()
            if old_text not in text:
                return f"Error: text not found in {path}"
            file_path.write_text(text.replace(old_text, new_text, 1))
            return f"Edited {path}"
        except Exception as e:
            return f"Error: {e}"


    def run_glob(pattern: str) -> str:
        import glob as g
        try:
            results = []
            for match in g.glob(pattern, root_dir=WORKDIR):
                if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                    results.append(match)
            return "\n".join(results) if results else "(no matches)"
        except Exception as e:
            return f"Error: {e}"


    def run_count_lines(path: str) -> str:
        try:
            file_path = safe_path(path)
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                count = sum(1 for _ in f)
            return f"{path}: {count} lines"
        except Exception as e:
            return f"Error: {e}"


    # ═══════════════════════════════════════════════════════════
    #  NEW in s02: 工具定义（s01 只有一个 bash，现在扩展到 6 个）
    # ═══════════════════════════════════════════════════════════

    TOOLS = [
        {"name": "bash", "description": "Run a shell command.",
         "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
        {"name": "read_file", "description": "Read file contents.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
        {"name": "write_file", "description": "Write content to a file.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
        {"name": "edit_file", "description": "Replace exact text in a file once.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
        {"name": "glob", "description": "Find files matching a glob pattern.",
         "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
        {"name": "count_lines", "description": "Count how many lines are in a text file.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to the file."}}, "required": ["path"]}},
    ]

    # ═══════════════════════════════════════════════════════════
    #  NEW in s02: 工具分发映射（s01 是硬编码 run_bash，现在改为查表）
    # ═══════════════════════════════════════════════════════════

    TOOL_HANDLERS = {
        "bash": run_bash, "read_file": run_read, "write_file": run_write,
        "edit_file": run_edit, "glob": run_glob, "count_lines": run_count_lines,
    }


    # ═══════════════════════════════════════════════════════════
    #  agent_loop — 与 s01 结构完全一致，只改了工具执行那部分
    #  s01: output = run_bash(block.input["command"])
    #  s02: output = TOOL_HANDLERS[block.name](**block.input)
    # ═══════════════════════════════════════════════════════════

    def agent_loop(messages: list):
        while True:
            response = client.messages.create(
                model=MODEL, system=SYSTEM, messages=messages,
                tools=TOOLS, max_tokens=8000,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return

            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\033[33m> {block.name}\033[0m")
                    debug_tool_call(block)
                    handler = TOOL_HANDLERS.get(block.name)
                    output = handler(**block.input) if handler else f"Unknown: {block.name}"
                    print(preview_output(output))
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

            messages.append({"role": "user", "content": results})


    if __name__ == "__main__":
        debug_setup()
        print("s02: Tool Use — 在 s01 基础上加了 4 个工具")
        print("输入问题，回车发送。输入 q 退出。\n")

        history = []
        while True:
            try:
                query = input("\033[36ms02 >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break
            if query.strip().lower() in ("q", "exit", ""):
                break
            history.append({"role": "user", "content": query})
            agent_loop(history)
            for block in history[-1]["content"]:
                if getattr(block, "type", None) == "text":
                    print(block.text)
            print()
