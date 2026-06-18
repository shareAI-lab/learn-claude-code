"""
loop_agent.py — s20 封装层

直接调用 s20_comprehensive/code.py 的核心函数，提供简化的 chat、init_context、run_maker、run_checker 接口。
使用 _run_agent_with_tools 实现工具隔离，不修改全局状态。
"""

import sys
import re
import json
import subprocess
import functools
import importlib.util
from pathlib import Path
from dataclasses import dataclass

# 确保 s20 目录在 sys.path 中
from config import S20_DIR, WORKDIR, MAX_DIFF_LENGTH, MAX_TEST_OUTPUT_LENGTH, MAKER_MAX_TURNS, CHECKER_MAX_TURNS

# 使用 importlib 动态导入 s20 的 code.py，避免与标准库的 code 模块冲突
_spec = importlib.util.spec_from_file_location("s20_code", S20_DIR / "code.py")
_s20_code = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s20_code)

# 从 s20 导入核心函数
agent_loop = _s20_code.agent_loop
assemble_system_prompt = _s20_code.assemble_system_prompt
update_context = _s20_code.update_context
prepare_context = _s20_code.prepare_context
assemble_tool_pool = _s20_code.assemble_tool_pool
trigger_hooks = _s20_code.trigger_hooks
register_hook = _s20_code.register_hook
scan_skills = _s20_code.scan_skills
list_skills = _s20_code.list_skills
load_skill = _s20_code.load_skill
consume_cron_queue = _s20_code.consume_cron_queue
collect_background_results = _s20_code.collect_background_results
create_worktree = _s20_code.create_worktree

# 从 s20 导入底层函数，用于 _run_agent_with_tools
call_llm = _s20_code.call_llm
call_tool_handler = _s20_code.call_tool_handler
has_tool_use = _s20_code.has_tool_use
build_user_content = _s20_code.build_user_content
RecoveryState = _s20_code.RecoveryState
DEFAULT_MAX_TOKENS = _s20_code.DEFAULT_MAX_TOKENS
ESCALATED_MAX_TOKENS = _s20_code.ESCALATED_MAX_TOKENS
MAX_RECOVERY_RETRIES = _s20_code.MAX_RECOVERY_RETRIES
CONTINUATION_PROMPT = _s20_code.CONTINUATION_PROMPT
is_prompt_too_long_error = _s20_code.is_prompt_too_long_error
reactive_compact = _s20_code.reactive_compact


def _run_agent_with_tools(messages: list, context: dict, tools: list, handlers: dict, max_turns: int, token_budget: int = 0) -> int:
    """使用指定的工具集运行 agent loop（不修改全局状态）。

    与 s20 的 agent_loop 功能等价，但接受自定义 tools/handlers，
    且支持 max_turns 和 token_budget 限制。用于 Maker/Checker 工具隔离。

    Args:
        messages: 对话历史（会被原地修改）
        context: 上下文 dict
        tools: 工具 schema 列表
        handlers: 工具名→处理函数 dict
        max_turns: 最大轮次（每次 LLM 调用计为一轮）
        token_budget: token 预算上限（0 = 不限制）

    Returns:
        累计消耗的 token 数量
    """
    from config import TOKEN_BUDGET
    effective_budget = token_budget if token_budget > 0 else TOKEN_BUDGET

    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS
    turns = 0
    total_tokens = 0

    while turns < max_turns:
        # 准备上下文
        prepare_context(messages)
        context = update_context(context, messages)

        try:
            response = call_llm(messages, context, tools, state, max_tokens)
        except Exception as e:
            if is_prompt_too_long_error(e) and not state.has_attempted_reactive_compact:
                messages[:] = reactive_compact(messages)
                state.has_attempted_reactive_compact = True
                continue
            messages.append({"role": "assistant", "content": [
                {"type": "text", "text": f"[Error] {type(e).__name__}: {e}"}]})
            return total_tokens

        turns += 1

        # 跟踪 token 用量
        if hasattr(response, 'usage') and response.usage:
            turn_tokens = getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)
            total_tokens += turn_tokens
            if effective_budget > 0 and total_tokens >= effective_budget:
                messages.append({"role": "assistant", "content": [
                    {"type": "text", "text": f"[Budget] Token budget of {effective_budget} exceeded ({total_tokens} used). Stopping."}]})
                return total_tokens

        # 处理 max_tokens 重试
        if response.stop_reason == "max_tokens":
            if not state.has_escalated:
                max_tokens = ESCALATED_MAX_TOKENS
                state.has_escalated = True
                continue
            messages.append({"role": "assistant", "content": response.content})
            if state.recovery_count < MAX_RECOVERY_RETRIES:
                messages.append({"role": "user", "content": CONTINUATION_PROMPT})
                state.recovery_count += 1
                continue
            return total_tokens

        max_tokens = DEFAULT_MAX_TOKENS
        state.has_escalated = False
        messages.append({"role": "assistant", "content": response.content})

        # 无 tool_use → 对话结束
        if not has_tool_use(response.content):
            return total_tokens

        # 分发工具调用
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = handlers.get(block.name)
            output = call_tool_handler(handler, block.input, block.name)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": build_user_content(results)})

    return total_tokens

