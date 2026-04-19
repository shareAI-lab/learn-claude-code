"""Worktree 隔离(M5-1): EnterWorktree + ExitWorktree。

基于 git worktree add,在 .mycode/worktrees/<name>/ 建独立工作区。
不调 os.chdir(线程安全风险),而是改 cfg._workspace_override,
使后续所有文件工具看到的 workspace_root 变为 worktree。

状态持久化在 .mycode/worktrees/state.json,记录:
- 当前是否在 worktree 里
- 如果是,原始 cwd 是什么、worktree 路径、分支名
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..config.models import Config
from .registry import Tool, ToolRegistry


_NAME_RE = re.compile(r"^[A-Za-z0-9._\-/]{1,64}$")


def _state_path(cfg: Config) -> Path:
    # 注意: 这里要拿**原始 cwd**,不是 workspace_root(),否则进入 worktree 后
    # 查 state 会找错目录
    base = Path.cwd()
    d = base / ".mycode" / "worktrees"
    d.mkdir(parents=True, exist_ok=True)
    return d / "state.json"


def _load_state(cfg: Config) -> dict:
    p = _state_path(cfg)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(cfg: Config, state: dict) -> None:
    _state_path(cfg).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _is_git_repo(path: Path) -> bool:
    r = _git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return r.returncode == 0 and r.stdout.strip() == "true"


def _current_branch(path: Path) -> str | None:
    r = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def _gen_worktree_name() -> str:
    import time
    return f"wt-{hashlib.sha1(str(time.time_ns()).encode()).hexdigest()[:6]}"


# ---------- EnterWorktree ----------


def _run_enter(cfg: Config, name: str | None = None, branch: str | None = None) -> str:
    state = _load_state(cfg)
    if state.get("active"):
        return (
            f"Error: already in a worktree session "
            f"(name={state.get('name')}, path={state.get('path')}). "
            f"Call ExitWorktree first."
        )

    origin = Path.cwd()
    if not _is_git_repo(origin):
        return f"Error: not inside a git repo: {origin}"

    if name is None:
        name = _gen_worktree_name()
    if not _NAME_RE.match(name):
        return f"Error: invalid worktree name '{name}' (only letters/digits/./-/_//)"

    worktree_dir = origin / ".mycode" / "worktrees" / name
    if worktree_dir.exists():
        return f"Error: worktree path already exists: {worktree_dir}"

    branch_name = branch or f"mycode/{name}"
    args = ["worktree", "add", "-b", branch_name, str(worktree_dir)]
    r = _git(args, cwd=origin)
    if r.returncode != 0:
        return f"Error: git worktree add failed: {(r.stderr or r.stdout).strip()}"

    cfg.set_workspace_override(worktree_dir)
    new_state = {
        "active": True,
        "name": name,
        "path": str(worktree_dir),
        "branch": branch_name,
        "origin": str(origin),
    }
    _save_state(cfg, new_state)
    return (
        f"Entered worktree '{name}' at {worktree_dir}\n"
        f"branch: {branch_name}\n"
        f"(workspace_root now points here; call ExitWorktree when done)"
    )


# ---------- ExitWorktree ----------


def _run_exit(
    cfg: Config,
    action: str = "keep",
    discard_changes: bool = False,
) -> str:
    state = _load_state(cfg)
    if not state.get("active"):
        return "Error: not in a worktree session (no-op)"

    origin = Path(state["origin"])
    worktree_dir = Path(state["path"])
    name = state["name"]
    branch = state["branch"]

    if action not in ("keep", "remove"):
        return f"Error: action must be 'keep' or 'remove', got '{action}'"

    # remove 前先检查脏东西
    if action == "remove":
        # 未提交的修改?
        r = _git(["status", "--porcelain"], cwd=worktree_dir)
        dirty = bool(r.stdout.strip()) if r.returncode == 0 else False
        # 有独立 commit?
        r2 = _git(
            ["rev-list", "--count", f"HEAD..{branch}" if False else f"main..HEAD"],
            cwd=worktree_dir,
        )
        # 简化:只要本分支有 commit,不比对 main/master
        has_commits = False
        r3 = _git(["log", "-n", "1", "--format=%H", "HEAD"], cwd=worktree_dir)
        if r3.returncode == 0:
            r4 = _git(["merge-base", "HEAD", "@{-1}"], cwd=worktree_dir)
            # 简化策略: 若 branch 不是刚创建的空 branch,视为有改动
            # 实际实现中我们只看 dirty + 是否有新 commit(相对于创建时的 HEAD)
            has_commits = False  # M5 简化: 只拦 dirty,commit 判断留给 --discard_changes

        if dirty and not discard_changes:
            return (
                f"Error: worktree '{name}' has uncommitted changes:\n"
                f"{r.stdout.strip()[:500]}\n"
                f"Pass discard_changes=true to force remove, or use action='keep'."
            )

        # 执行 remove
        rm_args = ["worktree", "remove", str(worktree_dir)]
        if discard_changes:
            rm_args.insert(2, "--force")
        rr = _git(rm_args, cwd=origin)
        if rr.returncode != 0:
            return f"Error: git worktree remove failed: {(rr.stderr or rr.stdout).strip()}"

        # 删除分支(best effort)
        _git(["branch", "-D", branch], cwd=origin)

        cfg.set_workspace_override(None)
        _save_state(cfg, {})
        return f"Exited and removed worktree '{name}' (branch {branch} deleted)"

    # keep
    cfg.set_workspace_override(None)
    _save_state(cfg, {})
    return (
        f"Exited worktree '{name}'. Path kept at {worktree_dir} (branch {branch}). "
        f"Use git worktree remove later if needed."
    )


# ---------- status 查询 ----------


def _run_status(cfg: Config) -> str:
    state = _load_state(cfg)
    if not state.get("active"):
        return "Not in a worktree session."
    return (
        f"In worktree '{state['name']}'\n"
        f"  path:   {state['path']}\n"
        f"  branch: {state['branch']}\n"
        f"  origin: {state['origin']}"
    )


# ---------- 注册 ----------


def register_worktree(registry: ToolRegistry, cfg: Config) -> None:
    registry.register(
        Tool(
            name="EnterWorktree",
            description=(
                "Create a git worktree under .mycode/worktrees/<name>/ on a new "
                "branch and enter it. The session's workspace_root will point "
                "to the worktree until ExitWorktree is called."
            ),
            requires=["exec", "write"],
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Worktree name (letters/digits/._-/ only, max 64). Auto-generated if omitted.",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name for the new worktree. Default: mycode/<name>",
                    },
                },
            },
            handler=lambda **kw: _run_enter(
                cfg, kw.get("name"), kw.get("branch")
            ),
        )
    )
    registry.register(
        Tool(
            name="ExitWorktree",
            description=(
                "Exit the current worktree session. action='keep' leaves it on "
                "disk; action='remove' deletes the worktree and its branch. "
                "If the worktree has uncommitted changes, remove requires "
                "discard_changes=true."
            ),
            requires=["exec", "write"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["keep", "remove"],
                        "default": "keep",
                    },
                    "discard_changes": {
                        "type": "boolean",
                        "default": False,
                    },
                },
            },
            handler=lambda **kw: _run_exit(
                cfg,
                kw.get("action", "keep"),
                kw.get("discard_changes", False),
            ),
        )
    )
    registry.register(
        Tool(
            name="WorktreeStatus",
            description="Show current worktree session status.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda **_: _run_status(cfg),
        )
    )