def _extract_last_assistant_text(messages: list) -> str:
    """从消息历史中提取最后一条 assistant 消息的文本。

    Args:
        messages: 对话历史列表

    Returns:
        最后一条 assistant 消息的文本内容，未找到则返回空字符串
    """
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content")
            if isinstance(content, list):
                texts = []
                for block in content:
                    if hasattr(block, "text"):
                        texts.append(block.text)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                if texts:
                    return "\n".join(texts)
            elif isinstance(content, str):
                return content
    return ""


@dataclass
class MakerResult:
    """Maker 子代理的执行结果。"""
    success: bool
    diff_stat: str
    test_output: str
    summary: str
    worktree_name: str
    tokens_used: int = 0


@dataclass
class CheckerResult:
    """Checker 子代理的审查结果。"""
    approved: bool
    feedback: str
    issues: list
    verdict: str = ""  # "APPROVED" | "REJECTED" | ""（解析失败时为空）
    tokens_used: int = 0


def chat(messages: list, context: dict) -> str:
    """
    调用 s20 的 agent_loop 执行对话。

    Args:
        messages: 对话历史
        context: 上下文信息

    Returns:
        最后一条 assistant 消息的文本
    """
    agent_loop(messages, context)
    return _extract_last_assistant_text(messages)


def init_context() -> dict:
    """
    初始化上下文信息。

    Returns:
        context dict，包含 memories、connected_mcp、active_teammates 等
    """
    # 扫描技能目录
    scan_skills()

    # 初始化上下文
    context = update_context({}, [])
    return context


def run_maker(task_description: str, branch_hint: str = "") -> MakerResult:
    """
    执行 Maker 子代理：在 worktree 中完成编码任务。

    Args:
        task_description: 任务描述
        branch_hint: 分支名称提示（可选）

    Returns:
        MakerResult 包含执行结果、diff、测试输出等
    """
    import time
    import random

    # 生成 worktree 名称
    if not branch_hint:
        branch_hint = f"maker_{int(time.time())}_{random.randint(0, 999):03d}"

    # 创建 worktree（s20 的 create_worktree 使用 cwd()/.worktrees）
    wt_result = create_worktree(branch_hint)
    if "Error" in wt_result or "error" in wt_result.lower():
        return MakerResult(
            success=False,
            diff_stat="",
            test_output="",
            summary=f"Failed to create worktree: {wt_result}",
            worktree_name="",
        )

    # 与 s20 的 WORKTREES_DIR 保持一致：cwd()/.worktrees/
    wt_path = _s20_code.WORKTREES_DIR / branch_hint

    if not wt_path.exists():
        return MakerResult(
            success=False,
            diff_stat="",
            test_output="",
            summary=f"Worktree directory does not exist after creation: {wt_path}",
            worktree_name="",
        )

    # 构建 maker 系统提示
    skills_catalog = list_skills()

    # 列出 worktree 中的文件结构，帮助 Maker 定位目标文件
    file_listing = ""
    try:
        ls_result = subprocess.run(
            ["git", "ls-files"],
            cwd=wt_path, capture_output=True, text=True, timeout=10,
        )
        if ls_result.returncode == 0:
            file_listing = ls_result.stdout.strip()
    except Exception:
        file_listing = "(could not list files)"

    system_prompt = f"""You are a Maker agent. Your task is to implement the following:

{task_description}

WORKING DIRECTORY: {wt_path}
You MUST read, edit, and write files relative to this directory. Do NOT create subdirectories for the project.

Existing files in the repository:
{file_listing}

Available skills:
{skills_catalog}

Instructions:
1. First, read the relevant files to understand the current code
2. Make targeted changes to fix bugs or add features
3. Run tests to verify your changes: python -m pytest <test_file> -v
4. When done, provide a summary of changes made

IMPORTANT: Edit existing files in place. Do NOT create new copies in subdirectories.
"""

    # 工具集：只保留基础读写工具，并注入 worktree 路径作为 cwd
    orig_tools = _s20_code.BUILTIN_TOOLS
    orig_handlers = _s20_code.BUILTIN_HANDLERS
    maker_tools = [t for t in orig_tools if t["name"] in (
        "bash", "read_file", "write_file", "edit_file", "glob")]
    maker_handlers = {
        k: functools.partial(v, cwd=wt_path)
        for k, v in orig_handlers.items()
        if k in ("bash", "read_file", "write_file", "edit_file", "glob")
    }

    # 执行 agent_loop（使用隔离工具集，不修改全局状态）
    messages = [{"role": "user", "content": f"Complete this task:\n{task_description}"}]
    context = init_context()
    tokens_used = 0

    try:
        tokens_used = _run_agent_with_tools(messages, context, maker_tools, maker_handlers, MAKER_MAX_TURNS)
    except Exception as e:
        return MakerResult(
            success=False,
            diff_stat="",
            test_output="",
            summary=f"Agent loop error: {e}",
            worktree_name=branch_hint,
        )

    # 收集 git diff --stat
    try:
        diff_result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=wt_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        diff_stat = diff_result.stdout.strip() if diff_result.returncode == 0 else "(no diff)"
    except Exception as e:
        diff_stat = f"(diff error: {e})"

    # 运行测试（如果有 pytest）
    test_output = ""
    try:
        test_result = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            cwd=wt_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        test_output = test_result.stdout + test_result.stderr
    except FileNotFoundError:
        test_output = "(pytest not available)"
    except subprocess.TimeoutExpired:
        test_output = "(test timeout)"
    except Exception as e:
        test_output = f"(test error: {e})"

    return MakerResult(
        success=True,
        diff_stat=diff_stat,
        test_output=test_output[:MAX_TEST_OUTPUT_LENGTH],
        summary=_extract_last_assistant_text(messages),
        worktree_name=branch_hint,
        tokens_used=tokens_used,
    )


def run_checker(maker_result: MakerResult) -> CheckerResult:
    """
    执行 Checker 子代理：审查 Maker 的代码变更。

    Checker 只有只读工具（bash 只读命令、read_file、glob），
    系统提示通过 context["memories"] 注入。

    Args:
        maker_result: Maker 的执行结果

    Returns:
        CheckerResult 包含审批状态和反馈
    """
    if not maker_result.success:
        return CheckerResult(
            approved=False,
            feedback=f"Maker failed: {maker_result.summary}",
            issues=["Maker execution failed"],
        )

    # ── 确定 worktree 路径（与 s20 的 WORKTREES_DIR 一致：cwd()/.worktrees/）──
    wt_path = _s20_code.WORKTREES_DIR / maker_result.worktree_name if maker_result.worktree_name else None

    # ── 准备 diff 内容 ─────────────────────────────────────
    diff_content = ""
    if wt_path and wt_path.exists():
        try:
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=wt_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            diff_content = diff_result.stdout[:MAX_DIFF_LENGTH] if diff_result.returncode == 0 else "(no diff)"
        except Exception:
            diff_content = "(diff unavailable)"

    # ── 只读 bash 包装 ─────────────────────────────────────
    _READ_ONLY_PREFIXES = (
        "git diff", "git log", "git show", "git status",
        "cat", "head", "tail", "grep", "find", "ls",
        "wc", "python -m pytest", "pytest", "mypy", "ruff",
    )
    _DANGEROUS_PREFIXES = ("rm", "mv", "cp", "chmod", "chown", "dd", "mkfs")

    def read_only_bash(command: str) -> str:
        """只允许只读命令，显式拒绝危险命令。"""
        import re as _re
        cmd_lower = command.lower().strip()

        # 分割链式命令（&&、||、;、|），逐一检查
        parts = _re.split(r'\s*(?:&&|\|\||;)\s*', cmd_lower)
        # 对管道命令，只检查第一个命令（管道是只读的合理操作）
        if not parts:
            parts = [cmd_lower]

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 检查危险命令前缀
            if any(part.startswith(p) for p in _DANGEROUS_PREFIXES):
                return f"Permission denied: dangerous command blocked: {command}"
            # 检查 find -exec 危险操作
            if "find" in part and "-exec" in part:
                exec_section = part.split("-exec", 1)[1].strip()
                if any(exec_section.lstrip().startswith(p) for p in _DANGEROUS_PREFIXES):
                    return f"Permission denied: dangerous find -exec blocked: {command}"

        # 取第一个命令判断是否在白名单
        first_cmd = parts[0].strip()
        if any(first_cmd.startswith(p) for p in _READ_ONLY_PREFIXES):
            return _s20_code.run_bash(command, cwd=wt_path)
        return f"Permission denied: read-only mode. Command not allowed: {command}"

    # ── 构建只读工具集（注入 worktree cwd）─────────────────
    checker_tools = [
        {"name": "bash", "description": "Run a read-only shell command.",
         "input_schema": {"type": "object",
                          "properties": {"command": {"type": "string"}},
                          "required": ["command"]}},
        {"name": "read_file", "description": "Read file contents.",
         "input_schema": {"type": "object",
                          "properties": {"path": {"type": "string"},
                                         "limit": {"type": "integer"},
                                         "offset": {"type": "integer"}},
                          "required": ["path"]}},
        {"name": "glob", "description": "Find files matching a glob pattern.",
         "input_schema": {"type": "object",
                          "properties": {"pattern": {"type": "string"}},
                          "required": ["pattern"]}},
    ]
    checker_handlers = {
        "bash": read_only_bash,
        "read_file": functools.partial(_s20_code.run_read, cwd=wt_path),
        "glob": functools.partial(_s20_code.run_glob, cwd=wt_path),
    }

    # ── 注入系统提示到 context memories ─────────────────────
    system_prompt = (
        "You are a Checker agent. Your job is to review code changes made by a Maker agent.\n\n"
        f"Maker's summary:\n{maker_result.summary}\n\n"
        f"Git diff stat:\n{maker_result.diff_stat}\n\n"
        f"Test output:\n{maker_result.test_output}\n\n"
        "Your job:\n"
        "1. Review the changes for correctness, style, and potential issues\n"
        "2. Check if tests pass\n"
        "3. Look for bugs, security issues, or performance problems\n\n"
        "You MUST respond with a JSON object on the LAST line of your response, in this exact format:\n"
        '{"verdict": "APPROVED", "issues": [], "summary": "Brief explanation"}\n'
        'or\n'
        '{"verdict": "REJECTED", "issues": ["Issue 1 description", "Issue 2 description"], "summary": "Brief explanation"}\n\n'
        "The verdict field must be exactly \"APPROVED\" or \"REJECTED\".\n"
        "The issues field must be a JSON array of strings (empty if approved).\n"
        "The summary field is a brief explanation of your decision.\n"
        "You may include analysis text BEFORE the JSON line, but the JSON must be the last line.\n\n"
        "Be thorough but fair. Focus on real problems, not style preferences."
    )

    # ── 执行审查（临时替换工具集 + 注入角色提示）────────────
    messages = [
        {"role": "user", "content": f"Review these changes:\n\n{diff_content}"}
    ]
    context = init_context()
    context["memories"] = [{"name": "checker-role", "content": system_prompt}]

    # 使用隔离工具集运行 checker，不修改全局状态
    tokens_used = 0
    try:
        tokens_used = _run_agent_with_tools(messages, context, checker_tools, checker_handlers, CHECKER_MAX_TURNS)
    except Exception as e:
        return CheckerResult(
            approved=False,
            feedback=f"Checker error: {e}",
            issues=["Checker execution failed"],
        )

    # ── 解析输出（JSON 优先，fallback 到子串匹配）────────────
    checker_output = _extract_last_assistant_text(messages)
    approved = False
    verdict = ""
    issues = []

    # 尝试从输出中提取 JSON
    json_match = re.search(r'\{[^{}]*\}', checker_output, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            verdict = parsed.get("verdict", "").upper()
            if verdict in ("APPROVED", "REJECTED"):
                approved = verdict == "APPROVED"
                raw_issues = parsed.get("issues", [])
                if isinstance(raw_issues, list):
                    issues = [str(i) for i in raw_issues]
        except (json.JSONDecodeError, AttributeError):
            pass  # JSON 解析失败，走 fallback

    # Fallback：子串匹配
    if not verdict:
        output_upper = checker_output.upper()
        if "APPROVED" in output_upper and "REJECTED" not in output_upper:
            approved = True
            verdict = "APPROVED"
        else:
            approved = False
            verdict = "REJECTED"
        # 从文本中提取问题列表
        if not approved:
            for line in checker_output.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    issues.append(line.lstrip("-* "))

    return CheckerResult(
        approved=approved,
        feedback=checker_output,
        issues=issues,
        verdict=verdict,
        tokens_used=tokens_used,
    )
